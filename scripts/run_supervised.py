"""Exercise the real API and model/MCP runtime, one explicitly selected action at a time.

Stop other backend instances first. Approve only after the human has authorized
the specific pending action; this script never decides approvals automatically.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.main import app, audit
from backend.models import AgentEvent

parser = argparse.ArgumentParser(description=__doc__)
actions = parser.add_mutually_exclusive_group(required=True)
actions.add_argument('--reset', action='store_true')
actions.add_argument('--ticket', type=int, choices=[101, 102, 103])
actions.add_argument('--approve', metavar='APPROVAL_ID')
actions.add_argument('--pending', action='store_true')
actions.add_argument('--record-start', action='store_true')
parser.add_argument('--operator')
args = parser.parse_args()
with TestClient(app) as client:
    if args.reset:
        response = client.post('/database/reset', json={'confirm': True})
    elif args.record_start:
        response = client.get('/cash')
        response.raise_for_status()
        asyncio.run(audit.append(AgentEvent(
            run_id='clean-final-run', event_type='starting_balance_verified',
            summary='Recorded the reset working database checking balance through MCP.',
            details=response.json(), tool_name='get_checking_balance')))
    elif args.ticket:
        response = client.post(f'/tickets/{args.ticket}/run', json={})
    elif args.approve:
        if not args.operator:
            parser.error('--approve requires the explicitly authorizing --operator')
        response = client.post(f'/approvals/{args.approve}/decision', json={
            'decision': 'approve', 'approved_by': args.operator,
            'note': 'Operator explicitly authorized this action in the supervised final run.'})
    else:
        response = client.get('/approvals/pending')
    print(json.dumps({'http_status': response.status_code, 'result': response.json()}, indent=2))
    response.raise_for_status()
