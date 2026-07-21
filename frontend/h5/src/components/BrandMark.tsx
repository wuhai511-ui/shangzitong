import { Wallet } from "lucide-react";

export function BrandMark({ className }: { className?: string }) {
  return (
    <h1 className={`brand-mark ${className ?? ""}`.trim()}>
      <Wallet size={22} aria-hidden />
      商资通
    </h1>
  );
}
