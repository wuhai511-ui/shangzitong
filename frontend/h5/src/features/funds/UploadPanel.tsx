import { useState } from "react";
import { previewUpload, useConfirmUploadMutation } from "../../api/queries";
import type { UploadPreview } from "../../api/types";

export function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const confirm = useConfirmUploadMutation();

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setError(null);
    try {
      const result = await previewUpload(selected);
      setPreview(result);
    } catch {
      setError("文件解析失败，请检查格式");
      setPreview(null);
    }
  }

  function handleConfirm() {
    if (!preview) return;
    confirm.mutate({
      preview_id: preview.preview_id,
      mappings: preview.mappings,
      provider: "upload",
    });
  }

  return (
    <section className="card panel">
      <h3>结算文件导入</h3>
      <label htmlFor="upload-file" className="upload-label">
        选择结算文件
      </label>
      <input
        id="upload-file"
        type="file"
        accept=".csv,.xlsx"
        onChange={handleFile}
      />

      {file && (
        <div className="upload-meta">
          <span>{file.name}</span>
          <span>{(file.size / 1024).toFixed(1)} KB</span>
        </div>
      )}

      {error && <span className="form-error">{error}</span>}

      {preview && (
        <div className="upload-preview">
          <div>共 {preview.total_rows} 行</div>
          {preview.preview_rows.length > 0 && (
            <table className="preview-table">
              <thead>
                <tr>
                  {Object.keys(preview.preview_rows[0]).map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview_rows.map((row, idx) => (
                  <tr key={idx}>
                    {Object.values(row).map((val, i) => (
                      <td key={i}>{String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <button type="button" onClick={handleConfirm} disabled={confirm.isPending}>
            {confirm.isPending ? "导入中" : "确认导入"}
          </button>
          {confirm.data && <div>已导入 {confirm.data.imported} 条</div>}
        </div>
      )}
    </section>
  );
}
