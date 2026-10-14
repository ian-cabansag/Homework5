"""Regression tests use disposable databases and a separate audit journal; no AI calls."""
import asyncio
import os
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main
from backend.audit import AuditTrail
from backend.models import AgentEvent, AgentReply, ApprovalDecision
from backend.agents import build_agents
from backend.mcp_client import MCPGateway
from mcp_server import server

ROOT = Path(__file__).resolve().parents[1]


class SafetyTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.audit-tools'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        (self.root / 'mcp_server').mkdir()
        shutil.copy2(ROOT / 'data/campus_customs.db', self.root / 'data/campus_customs.db')
        shutil.copy2(ROOT / 'data/campus_customs.db', self.root / 'data/campus_customs_new.db')
        shutil.copy2(ROOT / 'mcp_server/server.py', self.root / 'mcp_server/server.py')
        self.db = self.root / 'data/campus_customs_new.db'
        self.audit = AuditTrail(self.root / 'audit.jsonl')
        self.patches = [
            patch.object(server, 'DATABASE_PATH', self.db),
            patch.object(server, 'PROJECT_ROOT', self.root),
            patch('backend.mcp_client.MCP_SERVER_PATH', self.root / 'mcp_server/server.py'),
            patch.object(main, 'audit', self.audit),
            patch.object(main, 'operation_lock', asyncio.Lock()),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(main.app).__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def sql(self, query, args=()):
        with closing(sqlite3.connect(self.db)) as connection:
            with connection:
                return connection.execute(query, args).fetchall()

    def proposal(self, identifier='test-invoice', kind='invoice', ref=501, amount=840):
        asyncio.run(self.audit.append(AgentEvent(
            run_id='isolated-test', ticket_id=101 if kind == 'invoice' else 102,
            event_type='approval_requested', approval_id=identifier,
            summary='Synthetic test fixture, never production run evidence.',
            details={'request': {'payment_kind': kind, 'reference_id': ref, 'amount': amount}},
        )))

    def approve(self, identifier='test-invoice'):
        return self.client.post(f'/approvals/{identifier}/decision', json={
            'approved_by': 'Isolated test operator', 'decision': 'approve'})

    def test_internal_resolution_requires_review_and_preserves_cash_stock(self):
        quote = server.get_ticket_resolution_quote(103)
        self.assertTrue(quote['can_finalize_if_human_approved'])
        self.assertFalse(server.get_ticket_resolution_quote(101)['can_finalize_if_human_approved'])
        inventory = self.sql('SELECT * FROM inventory')
        asyncio.run(self.audit.append(AgentEvent(
            run_id='isolated-test', ticket_id=103, event_type='approval_requested',
            approval_id='test-resolution', summary='Isolated resolution fixture.',
            details={'request': {'payment_kind': 'ticket_resolution', 'reference_id': 103, 'amount': 0},
                     'authoritative_quote': quote},
        )))
        result = self.approve('test-resolution')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertFalse(result.json()['cash_changed'])
        self.assertEqual(self.sql('SELECT balance FROM cash_accounts')[0][0], 3400)
        self.assertEqual(self.sql('SELECT * FROM inventory'), inventory)
        self.assertEqual(self.sql('SELECT status FROM tickets WHERE id=103')[0][0], 'resolved')
        self.assertEqual(self.approve('test-resolution').status_code, 404)
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql('DELETE FROM ticket_resolutions')

    def test_changed_resolution_evidence_requires_new_review(self):
        quote = server.get_ticket_resolution_quote(103)
        self.sql("UPDATE inventory SET qty=9 WHERE sku='CC-HOOD-NAVY' AND size='M'")
        with patch.dict(os.environ, {'CAMPUS_CUSTOMS_APPROVAL_TOKEN': 't' * 48}):
            with self.assertRaises(ValueError):
                server.execute_approved_ticket_resolution(103, 'Test', 'isolated', quote['fingerprint'], 't' * 48)
        self.assertEqual(self.sql('SELECT status FROM tickets WHERE id=103')[0][0], 'open')
        with self.assertRaises(PermissionError):
            server.execute_approved_ticket_resolution(103, 'Test', 'isolated', quote['fingerprint'], 't' * 48)

    def test_payment_quote_proposal_field_aliases(self):
        self.assertEqual(MCPGateway.normalize_agent_arguments('get_payment_quote', {'payment_kind': 'lease', 'reference_id': 1}), {'kind': 'lease', 'ref_id': 1})
        with self.assertRaises(ValueError):
            MCPGateway.normalize_agent_arguments('get_payment_quote', {'payment_kind': 'lease', 'reference_id': 1, 'kind': 'invoice'})

    def test_actual_api_payment_duplicate_and_rent_resolution(self):
        self.proposal()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 0)
        result = self.approve()
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(result.json()['cash_changed'])
        self.assertEqual(self.approve().status_code, 404)
        self.proposal('test-rent', 'lease', 1, 2400)
        self.assertEqual(self.approve('test-rent').status_code, 200)
        self.assertEqual(self.sql('SELECT balance FROM cash_accounts')[0][0], 160)
        self.assertEqual(self.sql('SELECT status FROM tickets WHERE id=102')[0][0], 'resolved')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 2)

    def test_reset_invalidates_old_approvals_and_preserves_history(self):
        self.proposal()
        prefix = self.audit.path.read_bytes()
        self.assertEqual(self.client.post('/database/reset', json={'confirm': False}).status_code, 422)
        result = self.client.post('/database/reset', json={'confirm': True})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.approve().status_code, 404)
        self.assertEqual(self.client.get('/approvals/pending').json()['approvals'], [])
        self.assertEqual(self.sql('SELECT balance FROM cash_accounts')[0][0], 3400)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 0)
        self.assertTrue(self.audit.path.read_bytes().startswith(prefix))
        self.assertEqual(self.client.get('/events').json()['events'], [])
        self.assertEqual(self.client.get('/events?include_history=true').json()['total'], 2)

    def test_changed_amount_is_not_silently_paid(self):
        self.proposal()
        self.sql('UPDATE invoices SET amount=850 WHERE id=501')
        self.assertEqual(self.approve().status_code, 409)
        self.assertEqual(self.sql('SELECT balance FROM cash_accounts')[0][0], 3400)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 0)

    def test_negative_cash_is_rejected(self):
        self.proposal()
        self.sql('UPDATE cash_accounts SET balance=100')
        self.assertEqual(self.approve().status_code, 409)
        self.assertEqual(self.sql('SELECT balance FROM cash_accounts')[0][0], 100)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 0)

    def test_human_name_and_explicit_decision_required(self):
        self.proposal()
        path = '/approvals/test-invoice/decision'
        self.assertEqual(self.client.post(path, json={'approved_by': ' ', 'decision': 'approve'}).status_code, 422)
        self.assertEqual(self.client.post(path, json={'approved_by': 'Test'}).status_code, 422)
        self.assertEqual(self.client.post(path, json={'approved_by': 'Test', 'decision': 'reject'}).status_code, 200)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 0)

    def test_mcp_token_vendor_and_paid_rent_guards(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PermissionError):
                server.execute_approved_payment('invoice', 501, 'Test', 'test', 'x' * 48, 840)
        self.assertFalse(server.get_vendor_shipping_eligibility(1)['can_ship_new_product'])
        with self.assertRaises(ValueError):
            server.resolve_paid_rent_notice()
        self.assertEqual(self.sql('SELECT status FROM tickets WHERE id=102')[0][0], 'open')

    def test_desk_date_is_independent_of_cash_date(self):
        self.sql("UPDATE desk SET date_today='2026-09-01'")
        account = self.client.get('/cash').json()['account']
        self.assertEqual(account['desk_date_today'], '2026-09-01')
        self.assertEqual(account['date'], '2026-08-31')

    def test_long_valid_agent_summary_can_be_audited(self):
        reply = AgentReply(status='ready', summary='a' * 1800)
        event = AgentEvent(run_id='test', summary=reply.summary, event_type='agent_completed')
        self.assertEqual(len(event.summary), 1800)

    def test_cors_and_invalid_ticket_without_model_call(self):
        response = self.client.options('/tickets', headers={
            'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'})
        self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5173')
        self.assertEqual(self.client.post('/tickets/999/run').status_code, 422)

    def test_concurrent_approval_executes_only_once(self):
        self.proposal()
        async def simultaneous():
            decision = ApprovalDecision(approved_by='Isolated test operator', decision='approve')
            return await asyncio.gather(main.decide_payment('test-invoice', decision),
                                        main.decide_payment('test-invoice', decision), return_exceptions=True)
        results = asyncio.run(simultaneous())
        self.assertEqual(sum(isinstance(item, dict) for item in results), 1)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments')[0][0], 1)
        self.assertEqual(self.sql('SELECT balance FROM cash_accounts')[0][0], 2560)

    def test_five_configured_agents_and_read_only_gateway(self):
        with patch('backend.agents.require_portkey_key', return_value='test-placeholder-not-a-secret'):
            agents = build_agents()
        self.assertEqual(len(agents), 5)
        self.assertEqual({agent.model.model_name for agent in agents.values()}, {'gpt-6-Luna'})
        with self.assertRaises(PermissionError):
            asyncio.run(MCPGateway().call_agent_tool('execute_approved_payment', {}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
