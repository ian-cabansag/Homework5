export type AgentName = 'Boss' | 'Inventory' | 'Accounting' | 'Facilities' | 'Customer Service' | 'Human' | 'System'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
}

export interface AgentEvent {
  event_id: string
  timestamp: string
  run_id: string
  ticket_id: number | null
  agent: AgentName
  event_type: string
  summary: string
  tool_name?: string | null
  delegated_to?: AgentName | null
  approval_id?: string | null
  details: Record<string, unknown>
}

export interface TicketOutcome {
  run_id: string
  ticket_id: number
  status: 'ready' | 'needs_approval' | 'blocked' | 'draft_only'
  summary: string
  evidence_refs: string[]
  recommendations: string[]
  drafts: string[]
  pending_approval_ids: string[]
  specialist_reports: Array<Record<string, unknown>>
  agent_invocations: number
  mcp_calls: number
  delegation_count: number
  stop_reason: string
}

export interface Approval {
  event_id: string
  timestamp: string
  run_id: string
  ticket_id: number | null
  agent: AgentName
  event_type: string
  summary: string
  tool_name?: string | null
  approval_id?: string | null
  details: {
    request?: {
      payment_kind?: string
      reference_id?: number
      amount?: number
      rationale?: string
      evidence_refs?: string[]
      [key: string]: unknown
    }
    authoritative_quote?: {
      description?: string
      amount?: number
      checking_balance?: number
      balance_after_payment?: number
      desk_date_today?: string
      can_pay_if_human_approved?: boolean
      blocked_reason?: string | null
    }
    [key: string]: unknown
  }
}

export interface CashAccount {
  name: string
  balance: number
  date: string
}
