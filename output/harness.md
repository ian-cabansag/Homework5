# Campus Customs Database Harness

Problem 2 records the source database as found, the working copy, and the data relationships relevant to tickets 101–103. This is a factual reference for later implementation; no ticket has been processed here.

## Database files and source baseline (before the recorded run)

- Original source: `data/campus_customs.db` (53,248 bytes; SQLite integrity check: `ok`).
- Working database: `data/campus_customs_new.db`, initially copied from the original. The source baseline below is historical; see the final-run section and `resolved_tickets.json` for the verified current state.
- Shop date (`desk.date_today`): **2026-08-31**. Use this database value as “today.”
- Checking balance (`cash_accounts` row `checking`): **$3,400.00**, dated **2026-08-31**.
- The original contains nine application tables and three open tickets: 101, 102, and 103.

## Tables and fields

| Table | Fields (type; key/constraints where defined) | Why it matters |
|---|---|---|
| `cash_accounts` | `name` TEXT (PK); `balance` REAL (required); `date` TEXT (required) | Supplies the available cash and its as-of date for safe payment decisions. |
| `desk` | `date_today` TEXT (required); `notes` TEXT (optional) | The authoritative shop date for due-date and timing decisions. |
| `inventory` | `sku` TEXT (composite PK); `name` TEXT (required); `size` TEXT (composite PK); `qty` INTEGER (required); `location` TEXT (required) | Gives actual stock by SKU and size, plus the shop location. |
| `invoices` | `id` INTEGER (PK); `vendor_id` INTEGER (required, FK → `vendors.id`); `amount` REAL (required); `due_date` TEXT (required); `status` TEXT (required); `description` TEXT (optional) | Tracks vendor obligations, including an open invoice that can block new orders. |
| `leases` | `id` INTEGER (PK); `space_name` TEXT (required); `landlord` TEXT (required); `monthly_rent` REAL (required); `next_due` TEXT (required); `notes` TEXT (optional) | Supplies rent amount, landlord, and due date for the rent notice. |
| `payments` | `id` INTEGER (PK); `kind` TEXT (required); `ref_id` INTEGER (optional); `amount` REAL (required); `account` TEXT (required); `paid_at` TEXT (required); `approved_by` TEXT (required) | Append-only record of actual payments and their human approval; currently empty. |
| `pricing` | `sku` TEXT (PK); `unit_cost` REAL (required); `list_price` REAL (required) | Grounds product cost and listed price, including any proposed discount calculation. |
| `tickets` | `id` INTEGER (PK); `type` TEXT (required); `requester` TEXT (required); `subject` TEXT (required); `sku` TEXT (optional); `size` TEXT (optional); `qty` INTEGER (optional); `lease_id` INTEGER (optional, FK → `leases.id`); `invoice_id` INTEGER (optional, FK → `invoices.id`); `status` TEXT (required); `notes` TEXT (optional); `created_at` TEXT (required) | Holds the requests and references the lease or invoice involved; open ticket data drives agent work. |
| `vendors` | `id` INTEGER (PK); `name` TEXT (required); `specialty` TEXT (required); `lead_days` INTEGER (required) | Grounds vendor selection and shipping lead time in database facts. |

The declared foreign keys are `invoices.vendor_id → vendors.id`, `tickets.lease_id → leases.id`, and `tickets.invoice_id → invoices.id`. Inventory, pricing, and ticket SKUs are not declared as SQL foreign keys, but matching SKU values connect those records operationally. `payments.ref_id` has no declared foreign key; its meaning is paired with `kind` by application logic. `cash_accounts.name` also has no declared payment-account FK.

## Open ticket traces

### Ticket 101 — Tauhid Zaman, “Bulldog tee”

- Ticket requests one `CC-TEE-WHITE`, size `S`; ticket 101 is open and references invoice 501.
- Inventory has **0** `CC-TEE-WHITE` size S (Aisle B). The other tee stock is M 5, L 3, XL 2.
- Pricing for `CC-TEE-WHITE`: unit cost **$8.00**, list price **$28.00**.
- Invoice 501 is **$840.00**, due **2026-08-28**, status `open`, description “Rush reprint CC-TEE-WHITE S.” It references vendor 1, Bulldog Print Co (apparel reprint; **5-day** lead time).
- Cash is $3,400.00. The open invoice alone is below cash, but the $2,400.00 rent due 2026-09-02 would leave only $160.00 if both were paid. Payment still requires human approval; the open vendor invoice also means that vendor cannot ship new product under the assignment rules.
- No payment rows exist, so invoice 501 remains unpaid according to the present payment ledger.

