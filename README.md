# Campus Customs Operations Desk

A local multi-agent operations desk for Campus Customs. It combines a FastMCP data service, a FastAPI backend with five bounded PydanticAI roles, and a React/Vite/TypeScript dashboard.

## Requirements and setup

- Python 3.11 or newer
- Node.js 20 or newer and npm
- A Portkey API key for real agent runs

From the HW5 project root (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env locally and set PORTKEY_API_KEY. Never commit or share .env.
```

Install frontend dependencies:

```powershell
cd frontend
npm ci
cd ..
```

The application uses only `gpt-6-Luna` through Portkey for its agents. The MCP server itself does not need the API key.

The audited runtime uses PydanticAI 1.107.6, OpenAI SDK 3.19.2, FastAPI 0.142.2, Pydantic 2.13.5, and MCP 1.30.0. Requirements target these tested SDK major versions. `pydantic-ai-slim[openai]` supplies the same `pydantic_ai` API with the provider used here, without installing unrelated provider integrations. If PowerShell blocks activation, invoke `.venv\Scripts\python.exe` directly; if it blocks `npm.ps1`, use `npm.cmd`.

## Databases and clean starting state

`data/campus_customs.db` is the source database. Do not modify it. The server uses only `data/campus_customs_new.db` as its working database. With the backend stopped and the virtual environment activated, restore a clean copy through MCP and record the reset in the audit:

```powershell
python scripts/reset_working_db.py --confirm
```

With the API running, instead send `POST /database/reset` with JSON `{"confirm":true}` (also available in `/docs`). A reset replaces the working copy and invalidates earlier approvals; earlier audit entries remain available through `/events?include_history=true`. It overwrites the recorded run state, so preserve any evidence you still need before a new run. Do not copy the DB over a running server or reset it without recording the audit boundary.

## Start the services

Start the MCP server in a terminal from the project root:

```powershell
py -m mcp_server.server
```

It uses stdio and is normally launched on demand by the backend or an MCP client; a standalone terminal launch is useful for setup checks.

Start the API in another terminal from `backend/`:

```powershell
uvicorn main:app --reload --port 8000
```

Start the React dashboard in another terminal:

```powershell
cd frontend
npm run dev
```

Open the local Vite URL (normally `http://127.0.0.1:5173`). The dashboard calls `http://localhost:8000`.

## Clean ticket run and approvals

First restore the working database from the original, then verify the starting checking balance and ticket statuses in the dashboard/API. Run tickets 101, 102, and 103 individually from the dashboard. Agent runs only gather evidence and prepare outcomes. If a payment is proposed, inspect its records and use the dashboard's explicit human approval action only when authorized; that route rechecks the database balance. A run requiring approval remains unresolved until the required action is completed. Customer/vendor messages remain drafts; no external contact is made.

Tickets 101 and 103 now have an explicit internal-disposition workflow. After invoice 501 is paid, rerun 101 to obtain an internal backorder-plan proposal. For 103, the team can propose declining the unavailable requested quantity/discount with an unsent availability draft. Review and approve those proposals in the same dashboard approval panel. They resolve internal case handling only: no shipment, order acceptance, stock reservation, or customer contact is implied. Rent ticket 102 resolves atomically with its approved payment. The final run's database-derived status and approvals are recorded in `output/resolved_tickets.json`; never infer payment or resolution from an agent review alone.

## Project evidence

- `output/harness.md`: schema, tools, agents, safety, API, and operating notes
- `output/mcp_smoke.json`: real read-only smoke calls and returned values
- `output/desk_tickets.html`: standalone plans, actual run notes, cash, and reflection
- `output/audit_trail.json`: real append-only operational events
- `output/design.md`: dashboard design rationale

`output/resolved_tickets.json` records final database statuses, actual agent contributions/delegations, tool names, approval IDs, disposition scope and exact cash math. `output/resolved_board.html` embeds real dashboard screenshots using relative assets. `output/prior_run/` preserves the earlier partial-run evidence and DB, explicitly separate from the final working state. `output/audit_trail.json` is newline-delimited JSON: one append-only event per line, including failed attempts and reset boundaries.

## Validation without AI spending

With the Python environment active, run `python -m unittest discover -s tests -v`. These regression tests use disposable copies under ignored `.audit-tools/`; simulated operator decisions and payment rows stay in those test copies. They test the real API/MCP payment and reset paths, without changing the submitted DB or operational journal.

Run `python scripts/verify_evidence.py` to call all three initial tools over real MCP stdio, compare every returned field to independent SQL reads, and refresh `output/mcp_smoke.json` and `output/database_audit.json`. The original smoke capture is retained in `output/mcp_smoke_initial.json`. This verifies the MCP protocol, not whether a particular IDE loaded its project configuration.

Run `python scripts/scan_secrets.py` for a source/evidence and reachable Git-history scan; it reports no secret values. In `frontend/`, run `npm run typecheck` and `npm run build`.

Optional Windows browser evidence (Node 22+ and Chrome): `node scripts/capture_dashboard.mjs PATH_TO_PYTHON PATH_TO_CHROME`. The script temporarily uses backend port 8001 and frontend port 5173, reads the real working DB, captures all three selected tickets, checks reload/mobile/tabs, and stops its processes. It expects three resolved tickets and $160 after the authorized final run; it never starts agents or approves payments. The normal dashboard still defaults to `http://localhost:8000`.

See `output/final_audit.md` for observed validation results and any remaining host-connection steps. To rebuild evidence after an authorized completed run, use `python scripts/finalize_evidence.py`, then `python scripts/verify_evidence.py`, then capture the browser screenshots. The evidence generator refuses an incomplete or inconsistent database and preserves the original Expected sections.

## MCP connection in the IDE

Open **HW5 itself** as the trusted project folder. `.mcp.json` is supplied for hosts that support it; Codex uses the committed `.codex/config.toml`. Both use the portable `scripts/start_mcp.py` launcher and need `python` on PATH. Install dependencies into `.venv` first. Reload the Codex extension/VS Code window after opening HW5 so the project connection can be discovered. The Codex configuration disables mutation tools; approvals and resets belong to the backend. The smoke report distinguishes real protocol tests from actual IDE-host invocations—do not claim the latter until the tools appear and have been invoked there.

## Supervised command-line alternative

With other API instances stopped, `python scripts/run_supervised.py --reset` resets through the real API/MCP path; `--record-start` records the baseline, `--ticket 101` (or 102/103) runs real agents, and `--pending` displays proposals. Only after explicit human authorization, use `--approve APPROVAL_ID --operator NAME`. No approvals are inferred or batch-executed by this script. Do not run it concurrently with the dashboard backend. Use one backend worker: locks/audit append serialization are process-local.
