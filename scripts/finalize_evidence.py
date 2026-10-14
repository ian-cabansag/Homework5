"""Generate final evidence only from a completed, reconciled real working run.

This diagnostic report generator reads SQLite independently for verification.
It cannot run agents, approve actions, or mutate business data.
"""
import hashlib
import html
import json
import re
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
SOURCE_HASH = '23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a'
assert hashlib.sha256((ROOT / 'data/campus_customs.db').read_bytes()).hexdigest() == SOURCE_HASH
events = [json.loads(line) for line in (OUT / 'audit_trail.json').read_text(encoding='utf-8').splitlines() if line.strip()]
boundary = max(i for i, event in enumerate(events) if event['event_type'] == 'working_database_reset')
current = events[boundary + 1:]
start_event = next(e for e in current if e['event_type'] == 'starting_balance_verified')
start = Decimal(str(start_event['details']['account']['balance']))
with closing(sqlite3.connect((ROOT / 'data/campus_customs_new.db').as_uri() + '?mode=ro', uri=True)) as db:
    db.row_factory = sqlite3.Row
    tickets = [dict(row) for row in db.execute('SELECT * FROM tickets ORDER BY id')]
    payments = [dict(row) for row in db.execute('SELECT * FROM payments ORDER BY id')]
    resolutions = {row['ticket_id']: dict(row) for row in db.execute('SELECT * FROM ticket_resolutions')}
    end = Decimal(str(db.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]))
    today = db.execute('SELECT date_today FROM desk').fetchone()[0]
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert all(t['status'] == 'resolved' for t in tickets if t['id'] in (101, 102, 103))
assert start - sum(Decimal(str(p['amount'])) for p in payments) == end
assert start == Decimal('3400') and end == Decimal('160') and len(payments) == 2
assert all(p['approved_by'] == 'Ian' for p in payments)
assert len([e for e in current if e['event_type'] == 'payment_executed']) == 2
assert len([e for e in current if e['event_type'] == 'ticket_resolved']) == 3

def esc(value):
    return html.escape(str(value))

records = []
for ticket_id in (101, 102, 103):
    trace = [e for e in current if e.get('ticket_id') == ticket_id]
    contributions = [{'agent': e['agent'], 'summary': e['summary'], 'run_id': e['run_id']}
                     for e in trace if e['event_type'] == 'agent_completed']
    delegations = [{'from': e['agent'], 'to': e['delegated_to'], 'reason': e['summary'], 'run_id': e['run_id']}
                   for e in trace if e['event_type'] == 'delegation_started']
    approvals = [{'approval_id': e['approval_id'], **e['details']} for e in trace if e['event_type'] == 'approval_decision']
    terminal = next(e for e in reversed(trace) if e['event_type'] == 'ticket_resolved')
    payment_rows = [p for p in payments if (ticket_id == 101 and p['kind'] == 'invoice' and p['ref_id'] == 501)
                    or (ticket_id == 102 and p['kind'] == 'lease' and p['ref_id'] == 1)]
    records.append({'ticket_id': ticket_id, 'final_status': 'resolved', 'outcome': terminal['summary'],
                    'agent_contributions': contributions, 'delegations': delegations,
                    'mcp_tools_used': sorted({e['tool_name'] for e in trace if e.get('tool_name')}),
                    'human_approvals': approvals, 'payments': payment_rows,
                    'cash_change': -sum(p['amount'] for p in payment_rows),
                    'resolution': resolutions.get(ticket_id),
                    'run_ids': list(dict.fromkeys(e['run_id'] for e in trace if e['event_type'] == 'ticket_run_started')),
                    'audit_event_ids': [e['event_id'] for e in trace], 'external_contact_made': False})
result = {'status': 'resolved', 'captured_at': datetime.now(timezone.utc).isoformat(),
          'resolution_scope': '101 internal backorder plan; 102 paid rent; 103 internally declined bulk request. Not physical fulfillment.',
          'reset_event_id': events[boundary]['event_id'], 'starting_balance_event_id': start_event['event_id'],
          'desk_date_today': today, 'tickets': records,
          'cash_reconciliation': {'starting_checking_balance': float(start), 'payments': payments,
                                  'ending_checking_balance': float(end), 'incoming_revenue': 0}}
