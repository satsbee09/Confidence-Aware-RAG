export type RiskLevel = 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  avatarText: string;
  isLoggedIn: boolean;
  institution?: string;
  groqApiKey?: string;
  openaiApiKey?: string;
}

export interface DocumentSummary {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
  average_confidence: number;
  min_confidence: number;
  file_size_bytes: number;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface DocumentIngestResponse {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
  average_confidence: number;
  min_confidence: number;
  status: string;
  message: string;
}

export interface SourceCitation {
  page: number;
  confidence: number;
  flagged: boolean;
  chunk_id?: string;
  document_id?: string;
  document_name?: string;
  evidence_text?: string;
  risk?: string;
  tokens?: EvidenceWord[];
  page_width?: number;
  page_height?: number;
}

export interface EvidenceWord {
  text: string;
  confidence: number;
  flagged?: boolean;
  is_low_confidence?: boolean;
  page: number;
  bbox?: number[]; // [x0, y0, x1, y1]
  line_number?: number;
}

export interface EvidenceSentence {
  sentence_text?: string;
  text?: string;
  sentence_confidence?: number;
  confidence?: number;
  similarity_to_query?: number;
  flagged: boolean;
  low_confidence_words: EvidenceWord[];
  all_words?: EvidenceWord[];
}

export interface AnalyzedEvidenceChunk {
  chunk_id: string;
  chunk_text: string;
  page: number;
  chunk_confidence: number;
  min_word_confidence: number;
  flagged: boolean;
  similarity?: number;
  final_score?: number;
  key_sentences: EvidenceSentence[];
}

export interface EvidenceQualityReport {
  overall_confidence: number;
  overall_risk_level: RiskLevel;
  total_chunks_analyzed?: number;
  flagged_count: number;
  analyzed_chunks: AnalyzedEvidenceChunk[];
  summary?: string;
  warning_message?: string | null;
}

export interface QueryResponse {
  query: string;
  answer: string;
  confidence_score: number;
  semantic_similarity?: number;
  ocr_confidence?: number;
  risk_level: RiskLevel;
  sources: SourceCitation[];
  overall_warning: string | null;
  evidence_report?: EvidenceQualityReport;
  mode: 'confidence_aware' | 'baseline';
  execution_time_ms: number;
}

export interface BaselineAnswer {
  answer: string;
  sources: number[];
  warning: null;
  top_chunk_similarity?: number;
  similarity_score?: number;
  latency_ms: number;
}

export interface ComparisonResponse {
  query: string;
  baseline: BaselineAnswer;
  confidence_aware: QueryResponse;
  key_difference: string;
}

export interface BenchmarkTierData {
  noise_tier: string;
  total_queries: number;
  baseline: {
    mean_accuracy: number;
    warning_detection_rate: number;
    mean_evidence_confidence: number;
    mean_latency_ms: number;
    unchecked_hallucination_rate: number;
  };
  proposed: {
    mean_accuracy: number;
    warning_detection_rate: number;
    mean_evidence_confidence: number;
    mean_latency_ms: number;
    unchecked_hallucination_rate: number;
  };
}

export interface BenchmarkReport {
  benchmark_timestamp: string;
  system_configuration: {
    embedding_model: string;
    similarity_weight: number;
    confidence_weight: number;
    low_confidence_threshold: number;
    llm_provider: string;
  };
  tiers: Record<string, BenchmarkTierData>;
}
