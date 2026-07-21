import { useMonthlyReportQuery } from "../../api/queries";
import { ErrorState, LoadingState } from "../../components/AsyncState";
import { formatYuan } from "../../lib/format";

export function ReportPage() {
  const report = useMonthlyReportQuery();

  return (
    <div className="page">
      <h2>我的</h2>

      {report.isLoading && <LoadingState label="生成报告中" />}
      {report.error && <ErrorState onRetry={() => report.refetch()} />}
      {report.data && (
        <>
          <section className="card panel score-card">
            <span className="metric-label">健康评分</span>
            <span className="score-value">{report.data.score}</span>
            <span className="score-grade">{report.data.grade}</span>
          </section>

          <section className="card panel">
            <h3>评估维度</h3>
            <ul className="card-list">
              {Object.entries(report.data.dimensions).map(([name, value]) => (
                <li key={name} className="card-item">
                  <div className="card-item-main">
                    <span className="card-bank">{name}</span>
                    <span className="card-tail">{value}</span>
                  </div>
                </li>
              ))}
            </ul>
            {report.data.repayment_data_status === "unavailable" && (
              <p className="muted">暂无真实还款记录</p>
            )}
          </section>

          <section className="card panel">
            <h3>额度使用</h3>
            <div className="card-item-meta">
              <span>卡片数量 {report.data.card_count}</span>
              <span>总额度 {formatYuan(report.data.total_limit)}</span>
              <span>平均使用率 {report.data.avg_utilization}%</span>
            </div>
          </section>

          {report.data.suggestions.length > 0 && (
            <section className="card panel">
              <h3>建议</h3>
              <ul className="card-list">
                {report.data.suggestions.map((s, i) => (
                  <li key={i} className="card-item">{s}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
