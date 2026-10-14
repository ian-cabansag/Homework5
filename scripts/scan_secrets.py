"""Scan project files and all reachable Git blobs, reporting no secret values."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.settings import PORTKEY_API_KEY

PATTERN = re.compile(rb'(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
key = PORTKEY_API_KEY.encode() if PORTKEY_API_KEY else None
findings = []
count = 0
for path in ROOT.rglob('*'):
    if not path.is_file() or any(p in {'.git', '.audit-tools', '.venv', 'node_modules', '__pycache__', 'dist'} for p in path.relative_to(ROOT).parts):
        continue
    if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example'):
        continue
    value = path.read_bytes()
    count += 1
    if PATTERN.search(value) or (key and key in value):
        findings.append({'scope': 'working_tree', 'file': path.relative_to(ROOT).as_posix()})

def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args], cwd=ROOT)

blobs = 0
for row in git('rev-list', '--objects', '--all').decode().splitlines():
    parts = row.split(' ', 1)
    oid = parts[0]
    if git('cat-file', '-t', oid).strip() != b'blob':
        continue
    value = git('cat-file', 'blob', oid)
    blobs += 1
    if PATTERN.search(value) or (key and key in value):
        findings.append({'scope': 'git_history', 'object': oid, 'file': parts[1] if len(parts) > 1 else ''})
tracked = git('ls-files').decode().splitlines()
assert '.env' not in tracked
assert all(f'data/{name}' in tracked for name in ('campus_customs.db', 'campus_customs_new.db'))
result = {'working_files_scanned': count, 'git_blobs_scanned': blobs,
          'known_key_comparison_available': bool(key), 'findings': findings,
          'real_env_tracked': False, 'both_databases_tracked': True,
          'scope': 'Project source/evidence and reachable Git history; excludes local secrets and generated dependencies/caches.'}
(ROOT / 'output/security_check.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
sys.exit(bool(findings))
