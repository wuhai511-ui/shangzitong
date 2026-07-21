/** Shared typed contracts for the H5 frontend. */

export interface User {
  id: number;
  openid: string;
  nickname: string;
}

export interface CashProfile {
  available_cash: string | null;
  available_cash_updated_at: string | null;
  is_estimate: boolean;
}

export interface CashflowDay {
  date: string;
  opening_balance: string;
  settlements: string;
  repayments: string;
  purchases: string;
  other_outflows: string;
  closing_balance: string;
  funding_gap: string;
  events: Array<Record<string, unknown>>;
}

export interface CashflowResponse {
  days: CashflowDay[];
  is_estimate: boolean;
  available_cash: string | null;
  available_cash_updated_at: string | null;
}

export interface Card {
  id: number;
  user_id: number;
  bank_name: string;
  card_tail: string;
  credit_limit: string;
  temp_limit: string;
  used_limit: string;
  overpayment: string;
  avail_limit: string;
  bill_day: number;
  due_day: number;
  swipe_fee_rate: string;
  interest_rate: string;
  min_payment_ratio: string;
  installment_amount: string;
  bill_day_inclusive: number;
  status: number;
}

export interface CardCreateInput {
  bank_name: string;
  card_tail?: string;
  credit_limit: string;
  used_limit?: string;
  temp_limit?: string;
  overpayment?: string;
  bill_day: number;
  due_day: number;
  swipe_fee_rate?: string;
  interest_rate?: string;
  min_payment_ratio?: string;
  installment_amount?: string;
  bill_day_inclusive?: number;
}

export type CardUpdateInput = Partial<CardCreateInput>;

export interface UploadPreview {
  preview_id: string;
  mappings: Record<string, string>;
  preview_rows: Array<Record<string, unknown>>;
  total_rows: number;
  expires_at: string;
}

export interface UploadConfirmInput {
  preview_id: string;
  mappings: Record<string, string>;
  provider: string;
}

export interface UploadConfirmResponse {
  imported: number;
}

export interface Recommendation {
  card_id: number;
  bank_name: string;
  optimal_date: string;
  free_days: number;
  swipe_cost: string;
  daily_cost: string;
  repayment_date: string;
  risk_weight: number;
  score?: number;
}

export interface RecommendResponse {
  recommendations: Recommendation[];
  multi_card_split: Array<{ card_id: number; bank_name: string; allocated: string }>;
  coverage_ratio: number;
  gap_amount: string;
  warnings: string[];
}

export interface ScheduleEntry {
  date: string;
  cash_pool: string;
  funding_gap: string;
  settlements: Array<{ amount: string }>;
  repayments: Array<Record<string, unknown>>;
  alerts: Array<{ type: string; message: string }>;
}

export interface ScheduleResponse {
  days: ScheduleEntry[];
}

export interface StopLossPlan {
  name: string;
  description: string;
  cost: string;
  total: string;
}

export interface StopLossResponse {
  plan_a: StopLossPlan;
  plan_b: StopLossPlan;
  plan_c: StopLossPlan;
  recommendation: string;
  recommendation_reason: string;
}

export interface RepaymentAlert {
  card_id?: number;
  bank_name?: string;
  amount?: string;
  min_payment?: string;
  type?: string;
  due_date: string;
  funding_gap: string;
  gap_warning: boolean;
  recommended_action: string;
}

export interface AlertsUpcomingResponse {
  repayments: RepaymentAlert[];
}

export interface DailySummaryResponse {
  date: string;
  total_due: string;
  forecasted_settlements: string;
  gap: string;
  repayments: RepaymentAlert[];
}

export interface MonthlyReport {
  score: number;
  grade: string;
  dimensions: Record<string, number>;
  card_count: number;
  total_limit: string;
  avg_utilization: number;
  suggestions: string[];
  repayment_data_status: string;
}

export interface ApiError extends Error {
  code: string;
  requestId: string;
  status: number;
}


export type ManualSettlementPeriodType = "day" | "month";

export interface ManualSettlement {
  id: number;
  period_type: ManualSettlementPeriodType;
  period_date: string;
  amount: string;
  note: string | null;
  created_at: string;
}

export interface ManualSettlementCreateInput {
  period_type: ManualSettlementPeriodType;
  period_date: string;
  amount: string;
  note?: string;
}
