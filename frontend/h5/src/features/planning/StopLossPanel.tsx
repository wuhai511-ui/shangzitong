import { useEffect } from "react";
import { useStopLossMutation } from "../../api/queries";
import { formatYuan } from "../../lib/format";

interface Props {
  gapAmount: string;
  cardId?: number;
}

const PLANS = [
  { key: "plan_a", label: "全额借款" },
  { key: "plan_b", label: "最低还款" },
  { key: "plan_c", label: "分期" },
] as const;

export function StopLossPanel({ gapAmount, cardId }: Props) {
  const stoploss = useStopLossMutation();

  useEffect(() => {
    if (cardId && Number(gapAmount) > 0) {
      stoploss.mutate({ cardId, gapAmount });
    }
  }, [cardId, gapAmount]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className="card panel">
      <h3>止损方案</h3>
      <p className="muted">资金缺口 {formatYuan(gapAmount)}，请谨慎选择还款策略。</p>
      <div className="stoploss-grid">
        {PLANS.map((plan) => {
          const data = stoploss.data?.[plan.key];
          return (
            <div key={plan.key} className="card-item" data-testid="stoploss-plan">
              <h4>{plan.label}</h4>
              {data && (
                <div className="card-item-meta">
                  <span>总成本 {formatYuan(data.cost)}</span>
                  <span>合计 {formatYuan(data.total)}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="muted caution">以上为成本估算，不保证审批通过或必然节省。</p>
    </section>
  );
}
