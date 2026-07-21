import type { Card, CashProfile, CashflowResponse } from "../../api/types";

interface Props {
  cards?: Card[];
  cash?: CashProfile;
  cashflow?: CashflowResponse;
}

export function OnboardingCard({ cards, cash, cashflow }: Props) {
  const items: string[] = [];
  if (!cards || cards.length === 0) items.push("添加信用卡");
  if (!cash || cash.available_cash === null) items.push("起始资金未设置");
  if (cashflow && cashflow.days.every((d) => d.settlements === "0.00")) {
    items.push("导入结算数据");
  }

  if (items.length === 0) return null;

  return (
    <div className="card onboarding-card">
      <h3>待完善</h3>
      <ul>
        {items.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
    </div>
  );
}
