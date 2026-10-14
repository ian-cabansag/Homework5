"""Read-only SQL cross-check of real MCP calls; generates reproducible audit evidence."""
import asyncio
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.mcp_client import MCPGateway


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    db = ROOT / 'data/campus_customs_new.db'
    original = ROOT / 'data/campus_customs.db'
    original_hash = digest(original)
    assert original_hash == '23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a'
    before = digest(db)
    schema = {}
    for path in (original, db):
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            tables = [x[0] for x in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            schema[path.name] = {
                'sha256': digest(path),
                'integrity_check': connection.execute('PRAGMA integrity_check').fetchone()[0],
                'foreign_key_check': [list(x) for x in connection.execute('PRAGMA foreign_key_check')],
                'tables': {name: {
                    'fields': [dict(x) for x in connection.execute(f'PRAGMA table_info("{name}")')],
                    'foreign_keys': [dict(x) for x in connection.execute(f'PRAGMA foreign_key_list("{name}")')],
                    'rows': [dict(x) for x in connection.execute(f'SELECT * FROM "{name}"')],
                } for name in tables},
            }
            assert schema[path.name]['integrity_check'] == 'ok'
            assert not schema[path.name]['foreign_key_check']
    rows = {name: value['rows'] for name, value in schema[db.name]['tables'].items()}
    def one(table, field, value):
        return next(row for row in rows[table] if row[field] == value)
    cash = one('cash_accounts', 'name', 'checking')
    expected = {}
    for ticket_id in (101, 102, 103):
        ticket = one('tickets', 'id', ticket_id)
        value = {'ticket': ticket}
        if ticket_id in (101, 103):
            value['pricing'] = one('pricing', 'sku', ticket['sku'])
            stock = sorted([r for r in rows['inventory'] if r['sku'] == ticket['sku']], key=lambda r:r['size'])
            if ticket_id == 101:
                value['inventory'] = next(r for r in stock if r['size'] == ticket['size'])
                value['invoice'] = one('invoices', 'id', ticket['invoice_id'])
                value['vendor'] = one('vendors', 'id', value['invoice']['vendor_id'])
            else:
                value['inventory_by_size'] = stock
        else:
            value['lease'] = one('leases', 'id', ticket['lease_id'])
        if ticket_id != 103:
            value.update(checking=cash, desk_date_today=rows['desk'][0]['date_today'],
                         payment_ledger=sorted(rows['payments'], key=lambda r:r['id']))
        expected[ticket_id] = value
    tests = []
    async with MCPGateway() as gateway:
        names = await gateway.list_tool_names()
        for ticket_id, name in [(101,'get_ticket_101_tee_reprint_context'),
                                (102,'get_ticket_102_rent_and_cash_context'),
                                (103,'get_ticket_103_hoodie_stock_and_pricing')]:
            result = await gateway.call_agent_tool(name, {})
            assert result == expected[ticket_id], f'{name} differs from independent SQLite records'
            tests.append({'prompt': f'Read the current factual records for ticket {ticket_id}.',
                          'tool_name': name, 'arguments': {}, 'returned_output': result,
                          'verified_all_fields_against_working_db': True})
    assert digest(db) == before and digest(original) == original_hash
    resolved = json.loads((ROOT / 'output/resolved_tickets.json').read_text(encoding='utf-8'))
    for ticket in resolved['tickets']:
        assert ticket['final_status'] == one('tickets', 'id', ticket['ticket_id'])['status']
    start = schema[original.name]['tables']['cash_accounts']['rows'][0]['balance']
    outgoing = sum(row['amount'] for row in rows['payments'])
    assert start - outgoing == cash['balance'] == resolved['cash_reconciliation']['ending_checking_balance']
    evidence = {'verification': {'captured_at': datetime.now(timezone.utc).isoformat(),
        'mcp_interface': 'Real FastMCP stdio calls through backend MCPGateway (not an IDE tool invocation)',
        'database': 'data/campus_customs_new.db', 'sha256': before,
        'database_check': 'Every returned field compared with independent read-only SQL; all equal.',
        'tools_available': sorted(names), 'ai_calls': 0}, 'tests': tests}
    destination = ROOT / 'output/mcp_smoke.json'
    archive = ROOT / 'output/mcp_smoke_initial.json'
    if not archive.exists():
        archive.write_bytes(destination.read_bytes())
    destination.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'output/database_audit.json').write_text(json.dumps(schema, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: {len(names)} MCP tools; all 3 smoke outputs match every DB field; cash {start} - {outgoing} = {cash["balance"]}; original unchanged.')


if __name__ == '__main__':
    asyncio.run(main())
