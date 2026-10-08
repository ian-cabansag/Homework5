# AI Prompts

This file records the prompts and follow-ups used for each numbered HW5 problem.

## Problem 1 — Inspect the workspace and start the prompt log

**Prompt:**

> For now, only inspect the workspace, create AI_prompts.md if it does not exist, and tell me you are ready for Problem 2. Do not start later problems yet.

**Follow-up:** None.

## Problem 2 — Study the Campus Customs database

**Prompt:**

> Problem 2: Study the Campus Customs database.
>
> Please inspect data/campus_customs.db thoroughly: every table, every field, relationships between the tables, and the actual rows that matter to the open tickets.
>
> Create data/campus_customs_new.db as a clean copy of the original database. Do not modify data/campus_customs.db.
>
> Pay particular attention to the three open tickets 101, 102, and 103 and trace how each ticket connects to the relevant inventory, pricing, vendor, lease, cash, payment, invoice, desk, or other data.
>
> Start output/harness.md. For every table, record:
> - table name
> - its fields
> - one short practical explanation of why that table matters to this agent system
>
> Also note the current desk.date_today value and the current checking/cash balance because later logic will depend on those.
>
> Do not build agents or solve tickets yet. This problem is only about understanding the database, creating the working copy, and documenting it accurately from the real DB.

**Follow-up:** None so far.

## Problem 3 — Build the MCP server

**Prompt:**

> Problem 3: Build the MCP server.
>
> Create an MCP server under mcp_server/ using FastMCP. It must read from data/campus_customs_new.db, never the original database.
>
> For this first version, create exactly three useful, clearly named tools based on the actual three open tickets you inspected in Problem 2.
>
> Choose tools that unlock meaningful facts needed for tickets 101, 102, and 103 instead of making three vague generic database readers. Each tool should have a focused purpose, validated arguments where appropriate, structured/clear output, and no hallucinated information.
>
> Do not solve the tickets yet and do not update the database yet unless a read is explicitly needed for the tool. These first tools should give the later agents the evidence they need to reason about the tickets.
>
> Update output/harness.md with, for each of the three tools:
> - tool name
> - which table or tables it reads
> - which ticket (101, 102, or 103) it helps unlock
> - one sentence explaining why that tool is the right tool for that ticket
>
> Also create mcp_server/README.md explaining:
> - what the MCP server is for
> - which database it uses
> - how to run it
> - the three tools and what each does
>
> Keep the implementation small and understandable, but production-minded enough that we can grow it in Problem 5.

**Follow-up:** None so far.

## Problem 4 — Connect the MCP server and test its tools

**Prompt:**

> Problem 4: Connect this project’s MCP server to my vibe coder and test all three tools.
>
> Create the appropriate project-level MCP configuration, preferably .mcp.json at the HW5 project root if that is supported here, pointing to the local FastMCP server we created.
>
> Use paths/commands that will work from this project rather than machine-specific hardcoded absolute paths wherever possible.
>
> Then test each of the three MCP tools through the connected MCP interface.
>
> Create output/mcp_smoke.json. For each tool test, include:
> - the prompt/request used to trigger the tool
> - the tool name
> - the returned tool output
>
> Verify every returned value directly against data/campus_customs_new.db before saving the smoke test evidence. Do not fabricate successful results. If the MCP configuration requires Codex or the workspace to be reloaded before the tools become available, stop after creating the configuration and tell me exactly what I need to reload. Do not fake the MCP calls.

**Follow-up:** None so far.

## Problem 5 — Build the five-agent operations team and expand MCP tools

**Prompt:**

