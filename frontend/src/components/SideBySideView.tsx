import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Columns, AlertTriangle, AlertOctagon, CheckCircle2, ShieldAlert, Sparkles, Search, Clock, FileText } from 'lucide-react';
import type { DocumentSummary, ComparisonResponse } from '../types';
import { comparePipelines } from '../api';
import { EvidenceViewer } from './EvidenceViewer';
import { NoiseSimulationPlayground } from './NoiseSimulationPlayground';

interface SideBySideViewProps {
  documents: DocumentSummary[];
  selectedDocId: string | null;
  onSelectDocId: (docId: string | null) => void;
}

const COMPARISON_PROMPTS = [
  'What is the cost or penalty amount imposed by the High Court and where should it be deposited?',
  'Under what section and what is the timeline for filing a statutory appeal?',
  'What was the specific reason for rejecting the RTI application?',
  'What are the mandatory compliance directives issued in the government circular?',
];

export const SideBySideView: React.FC<SideBySideViewProps> = ({
  documents,
  selectedDocId,
  onSelectDocId,
}) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);

  const handleCompare = async (queryText?: string) => {
    const textToSearch = queryText || query;
    if (!textToSearch.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await comparePipelines(textToSearch, selectedDocId || undefined);
      setComparison(res);
    } catch (err: any) {
      setError(err.message || 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  const selectedDoc = documents.find((d) => d.document_id === selectedDocId);

  return (
    <div className="section-container">
      {/* Live Interactive Noise Simulation Playground */}
      <NoiseSimulationPlayground />

      {/* Section Header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Baseline RAG vs Confidence-Aware RAG Comparison</h2>
          <p className="section-desc">
            Direct side-by-side evaluation demonstrating how standard naive RAG suffers from silent hallucinations on noisy OCR scans, whereas Confidence-Aware RAG warns users and re-ranks quality chunks.
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
              <span>Comparing across All Documents</span>
            </div>
          )}
        </div>
      </div>

      {/* Query Bar */}
      <div className="query-box-card">
        <div className="query-input-row">
          <div className="query-input-wrapper">
            <Search className="query-input-icon" size={20} />
            <input
              type="text"
              className="query-input"
              placeholder="Ask a question to see dual execution comparison..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
            />
          </div>
          <motion.button
            className="btn-primary-gradient"
            disabled={loading || !query.trim()}
            onClick={() => handleCompare()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {loading ? (
              <span className="btn-loading-text">Comparing Pipelines...</span>
            ) : (
              <>
                <span>Compare Pipelines</span>
                <Columns size={16} />
              </>
            )}
          </motion.button>
        </div>

        <div className="sample-prompts-label">
          <Sparkles size={14} className="text-primary" />
          <span>Quick Comparative Tests:</span>
        </div>

        <div className="sample-prompts-list">
          {COMPARISON_PROMPTS.map((sample, idx) => (
            <motion.button
              key={idx}
              className="sample-prompt-chip"
              onClick={() => {
                setQuery(sample);
                handleCompare(sample);
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

      {/* Comparison Results */}
      <AnimatePresence>
        {comparison && (
          <motion.div
            className="comparison-results-wrapper"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Key Difference Banner */}
            <motion.div
              className="key-difference-banner"
              initial={{ scale: 0.96 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 350, damping: 25 }}
            >
              <div className="key-diff-icon-box">
                <Sparkles size={20} className="text-primary pulse-icon" />
              </div>
              <div className="key-diff-content">
                <span className="key-diff-label">System Synthesis & Viva Insight:</span>
                <p className="key-diff-text">{comparison.key_difference}</p>
              </div>
            </motion.div>

            {/* Two Column Grid */}
            <div className="comparison-grid">
              {/* Column 1: Baseline RAG */}
              <motion.div
                className="comparison-card baseline-card"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, delay: 0.1 }}
                whileHover={{ y: -3 }}
              >
                <div className="comparison-card-header">
                  <div className="comp-badge comp-badge-baseline">Baseline (Standard Naive RAG)</div>
                  <div className="comp-meta-row">
                    <span className="latency-tag">
                      <Clock size={12} /> {comparison.baseline.latency_ms.toFixed(0)} ms
                    </span>
                  </div>
                </div>

                <div className="card-behavior-summary">
                  <ShieldAlert size={16} className="text-danger flex-shrink-0" />
                  <span>Pure vector similarity search. No OCR confidence filtering or warning calibration.</span>
                </div>

                <div className="comparison-answer-body">
                  <h4 className="comp-subheading">Generated Response</h4>
                  <div className="answer-text">
                    <p>{comparison.baseline.answer}</p>
                  </div>
                </div>

                <div className="comparison-card-footer">
                  <div className="card-flag-box box-unaware">
                    <AlertOctagon size={16} className="text-danger flex-shrink-0" />
                    <div className="flag-info">
                      <span className="flag-title">Silent OCR Hallucination Risk</span>
                      <span className="flag-desc">
                        Cannot detect if numbers or dates were distorted by bad scanning.
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Column 2: Proposed Confidence-Aware RAG */}
              <motion.div
                className="comparison-card proposed-card"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, delay: 0.15 }}
                whileHover={{ y: -3 }}
              >
                <div className="comparison-card-header">
                  <div className="comp-badge comp-badge-proposed">Proposed (Confidence-Aware RAG)</div>
                  <div className="comp-meta-row">
                    <span className="latency-tag">
                      <Clock size={12} /> {comparison.confidence_aware.execution_time_ms.toFixed(0)} ms
                    </span>
                  </div>
                </div>

                <div className="card-behavior-summary">
                  <CheckCircle2 size={16} className="text-success flex-shrink-0" />
                  <span>Weighted reranking (0.5 Sim + 0.5 OCR), token-level risk assessment & hallucination guardrails.</span>
                </div>

                <div className="comparison-answer-body">
                  <h4 className="comp-subheading">Risk-Calibrated Response</h4>
                  <div className="answer-text">
                    <p>{comparison.confidence_aware.answer}</p>
                  </div>
                </div>

                <div className="comparison-card-footer">
                  {comparison.confidence_aware.risk_level === 'HIGH_RISK' ? (
                    <div className="card-flag-box box-high-risk">
                      <AlertOctagon size={16} className="text-danger flex-shrink-0" />
                      <div className="flag-info">
                        <span className="flag-title">High Risk Detected & Flagged</span>
                        <span className="flag-desc">
                          Warning injected into LLM prompt; user explicitly advised to check physical scan.
                        </span>
                      </div>
                    </div>
                  ) : comparison.confidence_aware.risk_level === 'MEDIUM_RISK' ? (
                    <div className="card-flag-box box-med-risk">
                      <AlertTriangle size={16} className="text-warning flex-shrink-0" />
                      <div className="flag-info">
                        <span className="flag-title">Moderate Risk Detected</span>
                        <span className="flag-desc">Certain tokens flagged with &lt;70% confidence.</span>
                      </div>
                    </div>
                  ) : (
                    <div className="card-flag-box box-clean">
                      <CheckCircle2 size={16} className="text-success flex-shrink-0" />
                      <div className="flag-info">
                        <span className="flag-title">High Reliability Confirmed</span>
                        <span className="flag-desc">All supporting evidence passes &gt;85% word confidence test.</span>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>

            {/* Deep Evidence Quality Inspection */}
            {comparison.confidence_aware.evidence_report && (
              <EvidenceViewer evidenceReport={comparison.confidence_aware.evidence_report} />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
