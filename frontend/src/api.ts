import type { AgentEvent, Approval, CashAccount, Ticket, TicketOutcome } from './types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const data = await response.json() as { detail?: string }
      if (data.detail) message = data.detail
    } catch { /* keep the concise status message */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function getTickets(): Promise<Ticket[]> {
  const data = await request<{ tickets: Ticket[] }>('/tickets')
  return data.tickets
}

export async function getCash(): Promise<CashAccount> {
  const data = await request<{ account: CashAccount }>('/cash')
  return data.account
}

export async function getEvents(ticketId?: number): Promise<AgentEvent[]> {
  const query = new URLSearchParams({ limit: '100' })
  if (ticketId) query.set('ticket_id', String(ticketId))
  const data = await request<{ events: AgentEvent[] }>(`/events?${query}`)
  return data.events
}

export async function getPendingApprovals(): Promise<Approval[]> {
  const data = await request<{ approvals: Approval[] }>('/approvals/pending')
  return data.approvals
}

export function runTicket(ticketId: number): Promise<TicketOutcome> {
  return request<TicketOutcome>(`/tickets/${ticketId}/run`, { method: 'POST' })
}

export function decideApproval(approvalId: string, approvedBy: string, decision: 'approve' | 'reject') {
  return request<{ approval_id: string; decision: string; cash_changed: boolean; payment?: Record<string, unknown> }>(
    `/approvals/${approvalId}/decision`,
    { method: 'POST', body: JSON.stringify({ approved_by: approvedBy, decision }) },
  )
}
