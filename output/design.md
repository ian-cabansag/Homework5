# Operations dashboard design

The dashboard is organized like a small live operations desk: a narrow ticket queue on the left, the selected ticket and its activity stream in the center, and a deliberate human-approval lane on the right. The checking balance sits above the work area as a quiet but persistent monitor rather than taking over the page.

The visual language uses warm paper neutrals, soft green for safe/ready states, and muted amber or clay for pending/high-impact states. Hairline separators and low shadows provide structure without the heavy card-grid look. Type is split between a compact mono face for timestamps/status metadata and a humanist sans for readable work summaries.

Agents are distinguished with small letter marks and restrained, consistent tints: Boss in ochre, Inventory in leaf, Accounting in slate blue, Facilities in muted violet, and Customer Service in clay. The same key appears in the queue, activity feed, and delegation events, making handoffs scannable without turning the workspace into a rainbow.

Events and pending approvals refresh every four seconds; the ticket list and cash position refresh every twenty seconds, with a full refresh after actions. This keeps the event stream responsive without repeatedly starting MCP database subprocesses just to repaint the balance. The activity stream shows the actor, event type, concise summary, delegation target, and MCP tool name when present. A run produces a separate outcome card with status and compact counts. A ticket whose API status is `resolved` gets a green resolved chip and its run action is disabled; the dashboard does not imply completion merely because a model run ended.

Payment proposals include the quoted amount, expected post-payment balance when available, and a final human-name field. Approve/Decline are disabled until a name is supplied; a blocked database quote cannot be approved. After approval, the interface changes its cash-success message only when the API returns `cash_changed: true`, then refreshes the balance. A failed or rejected approval never claims that money moved. The approval lane repeats the transaction-time cash recheck safeguard in plain language.

The current API/database implementation supports executable invoice and lease payments. A future purchase proposal can be shown in the approval lane, but its Approve action stays disabled until a purchase-order operation exists; the UI will not pretend the present payment endpoint can place or pay for an order.

Small intentional details include a timestamp for the last successful sync, a 4-second activity heartbeat, a date tied to the desk/database, ticket indexing, “drafts stay internal” language, and reduced-motion support. Loading, no-activity, no-approval, disconnected, processing, completed, and error states are all designed into the same visual system. The layout collapses into a ticket strip and stacked approval lane on smaller screens while keeping the work stream central.

The frontend is local React + Vite + TypeScript and calls only the FastAPI routes on `http://localhost:8000`. It uses no remote images or UI service; the icon set is bundled with the app.
