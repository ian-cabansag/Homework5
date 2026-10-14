"""MCP stdio client. All business data operations are delegated to mcp_server."""

import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.settings import MCP_SERVER_PATH
from backend.models import Ticket


AGENT_READ_TOOLS = {
    "get_ticket_resolution_quote",
    "get_ticket_resolution_record",
    "get_ticket_101_tee_reprint_context",
    "get_ticket_102_rent_and_cash_context",
    "get_ticket_103_hoodie_stock_and_pricing",
    "list_vendors",
    "get_vendor_shipping_eligibility",
    "get_payment_quote",
}
APPROVAL_ONLY_TOOLS = {"execute_approved_payment", "execute_approved_ticket_resolution"}
API_READ_TOOLS = {"get_dashboard_tickets", "get_checking_balance"}
ADMIN_TOOLS = {"reset_working_database"}
RESOLUTION_TOOLS = {"resolve_paid_rent_notice"}


class MCPGateway:
    def __init__(self, approval_token: str | None = None) -> None:
        self._stdio_context: Any = None
        self._session_context: Any = None
        self.session: ClientSession | None = None
        self._approval_token = approval_token
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self) -> "MCPGateway":
        child_env = os.environ.copy()
        child_env.pop("PORTKEY_API_KEY", None)
        child_env.pop("CAMPUS_CUSTOMS_APPROVAL_TOKEN", None)
        if self._approval_token:
            child_env["CAMPUS_CUSTOMS_APPROVAL_TOKEN"] = self._approval_token
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(MCP_SERVER_PATH)],
            env=child_env,
        )
        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(stdio_client(parameters))
            self.session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await self.session.initialize()
        except BaseException:
            await self._exit_stack.aclose()
            raise
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self._exit_stack.__aexit__(exc_type, exc, traceback)

    async def list_tool_names(self) -> set[str]:
        if self.session is None:
            raise RuntimeError("MCP session is not connected.")
        result = await self.session.list_tools()
        return {tool.name for tool in result.tools}

    async def call_agent_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in AGENT_READ_TOOLS:
            raise PermissionError("Agents may call only the approved read-only MCP tools.")
        return await self._call(name, self.normalize_agent_arguments(name, arguments))

    @staticmethod
    def normalize_agent_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Translate common model aliases to the fixed MCP tool schemas."""
        if name in {
            "get_ticket_101_tee_reprint_context",
            "get_ticket_102_rent_and_cash_context",
            "get_ticket_103_hoodie_stock_and_pricing",
            "list_vendors",
        }:
            return {}
        if name == "get_payment_quote":
            if "payment_kind" in arguments and "reference_id" in arguments:
                if ("kind" in arguments and arguments["kind"] != arguments["payment_kind"]) or ("ref_id" in arguments and arguments["ref_id"] != arguments["reference_id"]):
                    raise ValueError("Conflicting payment identifiers.")
                arguments = {**arguments, "kind": arguments["payment_kind"], "ref_id": arguments["reference_id"]}
            if "invoice_id" in arguments and "lease_id" in arguments:
                raise ValueError("Payment quote arguments cannot identify both an invoice and a lease.")
            if "kind" in arguments and "ref_id" in arguments:
                return {"kind": arguments["kind"], "ref_id": arguments["ref_id"]}
            if "invoice_id" in arguments:
                return {"kind": "invoice", "ref_id": arguments["invoice_id"]}
            if "lease_id" in arguments:
                return {"kind": "lease", "ref_id": arguments["lease_id"]}
        if name == "get_vendor_shipping_eligibility" and "vendor_id" in arguments:
            return {"vendor_id": arguments["vendor_id"]}
        return arguments

    async def execute_human_approved_payment(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if "execute_approved_payment" not in APPROVAL_ONLY_TOOLS:
            raise PermissionError("Payment execution is not available through this MCP gateway.")
        if not self._approval_token:
            raise PermissionError("No human approval token was provided to the MCP server.")
        return await self._call(
            "execute_approved_payment",
            {**arguments, "approval_token": self._approval_token},
        )

    async def call_api_read_tool(self, name: str) -> dict[str, Any]:
        if name not in API_READ_TOOLS:
            raise PermissionError("This MCP operation is not an API dashboard read.")
        return await self._call(name, {})

    async def execute_human_approved_resolution(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._approval_token:
            raise PermissionError("No human approval token was provided.")
        return await self._call("execute_approved_ticket_resolution", {**arguments, "approval_token": self._approval_token})

    async def reset_working_database(self) -> dict[str, Any]:
        if "reset_working_database" not in ADMIN_TOOLS:
            raise PermissionError("Database reset is not available through this MCP gateway.")
        return await self._call("reset_working_database", {})

    async def resolve_paid_rent_notice(self) -> dict[str, Any]:
        """Close the rent notice only after MCP verifies its lease payment ledger row."""
        if "resolve_paid_rent_notice" not in RESOLUTION_TOOLS:
            raise PermissionError("Paid-rent ticket resolution is not available through this gateway.")
        return await self._call("resolve_paid_rent_notice", {})

    async def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("MCP session is not connected.")
        result = await self.session.call_tool(name, arguments)
        if result.isError:
            messages = [getattr(block, "text", "MCP tool returned an error") for block in result.content]
            raise RuntimeError(f"MCP tool {name} failed: {'; '.join(messages)}")

        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            return self._validate_result(name, structured)
        for block in result.content:
            value = getattr(block, "text", None)
            if value:
                try:
                    decoded = json.loads(value)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict):
                    return self._validate_result(name, decoded)
        raise RuntimeError(f"MCP tool {name} returned no structured object.")

    @staticmethod
    def _validate_result(name: str, data: dict[str, Any]) -> dict[str, Any]:
        if name.startswith("get_ticket_") and "ticket" in data:
            data["ticket"] = Ticket.model_validate(data["ticket"]).model_dump(mode="json")
        return data
