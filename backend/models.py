"""Validated API, agent, MCP, delegation, approval, and audit data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentRole(StrEnum):
    BOSS = "Boss"
    INVENTORY = "Inventory"
    ACCOUNTING = "Accounting"
    FACILITIES = "Facilities"
    CUSTOMER_SERVICE = "Customer Service"


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = Field(default=None, ge=0)
    lease_id: int | None = Field(default=None, gt=0)
    invoice_id: int | None = Field(default=None, gt=0)
    status: str
    notes: str | None = None
    created_at: datetime | str


class DelegationRequest(BaseModel):
    target: AgentRole
    task: str = Field(min_length=8, max_length=1200)
    reason: str = Field(min_length=8, max_length=500)


class ToolResult(BaseModel):
    tool_name: str
    data: dict[str, Any]


class ApprovalRequest(BaseModel):
    payment_kind: Literal["invoice", "lease"]
    reference_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    rationale: str = Field(min_length=8, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class ApprovalDecision(BaseModel):
    approved_by: str = Field(min_length=1, max_length=120)
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class AgentReply(BaseModel):
    status: Literal["ready", "needs_approval", "blocked", "draft_only"]
    summary: str = Field(min_length=1, max_length=1800)
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)
    recommendations: list[str] = Field(default_factory=list, max_length=8)
    drafts: list[str] = Field(default_factory=list, max_length=5)
    approval_requests: list[ApprovalRequest] = Field(default_factory=list, max_length=3)


class TicketOutcome(BaseModel):
    run_id: str
    ticket_id: int
    status: Literal["ready", "needs_approval", "blocked", "draft_only"]
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    drafts: list[str] = Field(default_factory=list)
    pending_approval_ids: list[str] = Field(default_factory=list)
    specialist_reports: list[dict[str, Any]] = Field(default_factory=list)
    agent_invocations: int = Field(default=0, ge=0)
    mcp_calls: int = Field(default=0, ge=0)
    delegation_count: int = Field(default=0, ge=0)
    stop_reason: str


class TicketRunRequest(BaseModel):
    instruction: str | None = Field(default=None, max_length=1600)


class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str
    ticket_id: int | None = None
    agent: AgentRole | Literal["System", "Human"] = "System"
    event_type: str
    summary: str = Field(max_length=1200)
    tool_name: str | None = None
    delegated_to: AgentRole | None = None
    approval_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MCPToolRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentRunState(BaseModel):
    run_id: str
    ticket_id: int = Field(gt=0)
    active_role: AgentRole
    agent_runs: int = Field(default=0, ge=0)
    mcp_calls: int = Field(default=0, ge=0)
    delegations: int = Field(default=0, ge=0)
    delegation_path: list[AgentRole] = Field(default_factory=list)
    stop_reason: str | None = None
