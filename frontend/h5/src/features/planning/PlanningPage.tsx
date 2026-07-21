import { useState } from "react";
import { useCardsQuery, useRecommendQuery, useScheduleQuery } from "../../api/queries";
import { RecommendationPanel } from "./RecommendationPanel";
import { SchedulePanel } from "./SchedulePanel";
import { StopLossPanel } from "./StopLossPanel";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function PlanningPage() {
  const [amount, setAmount] = useState("1000");
  const purchaseDate = todayIso();
  const recommend = useRecommendQuery(Number(amount), purchaseDate);
  const schedule = useScheduleQuery();
  const cards = useCardsQuery();

  const gapDay = schedule.data?.days.find((d) => Number(d.funding_gap) > 0);
  const firstCard = cards.data?.[0];

  return (
    <div className="page">
      <h2>规划</h2>

      <div className="card cash-form">
        <label htmlFor="purchase-amount">进货金额</label>
        <input
          id="purchase-amount"
          type="text"
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </div>

      <RecommendationPanel query={recommend} />
      <SchedulePanel query={schedule} />
      {gapDay && (
        <StopLossPanel gapAmount={gapDay.funding_gap} cardId={firstCard?.id} />
      )}
    </div>
  );
}
