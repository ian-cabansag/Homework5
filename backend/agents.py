"""Five PydanticAI roles, all routed through the single Portkey model."""

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from backend.audit import AuditTrail
from backend.mcp_client import MCPGateway
from backend.models import AgentEvent, AgentReply, AgentRole, DelegationRequest, ToolResult
from backend.settings import MODEL_NAME, PORTKEY_BASE_URL, PROMPTS_DIR, require_portkey_key


MCPToolName = Literal[
    "get_ticket_101_tee_reprint_context",
    "get_ticket_102_rent_and_cash_context",
    "get_ticket_103_hoodie_stock_and_pricing",
    "list_vendors",
    "get_vendor_shipping_eligibility",
    "get_payment_quote",
]

ROLE_FILES = {
    AgentRole.BOSS: "boss.md",
    AgentRole.INVENTORY: "inventory.md",
    AgentRole.ACCOUNTING: "accounting.md",
    AgentRole.FACILITIES: "facilities.md",
    AgentRole.CUSTOMER_SERVICE: "customer_service.md",
}

ROLE_TOOLS = {
    AgentRole.BOSS: frozenset(MCPToolName.__args__),
    AgentRole.INVENTORY: frozenset({
        "get_ticket_101_tee_reprint_context",
        "get_ticket_103_hoodie_stock_and_pricing",
        "list_vendors",
        "get_vendor_shipping_eligibility",
    }),
    AgentRole.ACCOUNTING: frozenset({
        "get_ticket_101_tee_reprint_context",
        "get_ticket_102_rent_and_cash_context",
        "get_vendor_shipping_eligibility",
        "get_payment_quote",
    }),
    AgentRole.FACILITIES: frozenset({
        "get_ticket_102_rent_and_cash_context",
        "get_payment_quote",
    }),
    AgentRole.CUSTOMER_SERVICE: frozenset({
        "get_ticket_101_tee_reprint_context",
        "get_ticket_103_hoodie_stock_and_pricing",
        "list_vendors",
    }),
}

DelegateHandler = Callable[[DelegationRequest], Awaitable[dict[str, Any]]]


@dataclass
class AgentBudget:
    agent_runs: int = 0
    mcp_calls: int = 0
    delegations: int = 0
    role_mcp_calls: dict[AgentRole, int] = field(default_factory=dict)


@dataclass
class AgentDeps:
    role: AgentRole
    ticket_id: int
    run_id: str
    mcp: MCPGateway
    audit: AuditTrail
    budget: AgentBudget
    visited: tuple[AgentRole, ...]
    delegation_depth: int
    delegate: DelegateHandler


MAX_AGENT_RUNS = 5
MAX_MCP_CALLS = 12
MAX_DELEGATIONS = 3
MAX_DELEGATION_DEPTH = 2


def _model() -> OpenAIChatModel:
    key = require_portkey_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIChatModel(MODEL_NAME, provider=provider)


def build_agents() -> dict[AgentRole, Agent[AgentDeps, AgentReply]]:
    shared_model = _model()
    agents: dict[AgentRole, Agent[AgentDeps, AgentReply]] = {}

    for role, filename in ROLE_FILES.items():
        system_prompt = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
        agent = Agent(
            shared_model,
            deps_type=AgentDeps,
            output_type=AgentReply,
            name=f"campus-customs-{role.value.lower().replace(' ', '-')}",
            system_prompt=system_prompt,
            retries=1,
        )

        @agent.tool
        async def query_campus_customs(
            ctx: RunContext[AgentDeps],
            tool_name: MCPToolName,
            arguments: dict[str, Any],
        ) -> ToolResult:
            """Fetch factual records by calling a named read-only Campus Customs MCP tool."""
            current = ctx.deps
            if tool_name not in ROLE_TOOLS[current.role]:
                raise PermissionError(f"{current.role.value} is not allowed to use {tool_name}.")
            if current.budget.mcp_calls >= MAX_MCP_CALLS:
                raise RuntimeError("This ticket run reached its MCP call limit.")
            current.budget.mcp_calls += 1
            current.budget.role_mcp_calls[current.role] = (
                current.budget.role_mcp_calls.get(current.role, 0) + 1
            )
            await current.audit.append(AgentEvent(
                run_id=current.run_id,
                ticket_id=current.ticket_id,
                agent=current.role,
                event_type="mcp_call_started",
                tool_name=tool_name,
                summary=f"{current.role.value} requested factual evidence from {tool_name}.",
                details={
                    "arguments": MCPGateway.normalize_agent_arguments(tool_name, arguments),
                    **({"provided_arguments": arguments} if arguments != MCPGateway.normalize_agent_arguments(tool_name, arguments) else {}),
                },
            ))
            try:
                data = await current.mcp.call_agent_tool(tool_name, arguments)
            except Exception as error:
                await current.audit.append(AgentEvent(
                    run_id=current.run_id,
                    ticket_id=current.ticket_id,
                    agent=current.role,
                    event_type="mcp_call_failed",
                    tool_name=tool_name,
                    summary=f"{tool_name} failed: {type(error).__name__}.",
                ))
                raise
            concise = json.dumps(data, ensure_ascii=False, separators=(",", ":"))[:700]
            await current.audit.append(AgentEvent(
                run_id=current.run_id,
                ticket_id=current.ticket_id,
                agent=current.role,
                event_type="mcp_call_completed",
                tool_name=tool_name,
                summary=f"{tool_name} returned database evidence.",
                details={"result_summary": concise},
            ))
            return ToolResult(tool_name=tool_name, data=data)

        @agent.tool
        async def delegate_to_specialist(
            ctx: RunContext[AgentDeps],
            target: AgentRole,
            reason: str,
            task: str,
        ) -> dict[str, Any]:
            """Ask another role for a bounded specialist finding when its expertise is needed."""
            request = DelegationRequest(target=target, reason=reason, task=task)
            return await ctx.deps.delegate(request)

        agents[role] = agent

    return agents
