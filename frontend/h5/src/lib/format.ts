/** Formatting helpers for money and dates in the H5 UI. */

export function formatYuan(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) {
    return "—";
  }
  return (
    "¥" +
    num.toLocaleString("zh-CN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

/** Normalize a raw cash input into a 2-decimal string, null (blank), or undefined (invalid). */
export function normalizeCashInput(raw: string): string | null | undefined {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) return undefined;
  return Number(trimmed).toFixed(2);
}

export function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}
