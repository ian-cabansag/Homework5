"""Read-only cross-file submission checks; no model calls or business mutations."""
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.audit import AuditTrail
from backend.settings import MODEL_NAME

required = ['AI_prompts.md','requirements.txt','.env.example','.gitignore','.mcp.json','README.md',
            'data/campus_customs.db','data/campus_customs_new.db','mcp_server/server.py','mcp_server/README.md',
            'frontend/package.json','frontend/package-lock.json','frontend/src/App.tsx',
            'backend/main.py','backend/models.py',
            *[f'backend/prompts/{role}.md' for role in ['boss','inventory','accounting','facilities','customer_service']],
            *[f'output/{name}' for name in ['harness.md','mcp_smoke.json','desk_tickets.html','design.md',
                                          'resolved_tickets.json','resolved_board.html','audit_trail.json','github_url.txt']]]
assert all((ROOT / p).is_file() for p in required)
assert MODEL_NAME == 'gpt-6-Luna'
assert not AuditTrail().pending_approvals()
result = json.loads((ROOT / 'output/resolved_tickets.json').read_text(encoding='utf-8'))
shots = json.loads((ROOT / 'output/dashboard_browser_check.json').read_text(encoding='utf-8'))
smoke = json.loads((ROOT / 'output/mcp_smoke.json').read_text(encoding='utf-8'))
assert len(smoke['tests']) == 3 and all(t['verified_all_fields_against_working_db'] for t in smoke['tests'])
with closing(sqlite3.connect((ROOT / 'data/campus_customs_new.db').as_uri()+'?mode=ro', uri=True)) as db:
    statuses = dict(db.execute('SELECT id,status FROM tickets'))
    cash = db.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]
assert cash == result['cash_reconciliation']['ending_checking_balance'] == 160
for record in result['tickets']:
    assert statuses[record['ticket_id']] == record['final_status'] == 'resolved'
for capture in shots['captures']:
    assert capture['status'] == 'Resolved' and capture['checking'] == cash
    assert (ROOT / 'output' / capture['file']).is_file()
assert len(shots['captures']) == 3 and shots['standalone_tabs_passed'] == 5 and not shots['runtime_exceptions']
assert shots['mobile_no_overflow'] and shots['reload_summary_visible']
page = (ROOT / 'output/desk_tickets.html').read_text(encoding='utf-8')
prior = (ROOT / 'output/prior_run/desk_tickets.html').read_text(encoding='utf-8')
pattern = r'<div class="section-title"><h3>Expected</h3>.*?(?=<div class="section-title actual-title">)'
assert re.findall(pattern, page, re.S) == re.findall(pattern, prior, re.S)
assert len(re.findall(pattern, page, re.S)) == 3
for tid in [101,102,103]:
    assert f'ticket {tid} / status: resolved' in page
assert 'What the final run actually showed me.' in page
for file in ['resolved_board.html','desk_tickets.html']:
    text = (ROOT / 'output' / file).read_text(encoding='utf-8')
    for src in re.findall(r'<img[^>]+src="([^"]+)"', text):
        assert not src.startswith(('http:', 'https:', 'data:')) and (ROOT/'output'/src).is_file()
baseline = subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}','show','9296e31:output/audit_trail.json'], cwd=ROOT).decode('utf-8')
old_events = [json.loads(line) for line in baseline.splitlines() if line.strip()]
events = AuditTrail().events()
assert events[:len(old_events)] == old_events
print(f'PASS: {len(required)} required files; all three resolved; cash $160; four decisions complete; screenshots/HTML/JSON/DB agree; Expected plans unchanged; {len(old_events)} historical audit events preserved.')
