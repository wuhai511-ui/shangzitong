import type { UseQueryResult } from "@tanstack/react-query";
import type { ScheduleResponse } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/AsyncState";
import { formatDate, formatYuan } from "../../lib/format";

interface Props {
  query: UseQueryResult<ScheduleResponse>;
}

export function SchedulePanel({ query }: Props) {
  return (
    <section className="card panel">
      <h3>资金安排</h3>
      {query.isLoading && <LoadingState label="加载安排中" />}
      {query.error && <ErrorState onRetry={() => query.refetch()} />}
      {query.data && (
        <ul className="card-list">
          {query.data.days.slice(0, 7).map((day) => (
            <li key={day.date} className="card-item">
              <div className="card-item-main">
                <span className="card-bank">{formatDate(day.date)}</span>
                <span className="card-tail">余额 {formatYuan(day.cash_pool)}</span>
              </div>
              {Number(day.funding_gap) > 0 && (
                <div className="card-item-meta">
                  <span className="danger">资金缺口 {formatYuan(day.funding_gap)}</span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