> Problem 5: Build the five-agent Campus Customs operations team and expand the MCP tools.
>
> Build the agentic team using PydanticAI with these five distinct roles:
>
> - Boss
> - Inventory
> - Accounting
> - Facilities
> - Customer Service
>
> Use only gpt-6-Luna through Portkey for every single agent. There should be no other model name in this project.
>
> Put each agent’s system prompt in its own file under backend/prompts/:
> - boss.md
> - inventory.md
> - accounting.md
> - facilities.md
> - customer_service.md
>
> Make the prompts detailed and operational rather than generic. Each role should understand its scope, the shop rules that matter to it, when to delegate, what it must never do, and how to use factual MCP evidence.
>
> The agents need full connectivity: an agent should be able to delegate to another specialist when needed. But do not create pointless agent chatter. The Boss should route intelligently and specialists should only involve other specialists when their expertise is actually needed.
>
> Add the structured Pydantic/PydanticAI types needed for tickets, agent events, delegations, tool results, approvals, outcomes, and other useful structured state to backend/models.py.
>
> All business/database tools must remain in the MCP layer and use data/campus_customs_new.db. Do not create a secret second database-access layer in backend that bypasses MCP.
>
> Grow the MCP server with any additional read or write tools the agents genuinely need to solve tickets 101, 102, and 103. Preserve the shop rules:
> - shop date = desk.date_today
> - vendor lead times come from vendors
> - vendor cannot ship new product while an invoice to that vendor remains unpaid
> - payments always require human approval before money moves
> - payment must refuse if cash would go negative
> - no incoming revenue
> - no real emails or real vendor calls
> - factual shop values come from the DB, not agent guesses
>
> Wire the team so every meaningful agent-loop step appends an audit record to output/audit_trail.json instead of overwriting it. Record enough to understand later which agent acted, what it delegated or attempted, which MCP tool was used, a concise result, and the stop/outcome reason. Do not store hidden chain-of-thought; record useful operational summaries instead.
>
> Update output/harness.md with:
> - each of the five agents and its responsibility
> - every MCP tool now available
> - which tables each tool uses
> - safety and approval guardrails
> - practical loop/delegation limits to prevent runaway token usage
> - confirmation that all AI agents use only gpt-6-Luna
>
> Update mcp_server/README.md so its tool list matches the finished MCP server.
>
> Do not run all three tickets yet. We are building the system here, not doing the final run.

**Follow-up:** None so far.

## Problem 6 — Plan the three open tickets

**Prompt:**

> Problem 6: Plan the three open tickets before we run the agents.
>
> Use the actual database facts we inspected for tickets 101, 102, and 103. Do not resolve them yet.
>
> Create output/desk_tickets.html as a polished standalone page I can double-click.
>
> Give it five tabs:
> - Ticket 101
> - Ticket 102
> - Ticket 103
> - Cash
> - Reflection
>
> For now, Cash and Reflection can be empty or show a subtle “coming after the run” state.
>
> For each ticket tab, create an Expected section only and leave a clearly reserved Actual section for Problem 9.
>
> The Expected section must explain, based on the real ticket:
> - which specialist the Boss should delegate to first and why
> - every additional agent delegation that is actually justified
> - which MCP tools should probably be used
> - the expected decision/workflow
> - where human approval should occur if money or a purchase is involved
>
> Do not send all five agents to every ticket. I want efficient routing that reflects the problem rather than a generic multi-agent swarm.
>
> Make this page visually excellent even though it is primarily evidence: clean typography, calm spacing, compact status chips, strong information hierarchy, easy tab navigation, and a minimalist operations-desk aesthetic. Keep everything local so I can double-click the HTML.
>
> Do not perform the actual ticket runs yet.

**Follow-up:** None so far.

## Problem 7 — Build the FastAPI dashboard routes

**Prompt:**

> Problem 7: Build the FastAPI routes the dashboard will use.
>
> In backend/main.py, expose a FastAPI application that integrates the multi-agent system and working database/MCP setup.
>
> At minimum I need routes that can:
>
> 1. return tickets 101, 102, and 103 with open/resolved status
> 2. accept a ticket id and start/run the agent team on that ticket
> 3. return recent agent events so the UI can show what each agent said/did and which tools were used
> 4. expose pending human approvals for a payment or purchase and allow a human to approve one
> 5. ensure only the explicit approval route actually executes a payment / cash-changing action
> 6. return the current checking balance from cash_accounts
> 7. reset data/campus_customs_new.db back to the original data/campus_customs.db for a clean run
>
> Make the endpoints structured and frontend-friendly with appropriate Pydantic request/response models.
>
> Preserve all safety rules. In particular, an agent may prepare/propose a payment or purchase, but must not actually move money before the human approval endpoint is called. Reject anything that would create a negative cash balance.
>
> Set up CORS so the React app we build next can call localhost:8000.
>
> Update output/harness.md with a compact API section listing each route, method, and what it does.
>
> Make sure the backend can be started from backend/ using:
>
> `uvicorn main:app --reload --port 8000`
>
> Do not run the final three-ticket test yet.

