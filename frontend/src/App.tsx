import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, BadgeCheck, Banknote, Bell, Check, CheckCircle2,
  ChevronRight, CircleDot, Command, FileClock, LoaderCircle, Pause, Play,
  RefreshCw, ShieldCheck, Sparkles, TriangleAlert, X,
} from 'lucide-react'
import { decideApproval, getCash, getEvents, getPendingApprovals, getTickets, runTicket } from './api'
import type { AgentEvent, AgentName, Approval, CashAccount, Ticket, TicketOutcome } from './types'

const ROLE_CLASS: Record<AgentName, string> = {
  Boss: 'boss', Inventory: 'inventory', Accounting: 'accounting', Facilities: 'facilities',
  'Customer Service': 'customer', Human: 'human', System: 'system',
}

const ROLE_MARK: Record<AgentName, string> = {
  Boss: 'B', Inventory: 'I', Accounting: 'A', Facilities: 'F',
  'Customer Service': 'C', Human: 'H', System: '·',
}

const statusText = (status: string) => status.toLowerCase() === 'resolved' ? 'Resolved' : 'Open'
const dollars = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value)
const timeLabel = (value: string) => new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(value))

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<CashAccount | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [selectedId, setSelectedId] = useState(101)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [runningTicket, setRunningTicket] = useState<number | null>(null)
  const [outcome, setOutcome] = useState<TicketOutcome | null>(null)
  const [busyApproval, setBusyApproval] = useState<string | null>(null)
  const [approver, setApprover] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const selected = tickets.find(ticket => ticket.id === selectedId) ?? null
  const selectedEvents = useMemo(() => events.filter(event => event.ticket_id === selectedId), [events, selectedId])
  const savedOutcome = [...selectedEvents].reverse().find(event =>
    event.event_type === 'ticket_run_stopped' && event.details.outcome)?.details.outcome as TicketOutcome | undefined
  const visibleOutcome = outcome?.ticket_id === selectedId ? outcome : savedOutcome
  const lastBossReport = [...selectedEvents].reverse().find(event =>
    event.agent === 'Boss' && event.event_type === 'agent_completed')
  const finalResolution = [...selectedEvents].reverse().find(event => event.event_type === 'ticket_resolved')
  const runIsActive = runningTicket === selectedId

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setRefreshing(true)
    try {
      const [nextTickets, nextCash, nextEvents, nextApprovals] = await Promise.all([
        getTickets(), getCash(), getEvents(), getPendingApprovals(),
      ])
      setTickets(nextTickets)
      setCash(nextCash)
      setEvents(nextEvents)
      setApprovals(nextApprovals)
      setLastUpdated(new Date())
      setError('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not connect to the operations API.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  const refreshActivity = useCallback(async () => {
    try {
      const [nextEvents, nextApprovals] = await Promise.all([getEvents(), getPendingApprovals()])
      setEvents(nextEvents)
      setApprovals(nextApprovals)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not refresh live activity.')
    }
  }, [])

  const refreshDeskFacts = useCallback(async () => {
    try {
      const [nextTickets, nextCash] = await Promise.all([getTickets(), getCash()])
      setTickets(nextTickets)
      setCash(nextCash)
      setLastUpdated(new Date())
      setError('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not refresh desk facts.')
    }
  }, [])

  useEffect(() => {
    void refresh()
    const activityTimer = window.setInterval(() => void refreshActivity(), 4000)
    const deskTimer = window.setInterval(() => void refreshDeskFacts(), 20000)
    return () => {
      window.clearInterval(activityTimer)
      window.clearInterval(deskTimer)
    }
  }, [refresh, refreshActivity, refreshDeskFacts])

  const startRun = async () => {
    if (!selected || runningTicket !== null || selected.status.toLowerCase() === 'resolved') return
    setRunningTicket(selected.id)
    setOutcome(null)
    setNotice('')
    setError('')
    try {
      const result = await runTicket(selected.id)
      setOutcome(result)
      setNotice('Review complete. No payment was executed during the agent run.')
      await refresh(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The ticket run could not be completed.')
    } finally {
      setRunningTicket(null)
    }
  }

  const handleApproval = async (approval: Approval, decision: 'approve' | 'reject') => {
    const approvalId = approval.approval_id
    if (!approvalId || !approver.trim()) return
    setBusyApproval(approvalId)
    setError('')
    setNotice('')
    try {
      const result = await decideApproval(approvalId, approver.trim(), decision)
      if (decision === 'approve' && result.cash_changed === true) {
        setNotice(`Approved payment executed. Checking balance refreshed from the database.`)
      } else if (decision === 'approve') {
        setNotice('Approval was recorded; the API reports that no cash changed.')
      } else {
        setNotice('Approval declined. No cash moved.')
      }
      setApprover('')
      await refresh(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Approval could not be completed. No successful payment was confirmed.')
    } finally {
      setBusyApproval(null)
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#home" aria-label="Campus Customs home">
          <span className="brand-glyph">cc<span>.</span></span>
          <span className="brand-copy"><span>Campus Customs</span><small>Operations desk</small></span>
        </a>
        <div className="topbar-center"><span className="workspace-dot" /> OPERATIONS / LIVE WORKSPACE</div>
        <div className="topbar-right">
          <span className={`connection ${error ? 'has-error' : ''}`}><span className="connection-dot" />{error ? 'Needs attention' : loading ? 'Connecting' : 'Connected'}</span>
          <button className="icon-button" type="button" onClick={() => void refresh()} aria-label="Refresh dashboard" title="Refresh">
            <RefreshCw size={15} className={refreshing ? 'spin' : ''} />
          </button>
          <span className="avatar" title="Operator">J</span>
        </div>
      </header>

      <main className="main-wrap" id="home">
        <div className="page-heading">
          <div>
            <div className="eyebrow"><span>FIELD OFFICE</span><span className="eyebrow-sep">/</span><span>01 ACTIVE DESK</span></div>
            <h1>Good work starts<br className="mobile-break" /> with a clear view.</h1>
            <p className="page-subtitle">One place to supervise decisions, evidence, and the people behind them.</p>
          </div>
          <div className="heading-meta">
            <div className="date-stamp"><span className="meta-label">DESK DATE</span><span className="meta-value">{cash?.desk_date_today ?? '—'}</span></div>
            <div className="meta-divider" />
            <div className="date-stamp"><span className="meta-label">LAST SYNC</span><span className="meta-value">{lastUpdated ? timeLabel(lastUpdated.toISOString()) : '—'}</span></div>
          </div>
        </div>

        {error && <div className="banner banner-error" role="alert"><TriangleAlert size={16} /><span><strong>Connection needs attention.</strong> {error}</span><button onClick={() => void refresh()} type="button">Retry</button></div>}
        {notice && <div className="banner banner-success" role="status"><CheckCircle2 size={16} /><span>{notice}</span><button aria-label="Dismiss message" onClick={() => setNotice('')} type="button"><X size={15} /></button></div>}

        <section className="metrics-row" aria-label="Desk overview">
          <div className="metric-label"><span className="metric-icon"><Activity size={16} /></span><span>Open work</span><strong>{tickets.filter(ticket => ticket.status.toLowerCase() !== 'resolved').length.toString().padStart(2, '0')}</strong></div>
          <div className="metric-label"><span className="metric-icon quiet"><Bell size={16} /></span><span>Needs approval</span><strong className={approvals.length ? 'metric-alert' : ''}>{approvals.length.toString().padStart(2, '0')}</strong></div>
          <div className="balance-card">
            <div className="balance-head"><span className="balance-mark"><Banknote size={15} /></span><span className="meta-label">CHECKING BALANCE</span><span className="balance-date">AS OF {cash?.date ?? '—'}</span></div>
            <div className="balance-main"><strong>{cash ? dollars(cash.balance) : '—'}</strong><span className="balance-caption"><span className="balance-dot" /> Available cash</span></div>
          </div>
        </section>

        <div className="desk-grid">
          <aside className="ticket-rail" aria-label="Ticket queue">
            <div className="rail-heading"><div><span className="section-kicker">THE QUEUE</span><h2>Tickets</h2></div><span className="count-chip">{tickets.length.toString().padStart(2, '0')}</span></div>
            <div className="ticket-list">
              {loading && tickets.length === 0 ? <div className="loading-list"><LoaderCircle size={16} className="spin" /> Loading tickets</div> : tickets.map((ticket, index) => (
                <button className={`ticket-row ${selectedId === ticket.id ? 'selected' : ''}`} key={ticket.id} onClick={() => { setSelectedId(ticket.id); setOutcome(null) }} type="button">
                  <span className="ticket-index">0{index + 1}</span>
                  <span className="ticket-row-content"><span className="ticket-row-title">{ticket.subject}</span><span className="ticket-row-sub">#{ticket.id} <span>·</span> {ticket.requester}</span></span>
                  <span className={`status-dot ${ticket.status.toLowerCase() === 'resolved' ? 'resolved' : ''}`} title={statusText(ticket.status)} />
                  <ChevronRight size={14} className="row-chevron" />
                </button>
              ))}
              {!loading && tickets.length === 0 && <div className="empty-small">No tickets returned yet.</div>}
            </div>
            <div className="rail-note"><span className="live-ring" /><span>Synced from the working desk</span></div>
            <div className="rule" />
            <div className="people-title"><span className="section-kicker">ON THE DESK</span><span className="people-online">5 roles</span></div>
            <div className="people-list">{(['Boss', 'Inventory', 'Accounting', 'Facilities', 'Customer Service'] as AgentName[]).map(role => <RoleKey key={role} role={role} />)}</div>
            <div className="privacy-note"><ShieldCheck size={14} /><span>Drafts stay internal.<br />Payments wait for you.</span></div>
          </aside>

          <section className="ticket-workspace" aria-label="Selected ticket workspace">
            {!selected ? <WorkspaceEmpty loading={loading} /> : <>
              <div className="ticket-work-head">
                <div className="ticket-title-area">
                  <div className="breadcrumb">QUEUE <ArrowRight size={11} /> TICKET {selected.id}</div>
                  <div className="title-line"><h2>{selected.subject}</h2><span className={`status-pill ${selected.status.toLowerCase() === 'resolved' ? 'is-resolved' : ''}`}><span />{statusText(selected.status)}</span></div>
                  <p className="ticket-context">{selected.requester}{selected.sku && <> <span>·</span> {selected.sku}{selected.size ? ` / ${selected.size}` : ''}</>}{selected.qty ? <> <span>·</span> Qty {selected.qty}</> : null}</p>
                </div>
                <button className={`run-button ${runIsActive ? 'is-running' : ''}`} onClick={() => void startRun()} disabled={runningTicket !== null || selected.status.toLowerCase() === 'resolved'} type="button">
                  {runIsActive ? <><LoaderCircle size={15} className="spin" /> Working</> : selected.status.toLowerCase() === 'resolved' ? <><Check size={15} /> Resolved</> : <><Play size={14} fill="currentColor" /> Start team</>}
                </button>
              </div>

              <div className="selected-note"><FileClock size={14} /><span>{selected.notes || 'No additional ticket note.'}</span><span className="created-at">Opened {new Date(selected.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span></div>

              {selected.status.toLowerCase() === 'resolved' && finalResolution && <section className="outcome-card"><div className="outcome-content"><div className="outcome-head"><span>VERIFIED FINAL DISPOSITION</span><span className="outcome-status">Resolved in database</span></div><p>{finalResolution.summary}</p>{selected.id !== 102 && <p>Internal handling only. No shipment, accepted order, or customer contact is confirmed.</p>}</div></section>}
              {visibleOutcome && <OutcomeCard outcome={visibleOutcome} />}
              {!visibleOutcome && lastBossReport && <section className="outcome-card"><div className="outcome-content"><div className="outcome-head"><span>LAST AGENT REVIEW</span><span className="outcome-status">Before subsequent actions</span></div><p>{lastBossReport.summary}</p></div></section>}

              <section className="activity-section">
                <div className="activity-heading"><div><span className="section-kicker">OBSERVABILITY</span><h3>Activity stream</h3></div><div className="activity-tools"><span className="auto-refresh"><span /> AUTO-REFRESH · 4S</span><span className="event-count">{selectedEvents.length} events</span></div></div>
                {selectedEvents.length ? <div className="timeline">{selectedEvents.slice(-24).reverse().map(event => <EventRow key={event.event_id} event={event} />)}</div> : <div className="activity-empty"><span className="empty-orbit"><Activity size={17} /></span><strong>{loading ? 'Connecting to the desk…' : 'A quiet desk is a good place to begin.'}</strong><span>{loading ? 'Recent agent events will appear here.' : 'Start the team to see evidence, handoffs, and decisions appear in real time.'}</span></div>}
              </section>
            </>}
          </section>

          <aside className="approval-rail" aria-label="Human approvals">
            <div className="approval-heading"><div><span className="section-kicker">HUMAN IN THE LOOP</span><h2>Review & approve</h2></div><span className={`approval-count ${approvals.length ? 'has-pending' : ''}`}>{approvals.length.toString().padStart(2, '0')}</span></div>
            <p className="approval-intro">Money moves only after you review the request here.</p>
            <label className="approver-field"><span>YOUR NAME FOR THE AUDIT</span><input value={approver} onChange={event => setApprover(event.target.value)} placeholder="Enter approver name" maxLength={120} /></label>
            <div className="approval-stack">
              {approvals.map(approval => <ApprovalCard key={approval.approval_id} approval={approval} busy={busyApproval === approval.approval_id} canApprove={Boolean(approver.trim())} onDecision={decision => void handleApproval(approval, decision)} />)}
              {approvals.length === 0 && <div className="approval-empty"><span className="approval-empty-icon"><CheckCircle2 size={17} /></span><strong>Nothing waiting on you.</strong><span>Payment proposals will appear here with their evidence and cash impact.</span></div>}
            </div>
            <div className="approval-safety"><ShieldCheck size={15} /><span>Approval triggers a fresh balance check. A payment that would overdraw checking is blocked.</span></div>
            <div className="quiet-foot"><span><Command size={12} /> Campus Customs desk</span><span>LOCAL · PRIVATE</span></div>
          </aside>
        </div>

        <footer className="app-footer"><span><span className="footer-mark">CC</span> A calmer way to keep the shop moving.</span><span>AGENT ACTIONS ARE EVIDENCE-LED <span className="footer-divider">·</span> CASH IS HUMAN-APPROVED</span></footer>
      </main>
    </div>
  )
}

function RoleKey({ role }: { role: AgentName }) {
  return <div className="person-row"><span className={`agent-mark ${ROLE_CLASS[role]}`}>{ROLE_MARK[role]}</span><span className="person-name">{role}</span><span className="person-presence" /></div>
}

function EventRow({ event }: { event: AgentEvent }) {
  const role = event.agent
  const delegation = event.delegated_to ? `→ ${event.delegated_to}` : null
  const tool = event.tool_name
  const tone = event.event_type.includes('failed') || event.event_type.includes('blocked') ? 'event-warning' : event.event_type.includes('completed') || event.event_type.includes('executed') ? 'event-done' : ''
  return <article className={`event-row ${tone}`}>
    <div className="event-time">{timeLabel(event.timestamp)}</div>
    <div className="event-mark-col"><span className={`agent-mark ${ROLE_CLASS[role]}`}>{ROLE_MARK[role]}</span><span className="event-stem" /></div>
    <div className="event-body">
      <div className="event-top"><strong>{role}</strong><span className="event-type">{event.event_type.replaceAll('_', ' ')}</span>{delegation && <span className="delegation-chip">{delegation}</span>}</div>
      <p>{event.summary}</p>
      {tool && <span className="tool-chip"><Command size={11} />{tool}</span>}
      {typeof event.details?.result_summary === 'string' && <span className="event-detail">{event.details.result_summary}</span>}
      {event.details?.decision === 'approve' && <span className="event-detail">Human approval recorded · cash execution tracked separately.</span>}
    </div>
    <span className="event-state"><CircleDot size={12} /></span>
  </article>
}

function OutcomeCard({ outcome }: { outcome: TicketOutcome }) {
  const label = outcome.status.replaceAll('_', ' ')
  return <section className={`outcome-card outcome-${outcome.status}`}>
    <div className="outcome-icon">{outcome.status === 'blocked' ? <TriangleAlert size={17} /> : outcome.status === 'needs_approval' ? <Pause size={17} /> : <Sparkles size={17} />}</div>
    <div className="outcome-content"><div className="outcome-head"><span>AGENT REVIEW SNAPSHOT</span><span className="outcome-status">{label} · before subsequent actions</span></div><p>{outcome.summary}</p><div className="outcome-meta"><span>{outcome.agent_invocations} agent steps</span><span>{outcome.delegation_count} handoffs</span><span>{outcome.mcp_calls} MCP calls</span></div>{outcome.drafts.map((draft, index) => <details key={index}><summary>Internal draft {index + 1} · not sent</summary><p>{draft}</p></details>)}</div>
  </section>
}

function ApprovalCard({ approval, busy, canApprove, onDecision }: { approval: Approval; busy: boolean; canApprove: boolean; onDecision: (decision: 'approve' | 'reject') => void }) {
  const request = approval.details?.request ?? {}
  const quote = approval.details?.authoritative_quote ?? {}
  const amount = request.amount ?? quote.amount
  const kind = request.payment_kind ?? 'purchase'
  const resolution = kind === 'ticket_resolution'
  const supportedPayment = resolution || kind === 'invoice' || kind === 'lease'
  const item = quote.description ?? (resolution ? 'Internal case disposition' : kind === 'invoice' ? `Invoice ${request.reference_id ?? ''}` : kind === 'lease' ? `Lease ${request.reference_id ?? ''} rent` : `Purchase ${request.reference_id ?? ''}`)
  const remaining = quote.balance_after_payment
  return <article className="approval-card">
    <div className="approval-card-top"><span className="approval-type"><span className="approval-type-dot" />{kind} request</span><span className="approval-ticket">T{approval.ticket_id ?? '—'}</span></div>
    <h3>{item}</h3>
    <p className="approval-rationale">{request.rationale ?? approval.summary}</p>
    {resolution ? <><p className="approval-rationale">{quote.summary} No cash moves. This does not confirm shipment or accept an order.</p><details><summary>Review exact unsent draft</summary><p>{quote.draft}</p></details></> : <div className="money-impact"><div><span>REQUESTED</span><strong>{typeof amount === 'number' ? dollars(amount) : 'Amount pending'}</strong></div><ArrowDownRight size={15} /><div><span>AFTER PAYMENT</span><strong>{typeof remaining === 'number' ? dollars(remaining) : 'Rechecked on approval'}</strong></div></div>}
    <div className="approval-evidence"><span className="evidence-check"><Check size={11} /></span><span>{quote.can_pay_if_human_approved === false ? quote.blocked_reason ?? 'Current payment quote is blocked.' : 'Database quote attached · balance will be checked again.'}</span></div>
    <div className="approval-actions"><button className="decline-button" disabled={busy || !canApprove} onClick={() => onDecision('reject')} type="button">Decline</button><button className="approve-button" disabled={busy || !canApprove || !supportedPayment || quote.can_pay_if_human_approved === false || quote.can_finalize_if_human_approved === false} onClick={() => onDecision('approve')} type="button">{busy ? <LoaderCircle size={14} className="spin" /> : <BadgeCheck size={15} />} {resolution ? 'Approve resolution' : 'Approve'}</button></div>
    {!canApprove && <span className="approval-hint">Add your name above to enable review.</span>}
    {canApprove && !supportedPayment && <span className="approval-hint">Purchase execution is not supported by the current API.</span>}
  </article>
}

function WorkspaceEmpty({ loading }: { loading: boolean }) {
  return <div className="workspace-empty"><span className="empty-orbit"><Activity size={18} /></span><strong>{loading ? 'Setting up your desk…' : 'Choose a ticket to begin.'}</strong><span>The selected ticket’s evidence and activity will live here.</span></div>
}

export default App