### Ticket 102 — Elm City Properties, “Rent due”

- Open `rent_notice` ticket references lease 1 and has no SKU, quantity, or invoice reference. Its note says rent is due in two days.
- Lease 1 is the Chapel Street shop, landlord Elm City Properties, monthly rent **$2,400.00**, next due **2026-09-02**.
- `desk.date_today` is **2026-08-31**, consistent with the ticket note. Checking has **$3,400.00** as of that date; paying rent alone would leave $1,000.00.
- No payment exists for this lease in `payments` (table currently empty). The ticket asks for handling a notice; the database does not establish that payment has been approved or made.

### Ticket 103 — Yale AI Club, “Bulk hoodie discount”

- Open `price_override` ticket requests **20** `CC-HOOD-NAVY`, size M, and asks for a bulk discount.
- Inventory has **8** size M hoodies (Aisle A); total hoodie stock by size is S 4, M 8, L 14, XL 6. The request exceeds available M stock by 12.
- Pricing for `CC-HOOD-NAVY`: unit cost **$22.00**, list price **$58.00**. No override price is stored in the database.
- There is no vendor or invoice link on this ticket. The vendor list provides no hoodie-specific supplier: vendor 1 specializes in apparel reprints, vendor 2 in mugs and small goods, and vendor 3 in local courier service. Lead times must be looked up from that table if a vendor becomes relevant.
- No payment or incoming revenue is recorded. Any response or price proposal must remain a draft in the system.

## Remaining source rows and facts

- `cash_accounts`: one row, `checking`, $3,400.00, date 2026-08-31.
- `desk`: one row, date 2026-08-31, no notes.
- `invoices`: only invoice 501, described above.
- `leases`: only lease 1, described above.
- `payments`: zero rows.
- `pricing`: `CC-HOOD-NAVY` $22.00 cost / $58.00 list; `CC-TEE-WHITE` $8.00 / $28.00; `CC-HAT-BLUE` $6.00 / $22.00; `CC-MUG-CREST` $3.50 / $14.00.
- `inventory`: `CC-HOOD-NAVY` sizes S/M/L/XL quantities 4/8/14/6 in Aisle A; `CC-TEE-WHITE` sizes S/M/L/XL quantities 0/5/3/2 in Aisle B; `CC-HAT-BLUE` OS quantity 40 in Aisle C; `CC-MUG-CREST` OS quantity 0 in Aisle D.
- `vendors`: ID 1 Bulldog Print Co, apparel reprint, 5 days; ID 2 Elm City Gifts, mugs and small goods, 3 days; ID 3 QuickShip CT, local courier, 1 day.

## Problem 3 MCP evidence tools

The FastMCP server in `mcp_server/server.py` opens only `data/campus_customs_new.db` in SQLite read-only/query-only mode. Each tool is fixed to its ticket and returns structured data from the database.

