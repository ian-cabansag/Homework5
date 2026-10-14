"""FastAPI entry point for running one ticket and processing human approvals."""

import secrets
import sys
import asyncio
from pathlib import Path as FilePath
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Path as ApiPath, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = FilePath(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.audit import AuditTrail
from backend.mcp_client import MCPGateway
from backend.models import AgentEvent, ApprovalDecision, Ticket, TicketOutcome, TicketRunRequest
from backend.orchestrator import run_ticket


app = FastAPI(title="Campus Customs Operations", version="1.0.0")
audit = AuditTrail()
operation_lock = asyncio.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class TicketListResponse(BaseModel):
    tickets: list[Ticket]


class AgentEventsResponse(BaseModel):
    events: list[AgentEvent]
    total: int = Field(ge=0)


class PendingApprovalsResponse(BaseModel):
    approvals: list[AgentEvent]


class CheckingBalanceResponse(BaseModel):
    account: dict[str, str | float]


class ApprovalDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    approval_id: str
    decision: str
    cash_changed: bool
    payment: dict[str, object] | None = None


class ResetResponse(BaseModel):
    reset: bool
    database: str
    integrity_check: str


class ResetRequest(BaseModel):
    confirm: bool


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "database_access": "MCP only"}


@app.get("/tickets", response_model=TicketListResponse)
async def list_tickets() -> TicketListResponse:
    try:
        async with MCPGateway() as gateway:
            data = await gateway.call_api_read_tool("get_dashboard_tickets")
        return TicketListResponse.model_validate(data)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Could not read dashboard tickets through MCP.") from error


@app.post("/tickets/{ticket_id}/run", response_model=TicketOutcome)
async def run_one_ticket(
    ticket_id: Annotated[int, ApiPath(ge=101, le=103)],
    request: TicketRunRequest | None = None,
) -> TicketOutcome:
    """Review exactly one ticket; this endpoint never executes a payment."""
    try:
        async with MCPGateway() as gateway:
            names = await gateway.list_tool_names()
            required = {
                "get_ticket_101_tee_reprint_context",
                "get_ticket_102_rent_and_cash_context",
                "get_ticket_103_hoodie_stock_and_pricing",
                "get_payment_quote",
            }
            missing = required - names
            if missing:
                raise RuntimeError(f"MCP server is missing required tools: {sorted(missing)}")
            async with operation_lock:
                return await run_ticket(ticket_id, request.instruction if request else None, gateway, audit)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Ticket review stopped ({type(error).__name__}); see output/audit_trail.json.",
        ) from error


@app.get("/events", response_model=AgentEventsResponse)
async def recent_events(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ticket_id: Annotated[int | None, Query(ge=101, le=103)] = None,
    include_history: bool = False,
) -> AgentEventsResponse:
    events = audit.events() if include_history else audit.current_events()
    if ticket_id is not None:
        events = [event for event in events if event.get("ticket_id") == ticket_id]
    recent = events[-limit:]
    return AgentEventsResponse(events=[AgentEvent.model_validate(event) for event in recent], total=len(events))


@app.get("/approvals/pending", response_model=PendingApprovalsResponse)
async def pending_approvals() -> PendingApprovalsResponse:
    return PendingApprovalsResponse(
        approvals=[AgentEvent.model_validate(event) for event in audit.pending_approvals()]
    )


@app.get("/cash", response_model=CheckingBalanceResponse)
async def checking_balance() -> CheckingBalanceResponse:
    try:
        async with MCPGateway() as gateway:
            data = await gateway.call_api_read_tool("get_checking_balance")
        return CheckingBalanceResponse.model_validate(data)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Could not read checking through MCP.") from error


@app.post("/approvals/{approval_id}/decision", response_model=ApprovalDecisionResponse)
async def decide_payment(
    approval_id: str,
    decision: ApprovalDecision,
) -> dict[str, object]:
    """Record a human decision; only an explicit approval invokes the MCP payment tool."""
    async with operation_lock:
        return await _decide_payment_locked(approval_id, decision)


