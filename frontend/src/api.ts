import type { DocumentSummary, DocumentIngestResponse, QueryResponse, ComparisonResponse, BenchmarkReport } from './types';

const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<{ status: string; app: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed with status ${res.status}`);
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents list');
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentIngestResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete document ${docId}`);
}

export async function queryPipeline(
  query: string,
  docId?: string,
  useConfidenceReranking = true
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      document_id: docId || null,
      use_confidence_reranking: useConfidenceReranking,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Query failed with status ${res.status}`);
  }

  return res.json();
}

export async function comparePipelines(query: string, docId?: string): Promise<ComparisonResponse> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      document_id: docId || null,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Comparison failed with status ${res.status}`);
  }

  return res.json();
}

export function getPageImageUrl(docId: string, pageNumber: number, scale = 2.0): string {
  return `${API_BASE}/documents/${docId}/pages/${pageNumber}/image?scale=${scale}`;
}

export async function fetchBenchmarkReport(): Promise<BenchmarkReport | null> {
  try {
    const res = await fetch('/evaluation_results.json');
    if (res.ok) {
      return res.json();
    }
  } catch {
    // fallback
  }
  return null;
}