| Tool name | Tables read | Ticket unlocked | Why this tool fits |
|---|---|---:|---|
| `get_ticket_101_tee_reprint_context` | `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `cash_accounts`, `desk`, `payments` | 101 | It brings together the requested size's actual stock and price, the linked reprint invoice and vendor lead time, and the payment ledger needed to assess the backorder. |
| `get_ticket_102_rent_and_cash_context` | `tickets`, `leases`, `cash_accounts`, `desk`, `payments` | 102 | It gives the lease amount and due date alongside the authoritative shop date, available cash, and payment ledger. |
| `get_ticket_103_hoodie_stock_and_pricing` | `tickets`, `inventory`, `pricing` | 103 | It grounds the requested bulk quantity and discount discussion in all hoodie size-level stock and the database's unit cost and list price. |

## Problem 5 five-agent operations team

Each role has its own detailed operational prompt in `backend/prompts/`:

| Agent | Responsibility |
|---|---|
| Boss | Triage one ticket, select only necessary specialists, combine their evidence, and return the operational outcome. |
| Inventory | Verify SKU/size quantities, costs, vendor specialties, lead times, and vendor shipment eligibility. |
| Accounting | Verify invoices, rent, checking cash, payment quotes, and prepare human approval requests without executing payments. |
| Facilities | Handle lease and premises notices using the lease and authoritative desk date. |
| Customer Service | Prepare internal customer-response drafts grounded in evidence; never send them. |

The team and FastAPI routes use these MCP tools from `mcp_server/server.py`:

| Tool | Tables used | Access and purpose |
|---|---|---|
| `get_ticket_101_tee_reprint_context` | `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `cash_accounts`, `desk`, `payments` | Read ticket 101 tee availability, pricing, linked invoice/vendor and cash/date context. |
| `get_ticket_102_rent_and_cash_context` | `tickets`, `leases`, `cash_accounts`, `desk`, `payments` | Read ticket 102 lease, rent due date, current shop date, cash, and payment ledger. |
| `get_ticket_103_hoodie_stock_and_pricing` | `tickets`, `inventory`, `pricing` | Read ticket 103 hoodie sizes, quantities, unit cost, and list price. |
| `list_vendors` | `vendors` | Read factual vendor specialties and lead times. |
| `get_vendor_shipping_eligibility` | `vendors`, `invoices` | Read a vendor's open invoices and calculate whether new product is blocked from shipment. |
| `get_payment_quote` | `cash_accounts`, `desk`, `invoices` or `leases`, `payments` | Read the database amount, date, balance, and eligibility for a proposed outgoing invoice or rent payment. |
| `execute_approved_payment` | `cash_accounts`, `desk`, `invoices` or `leases`, `payments`, `tickets` | Write an outgoing payment and update checking only after explicit human approval; transactionally rechecks amount, open/unpaid state, and nonnegative cash. A linked rent notice is resolved in the same transaction. This tool is excluded from every agent's MCP allowlist. |
| `resolve_paid_rent_notice` | `tickets`, `leases`, `payments` | Reconcile ticket 102 after a full approved lease payment already exists; refuses if payment amount or approver evidence is missing. No cash change. |
| `get_dashboard_tickets` | `tickets` | Read tickets 101–103 and their actual status for the API/dashboard. |
| `get_checking_balance` | `cash_accounts`, `desk` | Read checking, its recorded date, and the independent authoritative shop date for the API/dashboard. |
| `reset_working_database` | Original and working database files; validates SQLite integrity | Administrative reset only: replace the working DB with a verified copy of the original. Never writes the original. |

### Safety and loop controls

- Every AI call uses the single model name **`gpt-6-Luna` through Portkey**. All five PydanticAI agents share the same configured Portkey-backed model; no fallback model is configured.
- Backend business-data access is exclusively through the MCP client. Read-only tools use SQLite read-only/query-only connections. MCP owns payment writes, paid-rent reconciliation, and administrative reset. The original is read only as the source of an explicit reset and is never modified.
- `desk.date_today` is the only shop date. Vendor lead time and open invoice status come from `vendors`/`invoices`. A vendor with an open invoice cannot ship new product.
- Cash only goes out. Agents cannot invoke the payment tool. A payment proposal is checked against `get_payment_quote`; an operator must explicitly approve through the API. The MCP server then requires a short-lived backend approval token, rechecks the obligation and balance inside a write transaction, and refuses a negative checking balance.
- There is no sales/revenue write, no customer email, and no vendor-contact tool. Customer/vendor text remains a draft.
- Each run addresses one ticket only. Limits: five agent invocations, twelve MCP calls, three delegations, delegation depth two, and per agent run four model requests, six tool calls, and 8,000 tokens. The runtime rejects cycles and agents that return without consulting MCP evidence.
- `output/audit_trail.json` is append-only newline-delimited JSON. It records agent starts/results, MCP tool use/results, delegation attempts/results, approval decisions, and stop reasons as concise operational summaries; it does not record hidden chain-of-thought.

Problem 5 creates the team and the guarded API; no ticket run was started here.

## Problem 7 FastAPI dashboard API

Start from `backend/` with `uvicorn main:app --reload --port 8000`. The API uses the MCP client for business database reads/writes; it does not query SQLite directly. React development origins `http://localhost:5173` and `http://127.0.0.1:5173` are allowed by CORS.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Health/status check. |
| `GET` | `/tickets` | Return tickets 101–103 and their current status via MCP. |
| `POST` | `/tickets/{ticket_id}/run` | Run the bounded agent team on exactly one valid ticket ID (101–103); never executes payment. |
| `GET` | `/events?limit=100&ticket_id=101` | Return recent append-only audit events, optionally filtered to a ticket. |
| `GET` | `/approvals/pending` | Return outstanding human payment approvals. |
| `POST` | `/approvals/{approval_id}/decision` | Record a human approve/reject decision; only this explicit route can invoke MCP's guarded payment action. Body: `{"approved_by":"...","decision":"approve"|"reject","note":"..."}`. |
| `GET` | `/cash` | Return current checking balance and recorded date via MCP. |
| `POST` | `/database/reset` | With body `{"confirm":true}`, restore `data/campus_customs_new.db` from the original source via MCP; does not modify the original. |

