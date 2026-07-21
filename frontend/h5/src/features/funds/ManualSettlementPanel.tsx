import { useState } from "react";
import {
  useManualSettlementsQuery,
  useCreateManualSettlementMutation,
  useDeleteManualSettlementMutation,
} from "../../api/queries";
import {
  LoadingState,
  EmptyState,
  ErrorState,
} from "../../components/AsyncState";
import { formatYuan, normalizeCashInput } from "../../lib/format";
import type { ManualSettlementPeriodType } from "../../api/types";

function toPeriodDate(raw: string, type: ManualSettlementPeriodType): string {
  if (!raw) return "";
  if (type === "month") {
    const [year, month] = raw.split("-");
    return `${year}-${month}-01`;
  }
  return raw;
}

function formatPeriod(periodType: ManualSettlementPeriodType, periodDate: string): string {
  const [year, month, day] = periodDate.split("-");
  if (periodType === "month") {
    return `${year}年${Number(month)}月`;
  }
  return `${year}-${month}-${day}`;
}

export function ManualSettlementPanel() {
  const [periodType, setPeriodType] = useState<ManualSettlementPeriodType>("day");
  const [dateValue, setDateValue] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const list = useManualSettlementsQuery();
  const createMut = useCreateManualSettlementMutation();
  const deleteMut = useDeleteManualSettlementMutation();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const normalized = normalizeCashInput(amount);
    if (normalized === undefined || normalized === null) {
      setError("金额不能为空且最多两位小数");
      return;
    }
    if (Number(normalized) < 0) {
      setError("金额不能为负");
      return;
    }
    const periodDate = toPeriodDate(dateValue, periodType);
    if (!periodDate) {
      setError("请选择日期");
      return;
    }
    setError(null);
    createMut.mutate(
      { period_type: periodType, period_date: periodDate, amount: normalized, note: note.trim() || undefined },
      {
        onSuccess: () => {
          setAmount("");
          setNote("");
        },
      },
    );
  }

  function handleDelete(id: number) {
    if (window.confirm("确认删除这条手动结算记录？")) {
      deleteMut.mutate(id);
    }
  }

  return (
    <section className="card manual-settlement-panel">
      <h3>手动结算录入</h3>
      <form className="manual-settlement-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            <input
              type="radio"
              name="period-type"
              value="day"
              checked={periodType === "day"}
              onChange={() => setPeriodType("day")}
            />
            按日
          </label>
          <label>
            <input
              type="radio"
              name="period-type"
              value="month"
              checked={periodType === "month"}
              onChange={() => setPeriodType("month")}
            />
            按月
          </label>
        </div>
        <label htmlFor="ms-date">
          {periodType === "day" ? "结算日期" : "结算月份"}
        </label>
        <input
          id="ms-date"
          type={periodType === "day" ? "date" : "month"}
          value={dateValue}
          onChange={(e) => setDateValue(e.target.value)}
          aria-label={periodType === "day" ? "结算日期" : "结算月份"}
        />
        <label htmlFor="ms-amount">结算金额</label>
        <input
          id="ms-amount"
          type="text"
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.00"
          aria-label="结算金额"
        />
        <label htmlFor="ms-note">备注（选填）</label>
        <input
          id="ms-note"
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="备注"
          aria-label="备注"
        />
        {error && <span className="form-error">{error}</span>}
        <button type="submit" disabled={createMut.isPending}>
          {createMut.isPending ? "保存中" : "保存"}
        </button>
      </form>

      <div className="manual-settlement-list">
        {list.isLoading && <LoadingState />}
        {list.isError && <ErrorState onRetry={() => list.refetch()} />}
        {list.isSuccess && Array.isArray(list.data) && list.data.length === 0 && (
          <EmptyState label="暂无手动结算记录" />
        )}
        {list.isSuccess && Array.isArray(list.data) && list.data.map((item) => (
          <div className="manual-settlement-item" key={item.id} data-testid="manual-settlement-item">
            <span className="ms-type">{item.period_type === "month" ? "月" : "日"}</span>
            <span className="ms-period">{formatPeriod(item.period_type, item.period_date)}</span>
            <span className="ms-amount">{formatYuan(item.amount)}</span>
            {item.note && <span className="ms-note">{item.note}</span>}
            <button
              type="button"
              className="ms-delete"
              onClick={() => handleDelete(item.id)}
              disabled={deleteMut.isPending}
              aria-label={`删除 ${formatPeriod(item.period_type, item.period_date)}`}
            >
              删除
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
