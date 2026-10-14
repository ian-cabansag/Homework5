"""Offline reset through MCP with an append-only audit boundary. Stop the API first."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.main import ResetRequest, reset_working_database

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm', action='store_true', required=True)
    parser.parse_args()
    result = asyncio.run(reset_working_database(ResetRequest(confirm=True)))
    print(result.model_dump_json())