Payment requests are re-quoted from the working DB and require an eligible obligation, explicit human approval, and a transaction-time nonnegative-balance check. The approval route is the only backend cash-changing path. A fully paid rent notice is resolved by MCP only after payment is recorded. Reset is separately explicit and only replaces the working copy. This API was added without running the ticket team or resetting the database.

## Problem 8 operations dashboard

`frontend/` contains the React + Vite + TypeScript supervision UI. It calls `http://localhost:8000`, polls audit activity and pending approvals every four seconds, and refreshes database-backed ticket/cash state every twenty seconds and after actions. Approve is explicit, requires an approver name, and only reports a cash change when the API confirms `cash_changed: true`. Current executable approval support is invoice/lease only; purchase approval remains disabled because there is no purchase-order operation in the database/API. Verify with `npm run typecheck` and `npm run build` from `frontend/`.

## Historical partial run — superseded by the clean final run below

The genuine run events are append-only in `output/audit_trail.json`. Ticket 101's first attempt stopped on an MCP argument mismatch; the retry completed as `needs_approval`. Ticket 102 completed as `needs_approval`; ticket 103 completed as `draft_only`. Ian explicitly approved invoice 501 ($840) and Lease 1 rent ($2,400) through the API approval route. Both payment executions and approvals are recorded in the audit; invoice 501 is paid, the payments ledger has two outgoing rows, and checking is $160.00. Ticket 102 was resolved only after MCP verified its paid lease record. Ticket 101's post-payment MCP eligibility check confirms the vendor may ship, but no shipment is confirmed; ticket 101 remains open. Ticket 103 remains open pending pricing/order disposition. Cash reconciliation: $3,400.00 − $840.00 − $2,400.00 − $0.00 = $160.00. This is not a three-ticket resolution.

## Historical Problem 10 evidence limits — before the final workflow

The Reflection tab in `output/desk_tickets.html` compares the expected routes with actual participation, duplicated MCP reads, the blocked delegation cycle, both approved payments, and the resulting cash. It also describes supported and unsupported future tasks. `output/resolved_tickets.json` records the actual ticket status for each request. Only ticket 102 is resolved; tickets 101 and 103 remain open. No three-ticket resolved dashboard screenshots are claimed. A final completion still needs legitimate dispositions for 101 and 103, a matching DB and audit trail, and genuine dashboard screenshots.

Current working-database snapshot after the human-approved payments: invoice 501 is `paid`; the payment ledger records $840 to invoice 501 and $2,400 to Lease 1, both approved by Ian; checking is $160.00. Ticket 102 is `resolved` after the rent-payment guard verified its obligation was paid; tickets 101 and 103 remain `open`. A post-payment MCP eligibility read confirms vendor 1 has no open invoices and is eligible to ship, but no shipment/receipt is recorded. The original database file remains byte-for-byte unchanged.

## Earlier audit corrections and reproducible checks

- Payment decisions, runs, and resets share one operation lock in the single-worker backend. The transaction requires the exact amount shown in the human-reviewed proposal, checks finite whole-cent financial values, and rejects duplicate or unaffordable payments.
- A reset records an append-only generation boundary under that lock. Earlier approval IDs cannot execute against the new database. `/events` defaults to the current generation; `/events?include_history=true` exposes the preserved history. Use the API reset route, or `python scripts/reset_working_db.py --confirm` with the API stopped.
- MCP session contexts unwind fully on successful calls, rejected payments, and initialization failures. The one-time approval token is confined to the payment subprocess and never logged.
- `get_checking_balance` now reads both `cash_accounts` and `desk`, so the displayed shop date cannot drift with the last cash transaction date.
- Future run outcomes, including internal drafts and specialist reports, are saved in the final audit event. The dashboard restores them after refresh, labels them as historical reviews, and displays internal drafts. Older runs retain only the information originally recorded; missing old draft text is not reconstructed.
- The agent/audit summary limits now agree at 1,800 characters; valid long agent summaries no longer fail audit validation. The MCP-call cap is enforced before incrementing, using the shared 12-call constant.
- Fresh `output/mcp_smoke.json` results match every field in the current working DB. The pre-payment smoke capture remains in `output/mcp_smoke_initial.json`. `output/database_audit.json` contains all source/working table fields, foreign keys, actual rows, integrity checks, and hashes.
- `output/resolved_board.html` now embeds actual screenshots for all three selected tickets. Screenshots and DB consistently show Open / Resolved / Open and $160. This remains a partial run, not three resolved tickets.
- Regression commands, normal startup, offline reset, and browser capture instructions are in the root README. `output/final_audit.md` separates observed passes from the remaining resolution and IDE-connection gaps.

