import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Send, Sparkles, AlertTriangle, AlertOctagon, CheckCircle2, Copy, Check, Sliders, FileText, Cpu, Database, Eye, UploadCloud } from 'lucide-react';
import type { DocumentSummary, QueryResponse } from '../types';
import { queryPipeline } from '../api';
import { EvidenceViewer } from './EvidenceViewer';
import { InteractivePipelineVisualizer } from './InteractivePipelineVisualizer';

interface QuerySectionProps {
  documents: DocumentSummary[];
  selectedDocId: string | null;
  onSelectDocId: (docId: string | null) => void;
}

const SAMPLE_QUERIES = [
  'What is the cost or penalty amount imposed by the High Court and where should it be deposited?',
  'Under what section and what is the timeline for filing a statutory appeal?',
  'What was the specific reason for rejecting the RTI application?',
  'What are the mandatory compliance directives issued in the government circular?',
];

const EXECUTION_STEPS = [
  { icon: Cpu, label: 'Encoding query vector with all-MiniLM-L6-v2 (384-d)...' },
  { icon: Database, label: 'Scanning vector index & computing cosine similarities...' },
  { icon: Sliders, label: 'Executing Confidence Reranker: 0.5 Sim + 0.5 OCR...' },
  { icon: Eye, label: 'Inspecting evidence tokens & assembling risk-calibrated prompt...' },
];

