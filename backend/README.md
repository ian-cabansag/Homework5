# Campus Customs operations backend

The FastAPI backend runs a PydanticAI team for one requested ticket at a time. Its MCP client starts `mcp_server/server.py` by project-relative file location; all business data reads and writes happen in that server. The backend does not open SQLite.

## Configure and run

The project reads `PORTKEY_API_KEY` from the process environment or `.env` at the HW5 project root or its parent workspace root. Keep `.env` private. All five roles share a Portkey OpenAI-compatible connection and the single configured model `gpt-6-Luna`.

From the HW5 project root:

```powershell
py -m pip install -r backend/requirements.txt
py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The API provides `POST /tickets/{ticket_id}/run` for one ticket ID (101, 102, or 103), `GET /approvals/pending`, and `POST /approvals/{approval_id}/decision`. A ticket review only prepares an outcome and possible approval request; it never executes a payment. Only an explicit `approve` decision by an operator can call the MCP payment mutation. Rejection records the decision without changing cash. An approved full payment of a lease linked to a `rent_notice` resolves that rent ticket within the same MCP transaction; the separate guarded reconciliation tool supports a previously recorded full approved payment.

Interactive API documentation is available at `/docs` while the local service is running.

Internal dispositions for tickets 101/103 use the same human decision route. MCP binds execution to the reviewed evidence fingerprint, appends the exact unsent draft and disposition, and changes only ticket status/history. It returns `cash_changed:false`. Ticket 101 requires its linked invoice payment and no unpaid vendor invoices. These dispositions do not claim shipment or an accepted order. Use one backend process; never run the offline supervisor concurrently with it.

## Agent roles and operating limits

Detailed role instructions live in `prompts/`. Boss coordinates and synthesizes; Inventory handles stock and replenishment constraints; Accounting handles invoices, cash, and approval requests; Facilities handles lease notices; Customer Service writes internal drafts. Agents can delegate with a specific reason and task. Runtime guards stop role cycles, cap the delegation depth at two and total delegations at three, and cap a ticket run at five agent invocations and twelve MCP calls. Each PydanticAI invocation is separately capped at four model requests, six tool calls, and 8,000 tokens.

`output/audit_trail.json` is append-only newline-delimited JSON: each line is one `AgentEvent`. It records operational summaries, tool names, delegation attempts/results, approval requests/decisions, and stop reasons, never hidden chain-of-thought. One worker is specified in the run command so concurrent processes do not compete over this file.
