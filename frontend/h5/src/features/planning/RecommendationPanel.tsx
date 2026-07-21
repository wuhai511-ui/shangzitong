import type { UseQueryResult } from "@tanstack/react-query";
import type { RecommendResponse } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/AsyncState";
import { formatYuan } from "../../lib/format";

interface Props {
  query: UseQueryResult<RecommendResponse>;
}

export function RecommendationPanel({ query }: Props) {
  return (
    <section className="card panel">
      <h3>进货推荐</h3>
      {query.isLoading && <LoadingState label="计算推荐中" />}
      {query.error && <ErrorState onRetry={() => query.refetch()} />}
      {query.data && query.data.recommendations.length === 0 && (
        <p className="muted">暂无可用推荐，请先添加信用卡。</p>
      )}
      {query.data && query.data.recommendations.length > 0 && (
        <ul className="card-list">
          {query.data.recommendations.map((rec, index) => (
            <li key={rec.card_id} className="card-item" data-testid="recommendation-card">
              <div className="card-item-main">
                <span className="card-bank">#{index + 1} {rec.bank_name}</span>
                <span className="card-tail">免息 {rec.free_days} 天</span>
              </div>
              <div className="card-item-meta">
                <span>手续费 {formatYuan(rec.swipe_cost)}</span>
                <span>建议刷卡日 {rec.optimal_date}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
      {query.data && query.data.warnings.length > 0 && (
        <div className="estimate-banner">
          <span>{query.data.warnings[0]}</span>
        </div>
      )}
    </section>
  );
}
