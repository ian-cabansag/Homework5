"""Campus Customs MCP data tools, backed only by the working database."""

import sqlite3
import hmac
import os
import tempfile
from contextlib import closing
from pathlib import Path
import shutil
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

mcp = FastMCP("Campus Customs Evidence")


@mcp.tool()
def get_dashboard_tickets() -> dict[str, Any]:
    """Return dashboard tickets 101–103 with their current open/resolved status."""
    with closing(_connect_readonly()) as connection:
        tickets = _many(
            connection,
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
            "status, notes, created_at FROM tickets WHERE id IN (101, 102, 103) ORDER BY id",
            (),
        )
    return {"tickets": tickets}


@mcp.tool()
def get_checking_balance() -> dict[str, Any]:
    """Return the current checking balance and its recorded date."""
    with closing(_connect_readonly()) as connection:
        account = _one(
            connection,
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
            ("checking",),
        )
    return {"account": account}


@mcp.tool()
def reset_working_database() -> dict[str, Any]:
    """Reset the working database from the immutable original source database."""
    original = PROJECT_ROOT / "data" / "campus_customs.db"
    working = DATABASE_PATH
    if not original.is_file() or original.resolve() == working.resolve():
        raise FileNotFoundError("Original source database is unavailable or unsafe to copy.")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="campus_customs_reset_", suffix=".db", dir=working.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        shutil.copy2(original, temporary_path)
        with closing(sqlite3.connect(temporary_path)) as verification:
            integrity = verification.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError("Original database copy failed integrity verification.")
        os.replace(temporary_path, working)
        return {"reset": True, "database": "data/campus_customs_new.db", "integrity_check": integrity}
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _connect_readonly() -> sqlite3.Connection:
    """Open only the working database, in read-only mode."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Working database not found: {DATABASE_PATH}")

    connection = sqlite3.connect(f"{DATABASE_PATH.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _connect_write() -> sqlite3.Connection:
    """Open only the working database for an explicitly approved payment."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Working database not found: {DATABASE_PATH}")
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _one(connection: sqlite3.Connection, query: str, parameters: tuple[Any, ...]) -> dict[str, Any]:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise LookupError("Required Campus Customs record was not found in the working database.")
    return dict(row)