async def _decide_payment_locked(
    approval_id: str, decision: ApprovalDecision,
) -> dict[str, object]:
    pending = audit.pending_approval(approval_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="Pending approval was not found.")

    operator = decision.approved_by.strip()
    if not operator:
        raise HTTPException(status_code=422, detail="A human approver name is required.")

    await audit.append(AgentEvent(
        run_id=pending["run_id"],
        ticket_id=pending.get("ticket_id"),
        agent="Human",
        event_type="approval_decision",
        approval_id=approval_id,
        summary="Operator approved the proposed action." if decision.decision == "approve" else "Operator rejected the proposed action.",
        details={"decision": decision.decision, "approved_by": operator, "note": decision.note},
    ))
    if decision.decision == "reject":
        return {"approval_id": approval_id, "decision": "rejected", "cash_changed": False}

    request = pending.get("details", {}).get("request", {})
    if request.get("payment_kind") == "ticket_resolution":
        try:
            async with MCPGateway(approval_token=secrets.token_urlsafe(48)) as gateway:
                result = await gateway.execute_human_approved_resolution({
                    "ticket_id": request["reference_id"], "approved_by": operator,
                    "approval_id": approval_id,
                    "quote_fingerprint": pending["details"]["authoritative_quote"]["fingerprint"],
                })
        except Exception as error:
            await audit.append(AgentEvent(
                run_id=pending["run_id"], ticket_id=pending.get("ticket_id"),
                event_type="resolution_blocked", approval_id=approval_id,
                tool_name="execute_approved_ticket_resolution",
                summary=f"Internal resolution blocked ({type(error).__name__}); review current evidence again.",
            ))
            raise HTTPException(status_code=409, detail="Resolution blocked by current database safeguards.") from error
        await audit.append(AgentEvent(
            run_id=pending["run_id"], ticket_id=pending.get("ticket_id"),
            event_type="ticket_resolved", approval_id=approval_id,
            tool_name="execute_approved_ticket_resolution", summary=result["summary"],
            details={"resolution": result, "status": "resolved"},
        ))
        return {"approval_id": approval_id, "decision": "approved", "cash_changed": False, "resolution": result}
    try:
        approval_token = secrets.token_urlsafe(48)
        async with MCPGateway(approval_token=approval_token) as gateway:
            result = await gateway.execute_human_approved_payment({
                "kind": request["payment_kind"],
                "ref_id": request["reference_id"],
                "approved_by": operator,
                "approval_id": approval_id,
                "approved_amount": request["amount"],
            })
    except Exception as error:
        await audit.append(AgentEvent(
            run_id=pending["run_id"],
            ticket_id=pending.get("ticket_id"),
            agent="System",
            event_type="payment_blocked",
            approval_id=approval_id,
            tool_name="execute_approved_payment",
            summary=f"Approved payment did not execute ({type(error).__name__}); MCP safeguards blocked it.",
        ))
        raise HTTPException(status_code=409, detail="Payment was blocked by current database safeguards.") from error

    await audit.append(AgentEvent(
        run_id=pending["run_id"],
        ticket_id=pending.get("ticket_id"),
        agent="System",
        event_type="payment_executed",
        approval_id=approval_id,
        tool_name="execute_approved_payment",
        summary="MCP executed the explicitly approved outgoing payment.",
        details={"payment": result},
    ))
    for resolved_ticket_id in result.get("resolved_ticket_ids", []):
        await audit.append(AgentEvent(
            run_id=pending["run_id"],
            ticket_id=int(resolved_ticket_id),
            agent="System",
            event_type="ticket_resolved",
            tool_name="execute_approved_payment",
            approval_id=approval_id,
            summary="The linked rent notice was resolved after the approved lease payment was recorded.",
            details={"payment": result, "status": "resolved"},
        ))
    return {"approval_id": approval_id, "decision": "approved", "cash_changed": True, "payment": result}


@app.post("/database/reset", response_model=ResetResponse)
async def reset_working_database(request: ResetRequest) -> ResetResponse:
    """Explicitly restore only the working copy; the original source remains untouched."""
    if not request.confirm:
        raise HTTPException(status_code=422, detail="Set confirm=true to reset the working database.")
    try:
        async with operation_lock:
            async with MCPGateway() as gateway:
                result = await gateway.reset_working_database()
            await audit.append(AgentEvent(
                run_id=str(uuid4()),
                agent="System",
                event_type="working_database_reset",
                summary="Operator explicitly reset the working database; earlier approvals are invalidated.",
                details={"database": result.get("database"), "integrity_check": result.get("integrity_check")},
            ))
        return ResetResponse.model_validate(result)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Working database reset failed through MCP.") from error
