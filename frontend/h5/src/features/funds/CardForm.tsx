import { useState } from "react";
import { useCreateCardMutation } from "../../api/queries";

interface Props {
  onDone?: () => void;
}

export function CardForm({ onDone }: Props) {
  const create = useCreateCardMutation();
  const [form, setForm] = useState({
    bank_name: "",
    card_tail: "",
    credit_limit: "",
    used_limit: "0",
    bill_day: "1",
    due_day: "1",
  });
  const [error, setError] = useState<string | null>(null);

  function update(key: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const billDay = Number(form.bill_day);
    const dueDay = Number(form.due_day);
    if (!form.bank_name.trim()) {
      setError("请填写银行名称");
      return;
    }
    if (billDay < 1 || billDay > 28) {
      setError("账单日需在 1-28 之间");
      return;
    }
    if (dueDay < 1 || dueDay > 31) {
      setError("还款日需在 1-31 之间");
      return;
    }
    if (Number(form.used_limit) > Number(form.credit_limit)) {
      setError("已用额度不能超过总额度");
      return;
    }
    setError(null);
    create.mutate(
      {
        bank_name: form.bank_name.trim(),
        card_tail: form.card_tail.trim(),
        credit_limit: Number(form.credit_limit).toFixed(2),
        used_limit: Number(form.used_limit).toFixed(2),
        bill_day: billDay,
        due_day: dueDay,
      },
      { onSuccess: () => onDone?.() },
    );
  }

  return (
    <form className="card-form" onSubmit={handleSubmit}>
      <label>
        银行名称
        <input value={form.bank_name} onChange={(e) => update("bank_name", e.target.value)} />
      </label>
      <label>
        卡号尾号
        <input
          value={form.card_tail}
          maxLength={4}
          onChange={(e) => update("card_tail", e.target.value)}
        />
      </label>
      <label>
        总额度
        <input
          value={form.credit_limit}
          inputMode="decimal"
          onChange={(e) => update("credit_limit", e.target.value)}
        />
      </label>
      <label>
        已用额度
        <input
          value={form.used_limit}
          inputMode="decimal"
          onChange={(e) => update("used_limit", e.target.value)}
        />
      </label>
      <label>
        账单日
        <input
          type="number"
          min={1}
          max={28}
          value={form.bill_day}
          onChange={(e) => update("bill_day", e.target.value)}
        />
      </label>
      <label>
        还款日
        <input
          type="number"
          min={1}
          max={31}
          value={form.due_day}
          onChange={(e) => update("due_day", e.target.value)}
        />
      </label>
      {error && <span className="form-error">{error}</span>}
      <button type="submit" disabled={create.isPending}>
        {create.isPending ? "保存中" : "保存卡片"}
      </button>
    </form>
  );
}
