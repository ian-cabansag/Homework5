# HW5 final pre-submission audit — October 8, 2026

**Verdict: not ready for a fully compliant submission.** Tickets 101 and 103 remain open. Ticket 102 is resolved. This audit fixed concrete runtime, approval, documentation, and evidence defects; it did not manufacture final ticket dispositions. No changes from this audit were committed or pushed.

## Problems 1–11

| Problem | Result | Evidence / remaining gap |
|---|---|---|
| 1 — Prompt log | PASS | All eleven numbered sections exist. The setup summary is labeled as a summary; the current follow-up and its verbatim attached checklist are preserved. |
| 2 — Database | PASS | All nine source tables, every field, foreign keys, and source/working rows inspected in `database_audit.json`. Both DBs pass integrity and FK checks. Source hash unchanged. |
| 3 — MCP server | PASS | FastMCP exposes 11 tools. Real stdio discovery and all three ticket evidence tools succeed. Business SQL remains in MCP; independent SQL in diagnostic/test scripts is not a backend access path. |
| 4 — IDE connection and smoke | FAIL (IDE unverified) | Fresh real MCP stdio tests match every working-DB field; configuration commands are present. This session exposes no Campus Customs IDE tools, so the connected vibe-coder invocation requirement cannot be certified. A backend MCP client test is not represented as an IDE invocation. |
| 5 — Five-agent team and expanded tools | FAIL (completion capability) | Five role-specific PydanticAI agents, structured models, bounded delegation, read-only agent tools, and guarded payment execution exist and were inspected/tested. There is still no supported final disposition/fulfillment or pricing-override workflow to complete 101/103. |
| 6 — Expected plans | PASS | All five tabs work locally. The three original Expected sections compare unchanged against Git HEAD. Actual notes remain factual and partial. |
| 7 — FastAPI | PASS | Startup from `backend/`, database-backed ticket/cash reads, events, pending approvals, explicit payment approval, reset, input validation, and CORS tested. Agent-run wiring is inspected; no new paid model invocation was made. |
| 8 — Dashboard | PASS | React/Vite/TypeScript build and typecheck pass. Browser verifies real ticket selection/status, $160 balance, persisted review after reload, disabled resolved run action, mobile width 390, and no runtime exceptions. No new real payment was clicked in the browser; its API/MCP path is tested on copies. |
| 9 — Clean full resolution run | FAIL | Recorded state is Open / Resolved / Open. Clean reset and payments were tested on disposable DB copies. The submitted working DB was not reset and no new final three-ticket AI run was performed: known missing completion workflows would still prevent success. |
| 10 — Reflection | PASS | Specific analysis of the actual ticket routes, duplicate reads, blocked delegation cycle, cash, one-agent alternatives, three distinct new supported inquiries, and three unsupported tasks with needed capabilities. |
| 11 — Final submission | FAIL | Required named files and both DBs exist, and real screenshots now exist locally. Two tickets remain unresolved; the public repository still contains the earlier submission, not these uncommitted audit fixes. No push performed, as requested. |

## Component checks

| Component | Result | Scope |
|---|---|---|
| Folder structure | PASS | All requested files plus useful tests, scripts, and local screenshot assets present. |
| Database integrity | PASS | Original and working integrity/FK checks; original unchanged. |
| MCP | PASS | Real protocol discovery and field-by-field verification for all three initial tools. IDE-host connection remains unverified above. |
| Agents | PASS | Five configured PydanticAI roles, prompts, delegation limits, model wiring; completion-tool gap remains under Problem 5. |
| gpt-6-Luna only | PASS | Only executable model configuration is gpt-6-Luna via Portkey. Other names in the verbatim user checklist are quoted exclusions, not configured models. |
| Safety | PASS | For implemented invoice/lease actions: no agent payment permission, one-time token, finite cents, exact approved amount, duplicate/negative-cash rejection, desk date, vendor eligibility, drafts only. |
| Human approval | PASS | Recorded payments name Ian; isolated tests verify name/decision requirements, rejection, concurrent approval, and reset invalidation. |
| Backend | PASS | Python compilation/import, startup, read/approval/reset paths and CORS. |
| Frontend | PASS | TypeScript, production bundle, real browser checks/screenshots. |
| Ticket resolution | FAIL | 101 and 103 remain open. |
| Cash reconciliation | PASS | $3,400.00 − $840.00 − $2,400.00 − $0.00 = $160.00, exactly matching DB and result file. |
| Output evidence | FAIL (completed-run target) | Current-state evidence is consistent and includes three real screenshots, but cannot demonstrate three resolved tickets. |
| Secrets | PASS | Current project/evidence and all reachable Git-history blobs scanned, including exact in-memory comparison with the configured key. No matches; real .env untracked; both DBs tracked. See `security_check.json`. |
| GitHub readiness | FAIL (submission completeness) | Source/evidence can be reviewed locally, but open-ticket requirements remain and this audit is intentionally unpublished. |

