import { useAlertsUpcomingQuery, useDailySummaryQuery } from "../../api/queries";
import type { RepaymentAlert } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/AsyncState";
import { formatDate, formatYuan } from "../../lib/format";

function groupAlerts(repayments: RepaymentAlert[]) {
  const urgent = repayments.filter((r) => Number(r.funding_gap) > 0);
  const upcoming = repayments.filter((r) => Number(r.funding_gap) <= 0);
  return { urgent, upcoming };
}

export function AlertsPage() {
  const upcoming = useAlertsUpcomingQuery();
  const summary = useDailySummaryQuery();

  const groups = upcoming.data ? groupAlerts(upcoming.data.repayments) : null;

  return (
    <div className="page">
      <h2>提醒</h2>

      <section className="card panel">
        <h3>今日概览</h3>
        {summary.isLoading && <LoadingState label="加载概览中" />}
        {summary.error && <ErrorState onRetry={() => summary.refetch()} />}
        {summary.data && (
          <div className="summary-grid">
            <div className="card">
              <span className="metric-label">今日应还</span>
              <span className="metric-value">{formatYuan(summary.data.total_due)}</span>
            </div>
            <div className="card">
              <span className="metric-label">预计入账</span>
              <span className="metric-value">{formatYuan(summary.data.forecasted_settlements)}</span>
            </div>
            <div className="card">
              <span className="metric-label">资金缺口</span>
              <span className={`metric-value ${Number(summary.data.gap) > 0 ? "danger" : ""}`}>
                {formatYuan(summary.data.gap)}
              </span>
            </div>
          </div>
        )}
      </section>

      <section className="card panel">
        <h3>紧急</h3>
        {upcoming.isLoading && <LoadingState label="加载提醒中" />}
        {upcoming.error && <ErrorState onRetry={() => upcoming.refetch()} />}
        {groups && groups.urgent.length === 0 && <p className="muted">暂无紧急提醒</p>}
        {groups && groups.urgent.length > 0 && (
          <ul className="card-list">
            {groups.urgent.map((r, i) => (
              <li key={i} className="card-item">
                <div className="card-item-main">
                  <span className="card-bank danger">{formatDate(r.due_date)} 应还</span>
                  <span className="card-tail danger">
                    <span>缺口 </span>
                    <span>{formatYuan(r.funding_gap)}</span>
                  </span>
                </div>
                {r.recommended_action && <p className="muted">{r.recommended_action}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card panel">
        <h3>即将到期</h3>
        {groups && groups.upcoming.length === 0 && <p className="muted">暂无即将到期提醒</p>}
        {groups && groups.upcoming.length > 0 && (
          <ul className="card-list">
            {groups.upcoming.map((r, i) => (
              <li key={i} className="card-item">
                <div className="card-item-main">
                  <span className="card-bank">{formatDate(r.due_date)} 应还</span>
                  <span className="card-tail">{formatYuan(r.amount ?? "0.00")}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card panel">
        <h3>已处理</h3>
        <p className="muted">暂无已处理提醒</p>
      </section>
    </div>
  );
}
