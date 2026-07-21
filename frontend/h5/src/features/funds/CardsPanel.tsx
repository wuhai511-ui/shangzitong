import { useState } from "react";
import { useCardsQuery, useDeleteCardMutation } from "../../api/queries";
import type { Card } from "../../api/types";
import { EmptyState, ErrorState, LoadingState } from "../../components/AsyncState";
import { formatYuan } from "../../lib/format";
import { CardForm } from "./CardForm";

function utilization(card: Card): string {
  const limit = Number(card.credit_limit);
  if (limit <= 0) return "0%";
  return Math.round((Number(card.used_limit) / limit) * 100) + "%";
}

export function CardsPanel() {
  const cards = useCardsQuery();
  const remove = useDeleteCardMutation();
  const [adding, setAdding] = useState(false);

  return (
    <section className="card panel">
      <div className="panel-header">
        <h3>信用卡</h3>
        <button type="button" onClick={() => setAdding((v) => !v)}>
          {adding ? "取消" : "添加卡片"}
        </button>
      </div>

      {adding && <CardForm onDone={() => setAdding(false)} />}

      {cards.isLoading && <LoadingState label="加载卡片" />}
      {cards.error && <ErrorState onRetry={() => cards.refetch()} />}
      {cards.data && cards.data.length === 0 && <EmptyState label="暂无信用卡" />}
      {cards.data && cards.data.length > 0 && (
        <ul className="card-list">
          {cards.data.map((card) => (
            <li key={card.id} className="card-item">
              <div className="card-item-main">
                <span className="card-bank">{card.bank_name}</span>
                <span className="card-tail">尾号 {card.card_tail || "****"}</span>
              </div>
              <div className="card-item-meta">
                <span>额度 {formatYuan(card.credit_limit)}</span>
                <span>已用 {formatYuan(card.used_limit)}</span>
                <span>使用率 {utilization(card)}</span>
              </div>
              <button
                type="button"
                className="link-button"
                onClick={() => remove.mutate(card.id)}
              >
                删除
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