**Follow-up:** None so far.

## Problem 8 — Build the React operations dashboard

**Prompt:**

> Problem 8: Build the React operations dashboard.
>
> Create the frontend in frontend/ using React + Vite + TypeScript and connect it to the FastAPI backend at http://localhost:8000.
>
> This should feel like a real operations desk, not a classroom CRUD page.
>
> At minimum the dashboard needs to:
> - show all three tickets and their current open/resolved states
> - let me select a ticket and start its agent team
> - show live/recent activity so I can see which agent is working, what it is doing, delegations, and MCP/tool usage
> - visually distinguish Boss, Inventory, Accounting, Facilities, and Customer Service
> - show a concise outcome/summary when the run finishes
> - surface pending payment or purchase approvals and give the human a clear Approve action
> - never imply money moved until that approval actually succeeds
> - show the current checking balance prominently enough to monitor it
> - refresh states cleanly after actions
> - clearly show when a ticket becomes resolved
>
> For the design, be creative but restrained. I prefer minimalist, calm, premium-looking interfaces.
>
> I want something closer to a modern mission-control / operations workspace than a colorful admin template:
> - generous whitespace
> - excellent typography
> - subtle depth instead of heavy borders
> - restrained motion
> - crisp status chips
> - compact but readable event timeline
> - quiet visual differentiation between agents
> - tasteful micro-interactions
> - a cash/balance treatment that communicates financial impact without becoming a giant finance dashboard
> - a clean approval drawer/card that makes high-impact actions deliberate
> - responsive layout that still looks excellent on a laptop
> - no neon cyberpunk look, excessive gradients, glassmorphism everywhere, giant rounded cards, or visual clutter
>
> Add thoughtful empty, loading, processing, success, and error states.
>
> The dashboard should be something I could plausibly leave open while supervising an agent team.
>
> Create output/design.md explaining the major visual/interaction choices, how agents read differently, how resolved tickets and cash changes appear, and the small creative details that make the dashboard feel intentional.
>
> Run a frontend build/typecheck and fix obvious errors before calling this complete.

**Follow-up:** None so far.

## Problem 9 — Perform the clean full run and resolve all three tickets

**Prompt:**

> Problem 9: Perform the clean full run and resolve all three tickets.
>
> Before doing anything else, reset data/campus_customs_new.db from the untouched original data/campus_customs.db so we have a clean starting point.
>
> Record the exact starting checking balance from the reset working database.
>
> Then run tickets 101, 102, and 103 through the real multi-agent system until each reaches its legitimate final resolved state.
>
> Use the real MCP tools and real working database. Do not fabricate agent events or manually invent resolved outcomes.
>
> Respect human approval. If a ticket produces a pending payment or purchase, use the same human-approval flow the dashboard is supposed to expose before the actual financial action occurs.
>
> After the runs:
>
> 1. Update output/desk_tickets.html. Keep every Expected section from Problem 6 intact. Fill each Actual section with participating agents, actual delegations, MCP tools used, material decisions/actions, final result, and any human approval.
>
> 2. Fill the Cash tab with exact auditable starting balance, per-ticket cash changes and causes, payment amounts, ending checking balance, and arithmetic that agrees with the working DB.
>
> 3. Save output/resolved_tickets.json with one structured record per ticket: id, final status, short outcome, agent contributions, and human approvals.
>
> 4. Create output/resolved_board.html as a standalone page showing real React dashboard screenshots for tickets 101, 102, and 103, using local relative assets. If screenshots require manual capture, ask for the exact screenshots instead of inventing them.
>
> 5. Append real run events to output/audit_trail.json without wiping earlier entries.
>
> 6. Finish output/harness.md with database tables, MCP tools, agents, delegation, API routes, dashboard, approvals, audit, safety, model/token limits, and reset/full-run process.
>
> Finally check consistency across ticket statuses, resolved_tickets.json, desk_tickets.html, audit_trail.json, cash_accounts, and dashboard/backend state. Do not say the task is complete if they disagree.
>
> Do not claim completion unless those agree.

**Follow-up:**

> okay go approve
>
> Ian

>
> do the best recommendation you have. then lets wrap up with the github as well

