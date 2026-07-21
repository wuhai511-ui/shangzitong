import { useState } from "react";
import { usePutCashMutation } from "../../api/queries";
import { normalizeCashInput } from "../../lib/format";

interface Props {
  initial?: string | null;
}

export function AvailableCashForm({ initial }: Props) {
  const [value, setValue] = useState(initial ?? "");
  const [error, setError] = useState<string | null>(null);
  const putCash = usePutCashMutation();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const normalized = normalizeCashInput(value);
    if (normalized === undefined) {
      setError("金额格式错误，最多两位小数");
      return;
    }
    setError(null);
    putCash.mutate(normalized);
  }

  return (
    <form className="card cash-form" onSubmit={handleSubmit}>
      <label htmlFor="available-cash">当前可用资金</label>
      <input
        id="available-cash"
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="留空表示未设置"
        aria-label="当前可用资金"
      />
      {error && <span className="form-error">{error}</span>}
      <button type="submit" disabled={putCash.isPending}>
        {putCash.isPending ? "保存中" : "保存并重新计算"}
      </button>
    </form>
  );
}
