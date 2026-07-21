import { AvailableCashForm } from "./AvailableCashForm";
import { CardsPanel } from "./CardsPanel";
import { ManualSettlementPanel } from "./ManualSettlementPanel";
import { UploadPanel } from "./UploadPanel";

export function FundsPage() {
  return (
    <div className="page">
      <h2>资金</h2>
      <AvailableCashForm />
      <CardsPanel />
      <ManualSettlementPanel />
      <UploadPanel />

      <section className="card panel connector-card" aria-disabled="true">
        <h3 aria-disabled="true">邮件接入</h3>
        <span className="badge">正在开发中</span>
      </section>

      <section className="card panel connector-card" aria-disabled="true">
        <h3 aria-disabled="true">SFTP 接入</h3>
        <span className="badge">正在开发中</span>
      </section>
    </div>
  );
}