export const QuerySection: React.FC<QuerySectionProps> = ({
  documents,
  selectedDocId,
  onSelectDocId,
}) => {
  const [query, setQuery] = useState('');
  const [useConfidenceReranking, setUseConfidenceReranking] = useState(true);
  const [loading, setLoading] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Animate through execution steps during query execution
  useEffect(() => {
    let timer: any;
    if (loading) {
      setCurrentStepIndex(0);
      timer = setInterval(() => {
        setCurrentStepIndex((prev) => (prev < EXECUTION_STEPS.length - 1 ? prev + 1 : prev));
      }, 350);
    }
    return () => clearInterval(timer);
  }, [loading]);

  const handleSearch = async (queryText?: string) => {
    const textToSearch = queryText || query;
    if (!textToSearch.trim()) return;

    if (documents.length === 0) {
      setError('Please upload and ingest a document first in the "Documents & Ingestion" tab before querying.');
      return;
    }

    setLoading(true);
    setError(null);
    setCopied(false);

    try {
      const res = await queryPipeline(textToSearch, selectedDocId || undefined, useConfidenceReranking);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute query');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (result?.answer) {
      navigator.clipboard.writeText(result.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const selectedDoc = documents.find((d) => d.document_id === selectedDocId);

  const getRiskBanner = (riskLevel: string, overallWarning: string | null) => {
    if (riskLevel === 'HIGH_RISK') {
      return (
        <motion.div
          className="risk-banner risk-banner-high"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <AlertOctagon size={22} className="risk-icon pulse-icon" />
          <div className="risk-banner-text">
            <span className="risk-banner-title">High Risk of OCR Hallucination Detected</span>
            <p className="risk-banner-desc">
              {overallWarning ||
                'Key statutory numbers, dates, or party names originate from low-confidence OCR scans (<50% reliability). Verify with the original document.'}
            </p>
          </div>
        </motion.div>
      );
    } else if (riskLevel === 'MEDIUM_RISK') {
      return (
        <motion.div
          className="risk-banner risk-banner-medium"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <AlertTriangle size={22} className="risk-icon" />
          <div className="risk-banner-text">
            <span className="risk-banner-title">Moderate Risk / Partial Low-Confidence Tokens</span>
            <p className="risk-banner-desc">
              {overallWarning ||
                'Certain sentences contain degraded text. Exercise caution with critical numbers and verify before legal filing.'}
            </p>
          </div>
        </motion.div>
      );
    } else {
      return (
        <motion.div
          className="risk-banner risk-banner-low"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <CheckCircle2 size={22} className="risk-icon" />
          <div className="risk-banner-text">
            <span className="risk-banner-title">High Reliability Grounded Answer</span>
            <p className="risk-banner-desc">
              Extracted evidence exhibits clean OCR quality with high word-level confidence (&gt;85%).
            </p>
          </div>
        </motion.div>
      );
    }
  };

  return (
    <div className="section-container">
      {/* Interactive Visualizer at top */}
      <InteractivePipelineVisualizer />

      {/* Header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Confidence-Aware RAG Query</h2>
          <p className="section-desc">
            Retrieve semantically relevant chunks weighted by token-level OCR confidence and generate risk-calibrated answers.
          </p>
        </div>

        <div className="query-scope-indicator">
          {selectedDoc ? (
            <div className="scope-pill-active">
              <FileText size={14} />
              <span>Scoped to: <strong>{selectedDoc.filename}</strong></span>
              <button className="scope-clear-btn" onClick={() => onSelectDocId(null)}>×</button>
            </div>
          ) : (
            <div className="scope-pill-global">
              <span>Searching Across All Ingested Documents ({documents.length})</span>
            </div>
          )}
        </div>
      </div>

      {/* Warning if 0 documents ingested */}
      {documents.length === 0 && (
        <div className="alert-box alert-warning">
          <UploadCloud size={20} className="text-warning" />
          <span>
            <strong>No documents ingested yet:</strong> Please upload a court order, RTI reply, or gazette PDF in the <strong>Documents & Ingestion</strong> tab first before executing queries.
          </span>
        </div>
      )}

      {/* Query Bar */}
      <div className="query-box-card">
        <div className="query-input-row">
          <div className="query-input-wrapper">
            <Search className="query-input-icon" size={20} />
            <input
              type="text"
              className="query-input"
              placeholder={
                documents.length === 0
                  ? 'Upload a document first to enable search...'
                  : 'Ask any legal or administrative question from the ingested documents...'
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <motion.button
            className="btn-primary-gradient"
            disabled={loading || !query.trim()}
            onClick={() => handleSearch()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {loading ? (
              <span className="btn-loading-text">Executing Pipeline...</span>
            ) : (
              <>
                <span>Ask RAG</span>
                <Send size={16} />
              </>
            )}
          </motion.button>
        </div>

        {/* Live Step Progress Stepper during Query */}
        {loading && (
          <motion.div
            className="query-execution-stepper"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <div className="stepper-track">
              {EXECUTION_STEPS.map((step, idx) => {
                const Icon = step.icon;
                const isCurrent = idx === currentStepIndex;
                const isDone = idx < currentStepIndex;
                return (
                  <div
                    key={idx}
                    className={`step-indicator-item ${isCurrent ? 'step-active' : isDone ? 'step-done' : 'step-pending'}`}
                  >
                    <div className="step-icon-bubble">
                      <Icon size={14} className={isCurrent ? 'pulse-icon' : ''} />
                    </div>
                    <span className="step-text">{step.label}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Query Controls & Sample Prompts */}
        <div className="query-controls-row">
          <div className="toggle-control-item">
            <Sliders size={16} className="text-secondary" />
            <span className="toggle-label">Confidence Reranker:</span>
            <button
              className={`toggle-switch-btn ${useConfidenceReranking ? 'active' : ''}`}
              onClick={() => setUseConfidenceReranking(!useConfidenceReranking)}
              title="When enabled, chunks are ranked by both cosine similarity and OCR token quality"
            >
              <div className="toggle-switch-handle" />
            </button>
            <span className="toggle-status-text">
              {useConfidenceReranking ? 'Enabled (0.5 Sim + 0.5 OCR)' : 'Disabled (Pure Similarity)'}
            </span>
          </div>

          <div className="sample-prompts-label">
            <Sparkles size={14} className="text-primary" />
            <span>Sample Questions:</span>
          </div>
        </div>

        <div className="sample-prompts-list">
          {SAMPLE_QUERIES.map((sample, idx) => (
            <motion.button
              key={idx}
              className="sample-prompt-chip"
              onClick={() => {
                setQuery(sample);
                handleSearch(sample);
              }}
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              {sample}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="alert-box alert-error">
          <AlertOctagon size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Result Section */}
      <AnimatePresence>
        {result && (
          <motion.div
            className="query-result-card"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
          >
            {/* Risk Level Banner */}
            {getRiskBanner(result.risk_level, result.overall_warning)}

            {/* Answer Card */}
            <div className="answer-box">
              <div className="answer-header">
                <div className="answer-title-group">
                  <h3 className="answer-heading">Grounded Answer</h3>
                  <span className="execution-time-tag">{result.execution_time_ms.toFixed(0)} ms</span>
                </div>
                <motion.button
                  className="btn-copy"
                  onClick={handleCopy}
                  title="Copy Answer"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </motion.button>
              </div>

              <div className="answer-text">
                <p>{result.answer}</p>
              </div>

              {/* Sources Citations */}
              <div className="sources-citation-row">
                <span className="sources-label">Sources & Citations:</span>
                <div className="sources-pills">
                  {result.sources.map((src, i) => (
                    <motion.span
                      key={i}
                      className={`source-pill ${src.flagged ? 'source-pill-flagged' : 'source-pill-clean'}`}
                      whileHover={{ scale: 1.05 }}
                    >
                      Page {src.page} • {(src.confidence * 100).toFixed(0)}% conf
                      {src.flagged && <AlertTriangle size={12} className="source-flag-icon" />}
                    </motion.span>
                  ))}
                </div>
              </div>
            </div>

            {/* Evidence Inspector */}
            {result.evidence_report && (
              <EvidenceViewer evidenceReport={result.evidence_report} />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