def _many(connection: sqlite3.Connection, query: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


@mcp.tool()
def get_ticket_101_tee_reprint_context() -> dict[str, Any]:
    """Read ticket 101's tee stock, pricing, linked reprint invoice/vendor, and cash context."""
    with closing(_connect_readonly()) as connection:
        ticket = _one(connection, "SELECT * FROM tickets WHERE id = ?", (101,))
        sku, size = ticket["sku"], ticket["size"]
        inventory = _one(
            connection,
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        )
        pricing = _one(
            connection,
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        )
        invoice = _one(connection, "SELECT * FROM invoices WHERE id = ?", (ticket["invoice_id"],))
        vendor = _one(
            connection,
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (invoice["vendor_id"],),
        )
        cash = _one(connection, "SELECT name, balance, date FROM cash_accounts WHERE name = ?", ("checking",))
        desk = _one(connection, "SELECT date_today FROM desk LIMIT 1", ())
        payment_ledger = _many(
            connection,
            "SELECT id, kind, ref_id, amount, account, paid_at, approved_by "
            "FROM payments ORDER BY id",
            (),
        )

    return {
        "ticket": ticket,
        "inventory": inventory,
        "pricing": pricing,
        "invoice": invoice,
        "vendor": vendor,
        "checking": cash,
        "desk_date_today": desk["date_today"],
        "payment_ledger": payment_ledger,
    }


@mcp.tool()
def get_ticket_102_rent_and_cash_context() -> dict[str, Any]:
    """Read ticket 102's lease, rent due date, shop date, checking balance, and related payments."""
    with closing(_connect_readonly()) as connection:
        ticket = _one(connection, "SELECT * FROM tickets WHERE id = ?", (102,))
        lease = _one(connection, "SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],))
        cash = _one(connection, "SELECT name, balance, date FROM cash_accounts WHERE name = ?", ("checking",))
        desk = _one(connection, "SELECT date_today FROM desk LIMIT 1", ())
        payment_ledger = _many(
            connection,
            "SELECT id, kind, ref_id, amount, account, paid_at, approved_by "
            "FROM payments ORDER BY id",
            (),
        )

    return {
        "ticket": ticket,
        "lease": lease,
        "checking": cash,
        "desk_date_today": desk["date_today"],
        "payment_ledger": payment_ledger,
    }


@mcp.tool()
def get_ticket_103_hoodie_stock_and_pricing() -> dict[str, Any]:
    """Read ticket 103's requested hoodie size, all size-level hoodie stock, and database pricing."""
    with closing(_connect_readonly()) as connection:
        ticket = _one(connection, "SELECT * FROM tickets WHERE id = ?", (103,))
        sku = ticket["sku"]
        inventory = _many(
            connection,
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY size",
            (sku,),
        )
        pricing = _one(
            connection,
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        )

    return {"ticket": ticket, "inventory_by_size": inventory, "pricing": pricing}


@mcp.tool()
def list_vendors() -> dict[str, Any]:
    """Read vendor specialties and database lead times; do not infer unsupported product matches."""
    with closing(_connect_readonly()) as connection:
        vendors = _many(
            connection,
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id",
            (),
        )
    return {"vendors": vendors}


@mcp.tool()
def get_vendor_shipping_eligibility(
    vendor_id: Annotated[int, Field(gt=0)],
) -> dict[str, Any]:
    """Read a vendor and its open invoices to determine whether new product may ship."""
    with closing(_connect_readonly()) as connection:
        vendor = _one(
            connection,
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        )
        open_invoices = _many(
            connection,
            "SELECT id, amount, due_date, status, description FROM invoices "
            "WHERE vendor_id = ? AND lower(status) = 'open' ORDER BY id",
            (vendor_id,),
        )
    return {
        "vendor": vendor,
        "open_invoices": open_invoices,
        "can_ship_new_product": len(open_invoices) == 0,
        "basis": "A vendor with an open invoice is blocked from shipping new product.",
    }


def _payment_quote(
    connection: sqlite3.Connection,
    kind: Literal["invoice", "lease"],
    ref_id: int,
) -> dict[str, Any]:
    checking = _one(
        connection,
        "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
        ("checking",),
    )
    desk = _one(connection, "SELECT date_today FROM desk LIMIT 1", ())

    if kind == "invoice":
        record = _one(connection, "SELECT id, vendor_id, amount, status FROM invoices WHERE id = ?", (ref_id,))
        amount = float(record["amount"])
        already_paid = (
            str(record["status"]).lower() != "open"
            or connection.execute(
                "SELECT 1 FROM payments WHERE kind = ? AND ref_id = ? LIMIT 1",
                ("invoice", ref_id),
            ).fetchone() is not None
        )
        description = f"Invoice {ref_id}"
    else:
        record = _one(
            connection,
            "SELECT id, monthly_rent, next_due, landlord FROM leases WHERE id = ?",
            (ref_id,),
        )
        amount = float(record["monthly_rent"])
        already_paid = connection.execute(
            "SELECT 1 FROM payments WHERE kind = ? AND ref_id = ? LIMIT 1",
            ("lease", ref_id),
        ).fetchone() is not None
        description = f"Lease {ref_id} rent"

    balance = float(checking["balance"])
    can_pay = not already_paid and amount > 0 and amount <= balance
    if already_paid:
        reason = "The invoice is not open or this lease already has a payment record."
    elif amount <= 0:
        reason = "Payment amount must be positive outgoing cash."
    elif amount > balance:
        reason = "Payment would make checking cash negative."
    else:
        reason = None
    return {
        "kind": kind,
        "ref_id": ref_id,
        "description": description,
        "amount": round(amount, 2),
        "checking_balance": round(balance, 2),
        "balance_after_payment": round(balance - amount, 2),
        "desk_date_today": desk["date_today"],
        "can_pay_if_human_approved": can_pay,
        "blocked_reason": reason,
    }


@mcp.tool()
def get_payment_quote(
    kind: Literal["invoice", "lease"],
    ref_id: Annotated[int, Field(gt=0)],
) -> dict[str, Any]:
    """Read the authoritative amount, current cash, and duplicate/open status for a proposed outgoing payment."""
    with closing(_connect_readonly()) as connection:
        return _payment_quote(connection, kind, ref_id)


@mcp.tool()
def execute_approved_payment(
    kind: Literal["invoice", "lease"],
    ref_id: Annotated[int, Field(gt=0)],
    approved_by: Annotated[str, Field(min_length=1, max_length=120)],
    approval_id: Annotated[str, Field(min_length=1, max_length=100)],
    approval_token: Annotated[str, Field(min_length=32, max_length=200)],
) -> dict[str, Any]:
    """Execute an explicitly approved outgoing payment; a linked paid rent notice is resolved atomically."""
    approved_by = approved_by.strip()
    if not approved_by:
        raise ValueError("A human approver name is required.")
    expected_token = os.environ.pop("CAMPUS_CUSTOMS_APPROVAL_TOKEN", "")
    if not expected_token or not hmac.compare_digest(approval_token, expected_token):
        raise PermissionError("Payment execution requires an explicit backend human approval.")

    with closing(_connect_write()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        quote = _payment_quote(connection, kind, ref_id)
        if not quote["can_pay_if_human_approved"]:
            raise ValueError(quote["blocked_reason"] or "Payment is not eligible.")

        amount = float(quote["amount"])
        date_today = str(quote["desk_date_today"])
        balance = float(quote["checking_balance"])
        connection.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (round(balance - amount, 2), date_today, "checking"),
        )
        cursor = connection.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, "checking", date_today, approved_by),
        )
        if kind == "invoice":
            connection.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))

        resolved_ticket_ids: list[int] = []
        if kind == "lease":
            rent_tickets = _many(
                connection,
                "SELECT id FROM tickets WHERE lease_id = ? AND lower(type) = 'rent_notice' "
                "AND lower(status) = 'open' ORDER BY id",
                (ref_id,),
            )
            for rent_ticket in rent_tickets:
                ticket_id = int(rent_ticket["id"])
                connection.execute(
                    "UPDATE tickets SET status = 'resolved' WHERE id = ? AND lower(status) = 'open'",
                    (ticket_id,),
                )
                resolved_ticket_ids.append(ticket_id)
        connection.commit()

    return {
        "approval_id": approval_id,
        "payment_id": cursor.lastrowid,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": "checking",
        "paid_at": date_today,
        "approved_by": approved_by,
        "balance_after_payment": round(balance - amount, 2),
        "cash_direction": "outgoing_only",
        "resolved_ticket_ids": resolved_ticket_ids,
    }


