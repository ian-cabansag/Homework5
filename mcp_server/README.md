# Campus Customs MCP server

This FastMCP server gives the operations agents focused, database-backed evidence for the three Campus Customs tickets. All business reads and writes stay in the MCP layer. AI agents receive read tools only; the payment tool is called by the backend only after explicit human approval. A rent notice can be resolved only after MCP verifies its full approved payment in the ledger.

## Database

The server reads and, for a specifically approved payment, updates `data/campus_customs_new.db` relative to this file. Read tools open SQLite in read-only mode and enable `query_only`. The payment tool uses a transaction and never connects to the original `data/campus_customs.db`.

## Install and run

From the HW5 project root, install the MCP Python SDK in the Python environment the client will use, then launch the stdio server:

```powershell
py -m pip install -r mcp_server/requirements.txt
py -m mcp_server.server
```

The server expects the working database to exist before launch. `.mcp.json` and `.codex/config.toml` launch `python scripts/start_mcp.py` from HW5. The launcher uses a project `.venv` (or the parent workspace `.venv`) when available, otherwise the invoking interpreter. Open HW5 itself as the trusted IDE project and reload the Codex extension to load its project configuration. Codex's configuration disables mutation tools in the IDE; use the backend's explicit approval/reset routes. FastMCP communicates over stdio; the backend independently launches it with its own interpreter. Protocol smoke tests are not proof that the IDE loaded the connection.

## Tools

The payment tool additionally requires `approved_amount` to equal the transaction's authoritative quote. It rejects changed amounts, non-finite/non-cent financial records, duplicates, and negative cash. Use the backend approval route rather than calling payment tools manually. Reset through the API or the offline reset script so old approvals are invalidated in the preserved audit journal.

| Tool | Tables used | Purpose and access |
|---|---|---|
| `get_ticket_101_tee_reprint_context` | `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `cash_accounts`, `desk`, `payments` | Reads ticket 101's tee stock, pricing, linked reprint and vendor lead time, date, cash, and payment ledger. |
| `get_ticket_102_rent_and_cash_context` | `tickets`, `leases`, `cash_accounts`, `desk`, `payments` | Reads ticket 102's lease, rent due date, desk date, checking balance, and payment ledger. |
| `get_ticket_103_hoodie_stock_and_pricing` | `tickets`, `inventory`, `pricing` | Reads ticket 103's requested hoodie quantity, all size stock, unit cost, and list price. |
| `list_vendors` | `vendors` | Reads database vendor specialties and lead times without inferring unsupported product matches. |
| `get_vendor_shipping_eligibility` | `vendors`, `invoices` | Reads a vendor's open invoices and reports whether new product is blocked from shipping. |
| `get_payment_quote` | `cash_accounts`, `desk`, `invoices` or `leases`, `payments` | Reads the authoritative amount, shop date, cash, and duplicate/open status for an outgoing payment proposal. |
| `get_dashboard_tickets` | `tickets` | Returns tickets 101–103 and their actual current statuses for FastAPI/the dashboard. |
| `get_checking_balance` | `cash_accounts`, `desk` | Returns checking, its recorded date, and `desk_date_today` for FastAPI/the dashboard. |
| `execute_approved_payment` | `cash_accounts`, `desk`, `invoices` or `leases`, `payments`, `tickets` | Writes one outgoing invoice or rent payment only when called with the backend's one-time approval token; atomically checks current cash, records approver/payment/date, reduces checking, marks an invoice paid, and resolves a linked rent notice after payment. |
| `resolve_paid_rent_notice` | `tickets`, `leases`, `payments` | Reconciles ticket 102 after an already-recorded full lease payment; refuses if the ticket is not the linked rent notice or the payment is missing, partial, or lacks an approver. Never moves cash. |
| `reset_working_database` | Original/working database files; SQLite integrity metadata | Replaces only the working DB with a verified copy of the original; never writes the source DB. |
| `get_ticket_resolution_quote` | `tickets`, `inventory`, `pricing`, `desk`; for 101 also `invoices`, `vendors`, `payments` | Read an exact internal disposition, unsent draft, prerequisites and evidence fingerprint for human review. |
| `execute_approved_ticket_resolution` | Same quote tables; writes `tickets`, `ticket_resolutions` | One-time approval token required. Rechecks the fingerprint and prerequisites transactionally, appends the approved draft/evidence, and resolves internal handling only. No cash, stock, purchase, shipment or external contact. |
| `get_ticket_resolution_record` | `ticket_resolutions` | Read the exact stored disposition and human approval; returns null before a resolution exists. |

Tools take no caller-supplied SQL. Required identifiers and payment kinds are validated; missing required records raise an error instead of being filled in with assumptions. The backend exposes only read tools to PydanticAI. It invokes `execute_approved_payment` only after an operator approves a pending request, and the short-lived approval token is not written to the audit log. The write tool rechecks that the obligation remains open/unpaid and that checking will not go below zero inside a SQLite transaction. Rent resolution is guarded by a full human-approved lease payment record. No tool records incoming revenue, sends email, or contacts a vendor.