The missing element after the initial run was explicit human authorization and an approver name; both payments were later executed through the approval route, while ticket resolution and fulfillment evidence remain outstanding. The failed ticket 101 attempt and retry are both retained in the append-only audit trail.

## Problem 10 — Complete the Reflection tab

**Prompt:**

> Problem 10: Complete the Reflection tab in output/desk_tickets.html.
>
> Base everything on the actual system we built and the real runs of tickets 101, 102, and 103. Read their Expected and Actual sections, the Cash tab, resolved_tickets.json, audit_trail.json, and the relevant database changes before writing.
>
> Write the reflection in a natural first-person student voice. Keep it analytical and specific rather than overly polished or generic.
>
> For each ticket, evaluate:
> - how well the agent team performed
> - what worked well
> - anything inefficient, unnecessary, or wrong
> - how Actual compared with the Expected plan and why
> - whether delegation helped or added unnecessary coordination
>
> Then answer:
> - what parts of these tasks would have been simpler using one capable agent with tools instead of five agents, and why
> - three realistic new Campus Customs problems this existing agent team could solve with the tools we already built
> - three realistic new Campus Customs problems it could NOT currently solve
> - for each unsupported problem, which new tools, data, and/or agent capability would be needed
>
> Tie every point to concrete Campus Customs details from this project. Mention actual tickets, tools, decisions, cash effects, delegation patterns, or limitations when relevant.
>
> Avoid generic claims about “AI efficiency” that could apply to any project.
>
> Keep the page’s existing design and make the Reflection tab easy to read.

**Follow-up:** None so far.

## Problem 11 — Finalize the project and prepare it for GitHub submission

**Prompt:**

> Problem 11: Finalize the project and prepare it for GitHub submission.
>
> Do a full audit of the HW5 folder against the assignment deliverables before committing anything.
>
> The public repository needs to include the completed project, including at minimum:
>
> - AI_prompts.md
> - requirements.txt
> - .env.example
> - .gitignore
> - .mcp.json
> - README.md
>
> data/
> - campus_customs.db
> - campus_customs_new.db
>
> mcp_server/
> - server.py
> - README.md
>
> frontend/
> - the full React + Vite + TypeScript app needed to run the dashboard
>
> backend/
> - main.py
> - models.py
> - all additional agent/runtime files we actually use
> - prompts/
>   - boss.md
>   - inventory.md
>   - accounting.md
>   - facilities.md
>   - customer_service.md
>
> output/
> - harness.md
> - mcp_smoke.json
> - desk_tickets.html
> - design.md
> - resolved_tickets.json
> - resolved_board.html
> - any local screenshot assets referenced by resolved_board.html
> - audit_trail.json
> - github_url.txt
>
> Extra implementation files that are genuinely required are fine. Do not delete working code just to make the tree look identical.
>
> Do not commit the real .env, PORTKEY_API_KEY, or any secret. Search the repository for accidental keys, ensure .env is ignored, and use placeholders in .env.example. Search the codebase and confirm gpt-6-Luna is the only configured AI model.
>
> README.md needs clear reproducible instructions for:
> 1. installing Python dependencies
> 2. installing frontend dependencies
> 3. setting PORTKEY_API_KEY
> 4. copying/resetting the original database to the working database for a clean run
> 5. starting the MCP server
> 6. starting the FastAPI backend
> 7. starting the React dashboard
> 8. performing/resetting a three-ticket run
> 9. where the evidence/output files are
>
> Run reasonable validation before committing:
> - Python syntax/import checks where possible
> - frontend build/typecheck
> - confirm required output files exist
> - confirm both DB files exist
> - confirm cash/result files remain internally consistent
>
> Then initialize/use Git, commit the project, and push it to a PUBLIC GitHub repository. After a successful push, save the exact public repository URL to output/github_url.txt and provide the Canvas URL.
>
> If GitHub authentication, repository creation, or any external confirmation requires me to take an action, stop at that exact step and tell me what to do instead of pretending the push succeeded.

**Follow-ups:**

> okay do whatever it takes to succeed
>
> https://github.com/ian-cabansag/Homework5
>
> okay go approve
>
> Ian

The first audit was missing the target repository and explicit payment decisions; both payments are now recorded, but the tickets still lack legitimate final dispositions and screenshot evidence. The conservative disposition is to keep 101 and 103 open rather than fabricate fulfillment or a customer decision.