## Clean final run — October 14, 2026 (supersedes partial-run notes above)

The real working database was reset from the unchanged original through the API/MCP reset operation. The audit records the reset and an MCP-verified $3,400 starting checking balance. Shop date remains 2026-08-31. Ian explicitly approved invoice 501 ($840), lease 1 ($2,400), ticket 101's internal backorder plan after payment, and ticket 103's internally declined quantity/discount request with an unsent response.

All three database ticket statuses are now `resolved`. Ticket 101 ran twice: before and after invoice payment. Ticket 102's first review failed on payment-quote argument aliases after redundant Accounting delegation; the adapter and routing instructions were corrected and the retry completed. Ticket 103 used Inventory and Customer Service. All meaningful steps, failed attempts, proposals and human actions remain in the append-only audit. Exact run IDs, contributions, delegations, tools, approval IDs and dispositions are in `resolved_tickets.json`.

Cash: $3,400 − $840 (invoice 501 / ticket 101) − $2,400 (lease 1 / ticket 102) − $0 (ticket 103) = **$160**, verified against `cash_accounts` and both `payments` rows. Internal dispositions do not move cash or stock. Ticket 101 closure does not establish shipment or fulfillment; ticket 103 closure does not authorize a discount, reserve stock or accept an order. All drafts remain unsent.

### Final MCP additions (14 tools total)

The preceding 11-tool table remains applicable, plus:

| Tool | Tables | Purpose / guard |
|---|---|---|
| `get_ticket_resolution_quote` | `tickets`, `inventory`, `pricing`, `desk`; 101 also `invoices`, `vendors`, `payments` | Exact internal disposition/draft, eligibility and evidence fingerprint for a human review. |
| `execute_approved_ticket_resolution` | Same quote tables; writes `tickets`, `ticket_resolutions` | One-time backend approval token, named human, unchanged evidence fingerprint and transaction-time prerequisite checks. Marks internal handling resolved without cash, stock or external effects. |
| `get_ticket_resolution_record` | `ticket_resolutions` | Reads the stored approved internal disposition, draft and audit link; null before it exists. |

### Working-only table

`ticket_resolutions` is created only in the working DB when an approved internal disposition executes. Fields: `ticket_id` INTEGER PK/FK to tickets.id; `disposition`, `summary`, `draft`, `evidence_json`, `approved_by`, `approval_id`, `resolved_on` TEXT NOT NULL. `approval_id` is UNIQUE. UPDATE/DELETE triggers enforce append-only history. `evidence_json` preserves the reviewed pre-resolution quote; its embedded open ticket status is a historical fact, not the current ticket status. Reset removes this working extension by restoring the original nine-table DB.

### API, dashboard and limits

`GET /approvals/pending` now includes financial and internal-disposition proposals. `POST /approvals/{approval_id}/decision` executes the appropriate MCP action only after a named human approves; resolution responses explicitly report `cash_changed:false`. Agent tool permissions remain read-only. The dashboard shows the exact draft in the approval card and a verified-final-disposition card above the historical review. Arbitrary purchase orders are still unsupported and disabled.

All five AI roles use only **gpt-6-Luna through Portkey**. Per ticket review: at most 5 agent invocations, 3 delegations, depth 2, 12 MCP calls. Per agent invocation: 4 model requests, 6 tool calls, 8,000 total tokens; one output retry. Cycles are stopped; limits are not silently raised after a failure. The application runs one backend worker; use the offline supervisor only when other API instances are stopped. No model or MCP call receives permission to invent incoming revenue or contact customers/vendors.

Final evidence is generated from read-only verification of the DB and current audit generation using `scripts/finalize_evidence.py`, followed by independent MCP/SQL comparison with `scripts/verify_evidence.py`. Earlier evidence is under `output/prior_run/`; earlier audit records remain in place. Actual and Reflection discuss both correct behavior and observed mistakes; Expected plans are preserved. `scripts/capture_dashboard.mjs` captures the real resolved UI, checks mobile/reload behavior and all five standalone tabs. `scripts/scan_secrets.py` checks source/evidence and Git history without displaying secrets.

### IDE connection qualification

`.mcp.json` and the committed `.codex/config.toml` use the portable launcher. Open HW5 itself as the trusted project root and reload Codex/VS Code. Codex's configuration disables write tools in the IDE. `mcp_smoke.json` proves real stdio MCP calls with exact DB comparisons; it does not claim an IDE-host tool invocation. That final host step must be verified after reload.