(OUT / 'resolved_tickets.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

path = OUT / 'desk_tickets.html'
page = path.read_text(encoding='utf-8')
expected_pattern = r'<div class="section-title"><h3>Expected</h3>.*?(?=<div class="section-title actual-title">)'
expected = re.findall(expected_pattern, page, re.S)
assert len(expected) == 3
for record in records:
    ticket_id = record['ticket_id']
    participants = ', '.join(dict.fromkeys(c['agent'] for c in record['agent_contributions']))
    routes = '; '.join(f"{d['from']} → {d['to']}: {d['reason']}" for d in record['delegations'])
    tools = ', '.join(record['mcp_tools_used'])
    cash = f"${abs(record['cash_change']):,.2f} outgoing" if record['cash_change'] else '$0.00; no cash change'
    body = f'<div class="actual-slot"><div><strong>Resolved · {esc(record["outcome"])}</strong><p>Agents: {esc(participants)}.</p><p>Actual delegations: {esc(routes)}.</p><p>MCP tools: <code>{esc(tools)}</code>.</p><p>Cash effect: {cash}. {len(record["human_approvals"])} explicit human approval(s), recorded under Ian through the API decision route.</p>'
    for contribution in record['agent_contributions']:
        body += f'<details><summary>{esc(contribution["agent"])} contribution</summary><p>{esc(contribution["summary"])}</p></details>'
    if record['resolution']:
        body += f'<p>Approved internal draft, not sent: {esc(record["resolution"]["draft"])}</p><p>No shipment, accepted order, inventory change, or customer acceptance is claimed.</p>'
    body += '</div><span class="reserved">Verified in DB</span></div>'
    body += f'<div class="source-note"><span>Clean run · real agents, MCP and explicit human approvals</span><code>ticket {ticket_id} / status: resolved</code></div>\n      </section>'
    pattern = rf'(<section class="tab-panel" id="panel-{ticket_id}".*?<div class="section-title actual-title">.*?</div>)\s*.*?</section>(?=\s*<section class="tab-panel")'
    page, count = re.subn(pattern, lambda m: m[1] + '\n' + body, page, count=1, flags=re.S)
    assert count == 1
    head_pattern = rf'(<section class="tab-panel" id="panel-{ticket_id}".*?)(?=<div class="section-title"><h3>Expected)'
    page = re.sub(head_pattern, lambda m: m[1].replace('Open ticket', 'Resolved ticket').replace('>Open<', '>Resolved<'), page, count=1, flags=re.S)

cash_html = '<div class="reflection-page"><h2>Exact checking reconciliation</h2><div class="reflection-two"><article class="reflection-box"><h4>Reset baseline</h4><p>$3,400.00, verified through MCP after the clean reset; shop date 2026-08-31.</p>'
for record in records:
    cash_html += f'<p>Ticket {record["ticket_id"]}: <strong>−${abs(record["cash_change"]):,.2f}</strong>.'
    cash_html += ' '.join(f' Payment {p["id"]}: {esc(p["kind"])} {p["ref_id"]}, ${p["amount"]:,.2f}, approved by {esc(p["approved_by"])} on {esc(p["paid_at"])}.' for p in record['payments'])
    cash_html += ' Internal closure has no additional cash effect.</p>'
cash_html += '</article><article class="reflection-box"><h4>Verified ending balance</h4><p><strong>$3,400.00 − $840.00 − $2,400.00 − $0.00 = $160.00</strong></p><p>Exactly matches cash_accounts.checking and the two payments rows. No incoming revenue. Invoice payment left $2,560; rent left $160. Historical payments before the reset are preserved in the audit, not counted again.</p></article></div></div>'
page = re.sub(r'(<section class="tab-panel" id="panel-cash"[^>]*>).*?</section>(?=\s*<section class="tab-panel")', lambda m:m[1]+cash_html+'</section>', page, count=1, flags=re.S)

reflection = '<div class="reflection-page"><header class="reflection-intro"><p class="eyebrow">Problem 10 / Clean run review</p><h2>What the final run actually showed me.</h2><p>The useful result was not three automatic sales. It was three reviewed dispositions: a backorder plan, paid rent, and a declined bulk request. I had to make the distinction between closing an internal case and fulfilling an order explicit. Ian approved those decisions; the agents did not authorize themselves.</p></header>'
assessments = {
101: 'My Expected plan kept the tee request pending while payment and fulfillment were unresolved. The clean run first respected the unpaid-invoice block, obtained the $840 approval, then reviewed fresh evidence after payment. The later human-approved internal backorder plan is a change from that original stopping point, not proof that the tee arrived. Inventory helped separate zero stock from a vendor being eligible to ship; Accounting helped with the actual obligation. The extra post-payment review was justified, but repeating unchanged stock facts was less valuable.',
102: 'The lease notice should have been the cleanest fit for the plan: verify lease 1 and its September 2 due date, check cash, then wait for the $2,400 approval. Instead, the first attempt duplicated Accounting work through Facilities, then Boss passed payment_kind/reference_id to a tool expecting kind/ref_id. That read failed before payment. The adapter was corrected and routing instructions tightened before retrying; the failure remains in the audit. The eventual payment left $160 after the invoice. Facilities and Accounting have distinct responsibilities, but a capable single agent could perform both checks here. The payment transaction, not an agent saying “done,” resolved the notice.',
103: 'The decisive facts were 8 medium hoodies against 20 requested, $22 cost, and $58 list price. My Expected plan asked for an availability draft and no invented supplier. The final workflow added an explicit operator decision to decline the requested quantity/discount. No discount, stock reservation or sale was recorded. Inventory verification and careful customer wording were useful, but the approved final draft was bound to a database quote, so another agent did not need to invent a pricing strategy.',
}
for record in records:
    tid = record['ticket_id']
    trace = [e for e in current if e.get('ticket_id') == tid]
    counts = Counter(e['tool_name'] for e in trace if e['event_type'] == 'mcp_call_started')
    repeats = ', '.join(f'{name} ×{n}' for name,n in counts.items() if n>1) or 'none'
    routes = '; '.join(f"{d['from']} → {d['to']}" for d in record['delegations']) or 'no specialist handoff'
    stopped = sum(e['event_type'] in ('delegation_stopped','agent_failed','mcp_call_failed') for e in trace)
    caveat = '<p>One actual Inventory sentence went too far: it said the vendor “can ship this SKU/size/quantity.” The eligibility tool only established that unpaid invoices no longer blocked vendor 1; it did not verify product availability. The adapter discarded unsupported SKU/quantity arguments. Boss and the final approved quote correctly limited the conclusion to an internal plan, but this is a factual overreach I would tighten in the specialist prompt.</p>' if tid == 101 else ''
    reflection += f'<article class="reflection-card"><header class="reflection-card-head"><span class="reflection-id">{tid}</span><h4>Ticket {tid}</h4><span class="pill sage">Resolved</span></header><div class="reflection-card-body"><p>{assessments[tid]}</p><p>The actual route was {esc(routes)} across {len(record["run_ids"])} review(s). This is the audit route, not my planned route. Repeated evidence calls were {esc(repeats)}. Rechecking after payment is useful; rereading the same record inside one review adds coordination cost. The trace contains {stopped} stopped delegation/tool/agent events, retained rather than hidden.</p>{caveat}<p>Final recorded result: {esc(record["outcome"])} Cash effect: −${abs(record["cash_change"]):,.2f}.</p></div></article>'
reflection += '''<div class="reflection-two"><article class="reflection-box"><h4>Where one agent would be simpler</h4><p>I would use one capable agent with tools for the rent notice: lease 1, the payment quote, and a human decision cover the work. The hoodie shortage also needs arithmetic and an unsent response, not five opinions. Even 101's invoice check can be done from the focused context tool. Specialists are useful for separating inventory constraints from payment authority, but the actual protection comes from MCP transactions and explicit approvals, not from the number of agents.</p><p>My original Expected sections remain unchanged above. The final internal-disposition tools were added afterward. That matters: I should not rewrite the plan to pretend it predicted the final workflow. Earlier partial runs and their failures remain in the audit and prior_run archive; the Cash tab counts only this reset generation.</p></article><article class="reflection-box"><h4>Three other supported desk questions</h4><ol><li>Is Bulldog Print Co currently eligible to ship after invoice 501? get_vendor_shipping_eligibility reads the vendor's unpaid invoices; it can explain eligibility without claiming shipment.</li><li>Would paying lease 1 again duplicate this month's recorded rent? get_payment_quote and the rent context read payments and refuse a duplicate rather than reducing the remaining $160.</li><li>What size-L hoodie availability can we mention as an alternative, without substituting it for the club's medium order? The hoodie stock/pricing tool returns all sizes, including 14 L, at the recorded $58 list price. Customer Service can draft the option without accepting an order.</li></ol><p>These are evidence inquiries within the existing desk. The API intentionally accepts only tickets 101–103; intake of arbitrary new ticket IDs would need an API/tool extension.</p></article></div><article class="reflection-box"><h4>Three tasks this team cannot currently complete</h4><ol><li><strong>Order and receive twelve additional medium hoodies.</strong> We need SKU-to-vendor sourcing, vendor quotes, minimum order quantities, purchase-order and receipt tables, and approval-bound purchase/receive tools. The existing vendor specialty and lead time do not establish hoodie availability. Inventory needs a procurement workflow; the $160 balance still constrains spending.</li><li><strong>Authorize a new bulk-discount policy and reserve stock.</strong> We need an approved discount-policy table, policy/version approval tools, order and reservation data, and transactional stock allocation. Accounting would check policy and margin; Customer Service would explain the approved offer. The current internal decline tool does none of these.</li><li><strong>Track the tee shipment and confirm customer pickup.</strong> We need shipment, receipt and pickup records plus evidence-backed status tools, with Inventory verifying receipt and Customer Service recording pickup authorization. Paying invoice 501 and reading a five-day lead time cannot establish either event. Real vendor/customer communication remains prohibited in this assignment; any extension must keep communications as internal drafts.</li></ol></article></div>'''
page = re.sub(r'(<section class="tab-panel" id="panel-reflection"[^>]*>).*?(?=\n\s*</section>\s*\n\s*</section>\s*\n\s*<footer)', lambda m:m[1]+reflection, page, count=1, flags=re.S)
assert re.findall(expected_pattern, page, re.S) == expected, 'Expected plans changed'
assert 'What the final run actually showed me.' in page
path.write_text(page, encoding='utf-8')
board_path = OUT / 'resolved_board.html'
board = board_path.read_text(encoding='utf-8').split('<body>')[0]
board += '<body><main class="wrap"><div class="eyebrow">Campus Customs · final run evidence</div><h1>Three reviewed dispositions.</h1><p class="lede">Real React dashboard captures of the resolved working-database state. Internal case closure is not physical fulfillment.</p><aside class="banner"><strong>3 of 3 tickets resolved in the database</strong>Ian approved both payments and both internal dispositions. No vendor/customer contact, shipment, sale, discount authorization or incoming revenue is claimed.</aside><section class="grid">'
for record in records:
    board += f'<article class="card"><div class="card-head"><span class="id">TICKET {record["ticket_id"]}</span><span class="pill resolved">Resolved</span></div><h2>Ticket {record["ticket_id"]}</h2><p>{esc(record["outcome"])}</p></article>'
board += '</section><section class="cash"><div><small>CHECKING · AFTER APPROVED PAYMENTS</small><strong>$160.00</strong></div><div>$3,400.00 − $840.00 − $2,400.00 = $160.00</div></section><section class="screenshots">'
for record in records:
    tid = record['ticket_id']
    board += f'<figure><a href="dashboard_screenshots/ticket-{tid}.png"><img src="dashboard_screenshots/ticket-{tid}.png" alt="Real React dashboard, ticket {tid} resolved, checking $160"></a><figcaption>Ticket {tid} · {esc(record["outcome"])} Click for full-size evidence.</figcaption></figure>'
board += '</section><p class="foot">Captured from the real React app using a validation backend connected to the same working DB and audit. Screenshot capture does not run agents or approve actions. <a href="dashboard_browser_check.json">Browser verification</a> · <a href="resolved_tickets.json">Structured results</a> · <a href="audit_trail.json">Audit</a> · <a href="desk_tickets.html">Expected, Actual, Cash and Reflection</a></p></main></body></html>'
board_path.write_text(board, encoding='utf-8')
print('PASS: final JSON, Actual/Cash/Reflection generated from reconciled DB and current audit; Expected sections preserved.')