@mcp.tool()
def resolve_paid_rent_notice() -> dict[str, Any]:
    """Resolve ticket 102 only after its linked lease rent payment is recorded in the ledger."""
    with closing(_connect_write()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        ticket = _one(
            connection,
            "SELECT id, type, lease_id, status FROM tickets WHERE id = ?",
            (102,),
        )
        if str(ticket["type"]).lower() != "rent_notice" or ticket["lease_id"] is None:
            raise ValueError("Ticket 102 is not a linked rent notice.")
        lease = _one(
            connection,
            "SELECT monthly_rent FROM leases WHERE id = ?",
            (ticket["lease_id"],),
        )

        payment = connection.execute(
            "SELECT id, amount, paid_at, approved_by FROM payments "
            "WHERE kind = 'lease' AND ref_id = ? ORDER BY id DESC LIMIT 1",
            (ticket["lease_id"],),
        ).fetchone()
        if payment is None:
            raise ValueError("The linked lease has no recorded payment; the rent notice cannot be resolved.")
        if (
            float(payment["amount"]) != float(lease["monthly_rent"])
            or not str(payment["approved_by"] or "").strip()
        ):
            raise ValueError("The linked payment does not verify a fully paid, human-approved rent obligation.")

        if str(ticket["status"]).lower() == "open":
            connection.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (102,))
        elif str(ticket["status"]).lower() != "resolved":
            raise ValueError("Ticket 102 has an unsupported status and cannot be resolved.")
        connection.commit()

    return {
        "ticket_id": 102,
        "status": "resolved",
        "payment_id": int(payment["id"]),
        "payment_amount": float(payment["amount"]),
        "paid_at": payment["paid_at"],
        "approved_by": payment["approved_by"],
        "external_contact_made": False,
    }


if __name__ == "__main__":
    mcp.run()
