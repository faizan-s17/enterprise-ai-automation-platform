import { useRef, useState } from "react";
import { roleAtLeast, useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { ApiError } from "../lib/api";
import { useApi } from "../lib/useApi";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorNote,
  PageHeader,
  Select,
  Spinner,
  TextInput,
} from "../components/ui";

const DOC_TYPES = ["", "invoice", "contract", "purchase_order", "receipt", "report", "other"];
const DOC_STATUSES = ["", "uploaded", "processing", "analyzed", "failed"];

export default function Documents() {
  const { token, user } = useAuth();
  const [search, setSearch] = useState("");
  const [docType, setDocType] = useState("");
  const [status, setStatus] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const canUpload = roleAtLeast(user?.role, "analyst");

  const docs = useApi(
    () =>
      api.listDocuments(token!, {
        search: search || undefined,
        doc_type: docType || undefined,
        status: status || undefined,
      }),
    [token, search, docType, status]
  );

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocument(token!, file);
      docs.reload();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleReanalyse(id: number) {
    try {
      await api.reanalyseDocument(token!, id);
      docs.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Re-analysis failed.");
    }
  }

  return (
    <div>
      <PageHeader
        title="Document intelligence"
        subtitle="Upload invoices, contracts, and purchase orders for AI extraction and analysis."
      />

      {canUpload ? (
        <Card className="mb-6">
          <div className="flex items-center gap-3">
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.docx,.txt,.md,.csv"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
              disabled={uploading}
              className="text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-accent file:px-3.5 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-accent-dark"
            />
            {uploading && <Spinner label="Extracting and analysing..." />}
          </div>
          {uploadError && <div className="mt-3"><ErrorNote message={uploadError} /></div>}
          <p className="mt-2 text-xs text-muted">PDF, DOCX, TXT, MD, or CSV.</p>
        </Card>
      ) : (
        <Card className="mb-6 text-sm text-muted">
          Viewers can read documents but not upload them. Ask an analyst, manager,
          or admin to upload.
        </Card>
      )}

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <TextInput
          placeholder="Search filename or summary"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select value={docType} onChange={(e) => setDocType(e.target.value)}>
          {DOC_TYPES.map((t) => (
            <option key={t} value={t}>
              {t ? t.replace("_", " ") : "All types"}
            </option>
          ))}
        </Select>
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          {DOC_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s || "All statuses"}
            </option>
          ))}
        </Select>
      </div>

      {docs.loading && <Spinner label="Loading documents..." />}
      {docs.error && <ErrorNote message={docs.error} />}
      {docs.data && docs.data.length === 0 && (
        <EmptyState message="No documents match. Upload one above to get started." />
      )}

      <div className="space-y-3">
        {docs.data?.map((d) => {
          const fields = Object.entries(d.ai_fields).filter(([k]) => k !== "analysed_by");
          return (
            <Card key={d.id}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-ink">{d.filename}</div>
                  <div className="text-xs text-muted">
                    {d.created_at.slice(0, 10)} &middot; {(d.size_bytes / 1024).toFixed(0)} KB
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Badge value={d.doc_type} />
                  <Badge value={d.status} />
                </div>
              </div>

              {d.ai_summary && (
                <p className="mt-3 whitespace-pre-line text-sm text-slate-700">
                  {d.ai_summary}
                </p>
              )}
              {d.error && <div className="mt-3"><ErrorNote message={d.error} /></div>}

              {fields.length > 0 && (
                <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 rounded-lg bg-band p-3 text-xs sm:grid-cols-3">
                  {fields.map(([k, v]) => (
                    <div key={k}>
                      <span className="text-muted">{k.replace(/_/g, " ")}: </span>
                      <span className="font-medium text-ink">
                        {Array.isArray(v) ? v.join(", ") : String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {canUpload && (
                <div className="mt-3">
                  <Button variant="secondary" onClick={() => handleReanalyse(d.id)}>
                    Re-analyse
                  </Button>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
