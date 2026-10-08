"""Central model and project settings. Secrets are read from environment only."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_CANDIDATES = (PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env")
for env_path in ENV_CANDIDATES:
    if env_path.is_file():
        load_dotenv(env_path, override=False)

MODEL_NAME = "gpt-6-Luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_server" / "server.py"
PROMPTS_DIR = PROJECT_ROOT / "backend" / "prompts"


def require_portkey_key() -> str:
    if not PORTKEY_API_KEY:
        raise RuntimeError("PORTKEY_API_KEY is not configured in the environment or project root .env.")
    return PORTKEY_API_KEY
