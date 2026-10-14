"""Run a bounded, auditable five-role team for one explicitly requested ticket."""

from uuid import uuid4

from pydantic_ai import UsageLimits

from backend.agents import (
    MAX_AGENT_RUNS,
    MAX_DELEGATIONS,
    MAX_DELEGATION_DEPTH,
    MAX_MCP_CALLS,
    AgentBudget,
    AgentDeps,
    build_agents,
)
from backend.audit import AuditTrail
from backend.mcp_client import MCPGateway
from backend.models import (
    AgentEvent,
    AgentReply,
    AgentRole,
    DelegationRequest,
    TicketOutcome,
)


async def run_ticket(
    ticket_id: int,
    instruction: str | None,
    mcp: MCPGateway,
    audit: AuditTrail,
) -> TicketOutcome:
    run_id = str(uuid4())
    budget = AgentBudget()
    agents = {}
    specialist_reports: list[dict[str, object]] = []

    async def run_role(
        role: AgentRole,
        task: str,
        visited: tuple[AgentRole, ...],
        depth: int,
    ) -> AgentReply:
        if budget.agent_runs >= MAX_AGENT_RUNS:
            raise RuntimeError("The ticket run reached its agent invocation limit.")
        budget.agent_runs += 1
        await audit.append(AgentEvent(
            run_id=run_id,
            ticket_id=ticket_id,
            agent=role,
            event_type="agent_started",
            summary=f"{role.value} started a bounded ticket task.",
            details={"delegation_depth": depth, "visited_roles": [item.value for item in visited]},
        ))

        async def delegate(request: DelegationRequest) -> dict[str, object]:
            if request.target in visited:
                reason = "Delegation denied to prevent a role cycle."
                await audit.append(AgentEvent(
                    run_id=run_id,
                    ticket_id=ticket_id,
                    agent=role,
                    delegated_to=request.target,
                    event_type="delegation_stopped",
                    summary=reason,
                    details={"reason": request.reason},
                ))
                return {"delegation": "stopped", "reason": reason}
            if depth >= MAX_DELEGATION_DEPTH or budget.delegations >= MAX_DELEGATIONS:
                reason = "Delegation denied because the ticket run reached its delegation limit."
                await audit.append(AgentEvent(
                    run_id=run_id,
                    ticket_id=ticket_id,
                    agent=role,
                    delegated_to=request.target,
                    event_type="delegation_stopped",
                    summary=reason,
                    details={"reason": request.reason},
                ))
                return {"delegation": "stopped", "reason": reason}

            budget.delegations += 1
            await audit.append(AgentEvent(
                run_id=run_id,
                ticket_id=ticket_id,
                agent=role,
                delegated_to=request.target,
                event_type="delegation_started",
                summary=request.reason,
                details={"task": request.task, "depth": depth + 1},
            ))
            report = await run_role(
                request.target,
                f"Ticket {ticket_id}. {request.task}\nDelegation reason: {request.reason}",
                visited + (request.target,),
                depth + 1,
            )
            record: dict[str, object] = {
                "agent": request.target.value,
                "summary": report.summary,
                "status": report.status,
                "evidence_refs": report.evidence_refs,
                "recommendations": report.recommendations,
                "drafts": report.drafts,
                "approval_requests": [item.model_dump(mode="json") for item in report.approval_requests],
                "resolution_requests": [item.model_dump(mode="json") for item in report.resolution_requests],
            }
            specialist_reports.append(record)
            await audit.append(AgentEvent(
                run_id=run_id,
                ticket_id=ticket_id,
                agent=role,
                delegated_to=request.target,
                event_type="delegation_completed",
                summary=f"{request.target.value} returned a specialist report.",
                details={"result_summary": report.summary},
            ))
            return record

        dependencies = AgentDeps(
            role=role,
            ticket_id=ticket_id,
            run_id=run_id,
            mcp=mcp,
            audit=audit,
            budget=budget,
            visited=visited,
            delegation_depth=depth,
            delegate=delegate,
        )
        run_prompt = (
            f"Handle only ticket {ticket_id}.\n"
            f"Task: {task}\n"
            f"Operator context: {instruction or 'No additional instruction.'}\n"
            "Read the relevant database evidence using your MCP tool before stating shop facts. "
            "Delegate only when another role's expertise is needed. Return the required structured response."
        )
        previous_mcp_calls = budget.role_mcp_calls.get(role, 0)
        try:
            result = await agents[role].run(
                run_prompt,
                deps=dependencies,
                usage_limits=UsageLimits(
                    request_limit=4,
                    tool_calls_limit=6,
                    total_tokens_limit=8000,
                ),
            )
        except Exception as error:
            await audit.append(AgentEvent(
                run_id=run_id,
                ticket_id=ticket_id,
                agent=role,
                event_type="agent_failed",
                summary=f"Agent run stopped after {type(error).__name__}.",
                details={"stop_reason": type(error).__name__},
            ))
            raise

        reply: AgentReply = result.output
        if budget.role_mcp_calls.get(role, 0) == previous_mcp_calls:
            await audit.append(AgentEvent(
                run_id=run_id,
                ticket_id=ticket_id,
                agent=role,
                event_type="agent_failed",
                summary="Agent stopped because it returned without reading MCP evidence.",
            ))
            raise RuntimeError(f"{role.value} returned without consulting MCP evidence.")
        await audit.append(AgentEvent(
            run_id=run_id,
            ticket_id=ticket_id,
            agent=role,
            event_type="agent_completed",
            summary=reply.summary,
            details={
                "status": reply.status,
                "evidence_refs": reply.evidence_refs,
                "recommendation_count": len(reply.recommendations),
                "draft_count": len(reply.drafts),
                "approval_request_count": len(reply.approval_requests),
            },
        ))
        return reply

    await audit.append(AgentEvent(
        run_id=run_id,
        ticket_id=ticket_id,
        agent=AgentRole.BOSS,
        event_type="ticket_run_started",
        summary="Started a single-ticket operations review.",
    ))

    try:
        agents.update(build_agents())
        reply = await run_role(
            AgentRole.BOSS,
            "Triage this ticket, gather evidence, delegate only to specialists that materially help, and return the operational outcome.",
            (AgentRole.BOSS,),
            0,
        )
        approval_ids: list[str] = []
        for request in reply.approval_requests:
            if budget.mcp_calls >= MAX_MCP_CALLS:
                await audit.append(AgentEvent(
                    run_id=run_id,
                    ticket_id=ticket_id,
                    agent="System",
                    event_type="approval_proposal_stopped",
                    summary="Approval proposal stopped at the MCP call limit.",
                ))
                break
            budget.mcp_calls += 1
            quote = await mcp.call_agent_tool(
                "get_payment_quote",
                {"kind": request.payment_kind, "ref_id": request.reference_id},
            )
            if (
                not quote.get("can_pay_if_human_approved")
                or float(quote.get("amount", -1)) != request.amount
            ):
                await audit.append(AgentEvent(
                    run_id=run_id,
                    ticket_id=ticket_id,
                    agent=AgentRole.ACCOUNTING,
                    event_type="approval_proposal_blocked",
                    tool_name="get_payment_quote",
                    summary="Approval proposal did not match an eligible database payment quote.",
                    details={"request": request.model_dump(mode="json"), "quote": quote},
                ))
                continue

            approval_id = str(uuid4())
            approval_ids.append(approval_id)
            await audit.append(AgentEvent(
                run_id=run_id,
                ticket_id=ticket_id,
                agent=AgentRole.ACCOUNTING,
                event_type="approval_requested",
                tool_name="get_payment_quote",
                approval_id=approval_id,
                summary="Payment proposal is awaiting explicit human approval; no cash has moved.",
                details={
                    "request": request.model_dump(mode="json"),
                    "authoritative_quote": quote,
                },
            ))

        for request in reply.resolution_requests:
            if request.ticket_id != ticket_id:
                raise ValueError("Resolution proposal must belong to the active ticket.")
            if budget.mcp_calls >= MAX_MCP_CALLS:
                raise RuntimeError("Resolution quote exceeds the MCP call budget.")
            budget.mcp_calls += 1
            quote = await mcp.call_agent_tool("get_ticket_resolution_quote", {"ticket_id": ticket_id})
            eligible = quote.get("can_finalize_if_human_approved") is True
            approval_id = str(uuid4()) if eligible else None
            if approval_id:
                approval_ids.append(approval_id)
            await audit.append(AgentEvent(
                run_id=run_id, ticket_id=ticket_id, agent=AgentRole.BOSS,
                event_type="approval_requested" if eligible else "approval_proposal_blocked",
                tool_name="get_ticket_resolution_quote", approval_id=approval_id,
                summary="Internal disposition requires human approval; no fulfillment or cash change." if eligible else str(quote["blocked_reason"]),
                details={"request": {"payment_kind": "ticket_resolution", "reference_id": ticket_id,
                                     "amount": 0, "rationale": request.rationale},
                         "authoritative_quote": quote},
            ))

        outcome = TicketOutcome(
            run_id=run_id,
            ticket_id=ticket_id,
            status="needs_approval" if approval_ids else reply.status,
            summary=reply.summary,
            evidence_refs=reply.evidence_refs,
            recommendations=reply.recommendations,
            drafts=reply.drafts,
            pending_approval_ids=approval_ids,
            specialist_reports=specialist_reports,
            agent_invocations=budget.agent_runs,
            mcp_calls=budget.mcp_calls,
            delegation_count=budget.delegations,
            stop_reason=(
                "Outcome prepared; all requested specialist work returned and any payment request is pending human approval."
                if approval_ids
                else "Outcome prepared; no payment was executed."
            ),
        )
        await audit.append(AgentEvent(
            run_id=run_id,
            ticket_id=ticket_id,
            agent=AgentRole.BOSS,
            event_type="ticket_run_stopped",
            summary=outcome.stop_reason,
            details={"status": outcome.status, "pending_approval_ids": approval_ids,
                     "outcome": outcome.model_dump(mode="json")},
        ))
        return outcome
    except Exception as error:
        await audit.append(AgentEvent(
            run_id=run_id,
            ticket_id=ticket_id,
            agent="System",
            event_type="ticket_run_stopped",
            summary=f"Ticket run stopped after {type(error).__name__}.",
            details={"stop_reason": type(error).__name__},
        ))
        raise
