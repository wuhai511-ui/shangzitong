import { useCardsQuery, useCashProfileQuery, useCashflowQuery } from "../../api/queries";
import type { CashflowDay } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/AsyncState";
import { formatDate, formatYuan } from "../../lib/format";
import { AvailableCashForm } from "../funds/AvailableCashForm";
import { CashflowChart } from "./CashflowChart";
import { OnboardingCard } from "./OnboardingCard";

function minClosingBalance(days: CashflowDay[]): string {
  return days.reduce((min, d) =>
    Number(d.closing_balance) < Number(min) ? d.closing_balance : min,
  days[0]?.closing_balance ?? "0.00");
}

function earliestGap(days: CashflowDay[]): { date: string; amount: string } | null {
  const gap = days.find((d) => Number(d.funding_gap) > 0);
  if (!gap) return null;
  return { date: gap.date, amount: gap.funding_gap };
}

function todaySettlements(days: CashflowDay[]): string {
  return days[0]?.settlements ?? "0.00";
}

function sevenDayRepayments(days: CashflowDay[]): string {
  return days
    .slice(0, 7)
    .reduce((sum, d) => sum + Number(d.repayments), 0)
    .toFixed(2);
}

export function DashboardPage() {
  const cashflow = useCashflowQuery(30);
  const cards = useCardsQuery();
  const profile = useCashProfileQuery();

  return (
    <div className="page">
      <h2>资金指挥舱</h2>
      {cashflow.isLoading && <LoadingState />}
      {cashflow.error && <ErrorState onRetry={() => cashflow.refetch()} />}
      {cashflow.data && (
        <>
          {cashflow.data.is_estimate && (
            <div className="estimate-banner" role="status">
              <span>试算</span>
              <span className="estimate-hint">数据为估算，设置起始资金后更精准</span>
            </div>
          )}

          <div className="summary-grid">
            <div className="card">
              <span className="metric-label">30日最低余额</span>
              <span className="metric-value">{formatYuan(minClosingBalance(cashflow.data.days))}</span>
            </div>
            <div className="card">
              <span className="metric-label">今日结算</span>
              <span className="metric-value">{formatYuan(todaySettlements(cashflow.data.days))}</span>
            </div>
            <div className="card">
              <span className="metric-label">7日应还</span>
              <span className="metric-value">{formatYuan(sevenDayRepayments(cashflow.data.days))}</span>
            </div>
            <div className="card">
              <span className="metric-label">最早缺口</span>
              {(() => {
                const gap = earliestGap(cashflow.data.days);
                return gap ? (
                  <span className="metric-value danger">
                    {formatDate(gap.date)} {formatYuan(gap.amount)}
                  </span>
                ) : (
                  <span className="metric-value">无缺口</span>
                );
              })()}
            </div>
          </div>

          <CashflowChart days={cashflow.data.days} />

          <AvailableCashForm initial={cashflow.data.available_cash} />

          <OnboardingCard
            cards={cards.data}
            cash={profile.data}
            cashflow={cashflow.data}
          />
        </>
      )}
    </div>
  );
}
