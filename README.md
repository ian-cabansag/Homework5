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

## Databases and clean starting state

`data/campus_customs.db` is the source database. Do not modify it. The server uses only `data/campus_customs_new.db` as its working database. To restore a clean copy before a new run:

```powershell
Copy-Item data/campus_customs.db data/campus_customs_new.db -Force
```

The backend also exposes `POST /database/reset` with an explicit confirmation body; the dashboard does not call it automatically. A reset overwrites the working copy only.

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

The two proposed payments were explicitly approved by Ian and executed through the API approval route. The working DB now has checking at $160.00, invoice 501 marked paid, and both payment rows recorded. MCP resolved rent ticket 102 only after confirming its full approved payment. Tickets 101 and 103 remain open: ticket 101 still has no confirmed shipment, and ticket 103 still lacks a human disposition. See `output/audit_trail.json` for the append-only run, payment, and resolution records; do not claim all tickets were resolved.

## Project evidence

- `output/harness.md`: schema, tools, agents, safety, API, and operating notes
- `output/mcp_smoke.json`: real read-only smoke calls and returned values
- `output/desk_tickets.html`: standalone plans, actual run notes, cash, and reflection
- `output/audit_trail.json`: real append-only operational events
- `output/design.md`: dashboard design rationale

`output/resolved_tickets.json` is a truthful snapshot marked `partially_resolved`, with the actual payment approvals and cash reconciliation; it is not evidence that all tickets were resolved. `output/resolved_board.html` records the actual status and calls out the missing screenshot evidence: ticket 102 is resolved, while 101 and 103 remain open. No screenshot is represented as a resolved result. The working DB currently has $160 checking after Ian-approved payments. Ticket 101 needs verified fulfillment; ticket 103 needs a human pricing/order disposition. No external vendor/customer contact is supported or was made.