## Changes made

1. `backend/main.py`, `backend/audit.py`: serialized approvals with reset/run operations; reset boundaries invalidate earlier approval IDs and separate current events from preserved history. Added `include_history=true` to the events route.
2. `mcp_server/server.py`: bound execution to the human-reviewed amount, rejected non-finite/non-cent financial records, and supplied the authoritative desk date independently of the cash date.
3. `backend/mcp_client.py`: used an async exit stack so sessions and subprocess contexts unwind even on MCP errors or initialization failures.
4. `backend/models.py`, `backend/orchestrator.py`: aligned valid agent/audit summary lengths, rejected non-finite approval amounts, enforced the shared MCP-call cap before incrementing, checked proposed amounts exactly, and persisted future full outcomes/drafts in the audit.
5. `frontend/src/App.tsx`, `frontend/src/types.ts`: corrected initial connection and desk-date display, restored historical reviews after reload, distinguished review snapshots from later actions, and exposed stored internal drafts.
6. Root/backend `requirements.txt`: added explicit Pydantic and corrected the declared SDK versions to match the tested runtime. The prior ranges excluded installed PydanticAI 1.107.6 and OpenAI SDK 3.19.2. The slim PydanticAI OpenAI extra supplies the same API without unrelated providers.
7. `scripts/reset_working_db.py`, README, harness, MCP README, design notes: documented a reset that also invalidates stale approvals, actual tools/tables, SDK setup, current-versus-source balances, verification commands, and remaining limits.
8. `tests/test_safety.py`: eleven regression tests on disposable fixtures. `scripts/verify_evidence.py` generates fresh independent DB/MCP checks and preserves the earlier smoke capture. `scripts/scan_secrets.py` checks files and Git history without printing secrets.
9. `scripts/capture_dashboard.mjs`, `output/dashboard_screenshots/`, `output/dashboard_browser_check.json`, `output/resolved_board.html`: captured and embedded three actual React dashboard screenshots. The board works with local relative assets and accurately labels open tickets.
10. `output/resolved_tickets.json`: renamed historical `run_status` to `initial_agent_run_status` to distinguish it from current `final_status`; no outcomes changed. `output/desk_tickets.html`: replaced recycled future-task examples with distinct, supported inquiries; Expected sections unchanged.
11. `AI_prompts.md`, `output/pre_submission_request.txt`: recorded the actual repeated-audit request and earlier omissions. `.gitignore` now excludes disposable `.audit-tools/` data. New `database_audit.json`, archived `mcp_smoke_initial.json`, refreshed `mcp_smoke.json`, and `security_check.json` hold verification evidence.

## Tests and preserved evidence

- `python -m unittest discover -s tests -v`: **11 tests passed**. Test payments and synthetic operator decisions exist only in disposable test copies/journals, not the submitted business DB or audit.
- `npm run typecheck` and `npm run build`: passed; final Vite production bundle built successfully.
- `python -m compileall -q backend mcp_server scripts tests`: passed.
- Real MCP smoke verification: 11 tools discovered; three initial tools called and every returned field matched independent read-only SQL. No AI calls.
- Real browser: three ticket selections, actual statuses/balance, restored review after reload, 390px no-overflow check, five standalone HTML tabs, zero runtime exceptions. Separate validation backend used port 8001; default app URL remains localhost:8000. Test servers/browser stopped afterward.
- `pip check`: no broken installed requirements. Declared requirements were corrected to the tested versions; a brand-new environment installation was not performed.
- All **77 original operational audit records remain unchanged**. No historical agent drafts or events were fabricated. Both submitted DB files are unchanged by this audit.
- Original SHA-256: `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`.

## Remaining actions before a complete submission

1. Establish and implement legitimate internal completion outcomes for 101 and 103 consistent with shop rules. Current tools cannot confirm fulfillment, reserve/receive goods, or authorize a discount. Keeping the tickets open was the previously selected conservative disposition; this audit does not override it.
2. After those workflows exist, perform the requested clean three-ticket run, obtain the required human approvals for that run, and refresh all run/cash/reflection/screenshot evidence. The existing approved payments must not be replayed as new decisions merely to make the files appear complete.
3. Open HW5 as the MCP host's project root with its Python environment active, reload the host's MCP configuration, and verify the three tools from the actual IDE connection. Current evidence verifies stdio MCP only.
4. Review and publish the final local changes when authorized. This audit did not commit or push. The recorded public URL is `https://github.com/ian-cabansag/Homework5`.

Fresh Portkey availability, a new full real-agent run, a connected IDE invocation, and a clean-machine dependency installation are not certified by this audit. Zero new AI requests or live financial actions were used for verification.
