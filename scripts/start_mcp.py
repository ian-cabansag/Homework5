"""Portable stdio launcher; prefer the project's installed virtual environment."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
relative = "Scripts/python.exe" if os.name == "nt" else "bin/python"
candidates = [root / ".venv" / relative, root.parent / ".venv" / relative]
interpreter = next((str(path) for path in candidates if path.is_file()), sys.executable)
os.chdir(root)
os.execv(interpreter, [interpreter, str(root / "mcp_server/server.py")])
