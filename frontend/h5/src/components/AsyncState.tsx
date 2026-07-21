import { AlertTriangle, Loader2, Inbox } from "lucide-react";

export function LoadingState({ label = "加载中" }: { label?: string }) {
  return (
    <div className="state-panel" role="status" aria-live="polite">
      <Loader2 size={24} aria-hidden className="spin" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ label = "暂无数据" }: { label?: string }) {
  return (
    <div className="state-panel">
      <Inbox size={24} aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({
  label = "加载失败，请重试",
  onRetry,
}: {
  label?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="state-panel state-error">
      <AlertTriangle size={24} aria-hidden />
      <span>{label}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="retry-button">
          重试
        </button>
      )}
    </div>
  );
}
