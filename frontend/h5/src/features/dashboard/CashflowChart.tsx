import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CashflowDay } from "../../api/types";
import { formatDate } from "../../lib/format";

export function CashflowChart({ days }: { days: CashflowDay[] }) {
  const data = days.map((d) => ({
    date: formatDate(d.date),
    balance: Number(d.closing_balance),
  }));
  return (
    <div className="card chart-card">
      <h3>30日资金趋势</h3>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="balance-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--mint)" stopOpacity={0.5} />
              <stop offset="100%" stopColor="var(--mint)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fill: "var(--muted)", fontSize: 11 }} interval={4} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} width={48} />
          <Tooltip
            contentStyle={{
              background: "var(--ink-800)",
              border: "1px solid var(--line)",
              borderRadius: 8,
              color: "var(--text)",
            }}
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke="var(--mint)"
            fill="url(#balance-gradient)"
            strokeWidth={2}
            name="余额"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
