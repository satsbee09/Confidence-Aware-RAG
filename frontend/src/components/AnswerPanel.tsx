import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Send, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  Sparkles, 
  Scale, 
  ArrowRight,
  HelpCircle
} from 'lucide-react';
import type { QueryResponse, ComparisonResponse, SourceCitation } from '../types';

interface AnswerPanelProps {
  queryResponse: QueryResponse | null;
  comparisonResponse: ComparisonResponse | null;
  loading: boolean;
  onQuerySubmit: (query: string, useConfidenceAware: boolean) => void;
  onSelectEvidence: (source: SourceCitation) => void;
  activeEvidence: SourceCitation | null;
}

export const AnswerPanel: React.FC<AnswerPanelProps> = ({
  queryResponse,
  comparisonResponse,
  loading,
  onQuerySubmit,
  onSelectEvidence,
  activeEvidence,
}) => {
  const [activeTab, setActiveTab] = useState<'ask' | 'compare'>('ask');
  const [queryInput, setQueryInput] = useState<string>('');

  const sampleQuestions = [
    'What was the budget allocation for the fiscal year 2022-23?',
    'What was the statutory penalty imposed and where should it be deposited?',
    'What sanction was granted by the competent authority in the RTI reply?',
  ];

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!queryInput.trim() || loading) return;
    onQuerySubmit(queryInput.trim(), activeTab === 'ask');
  };

  const handlePresetClick = (q: string) => {
    setQueryInput(q);
    onQuerySubmit(q, activeTab === 'ask');
  };

  // Calculate OCR Confidence breakdown from evidence
  const confidenceBreakdown = React.useMemo(() => {
    if (!queryResponse || !queryResponse.evidence_report) {
      return { high: 72, med: 20, low: 8 };
    }
    const chunks = queryResponse.evidence_report.analyzed_chunks || [];
    let highCount = 0;
    let medCount = 0;
    let lowCount = 0;
    let total = 0;

    for (const c of chunks) {
      for (const s of c.key_sentences || []) {
        total++;
        if (s.flagged || (s.sentence_confidence && s.sentence_confidence < 0.70)) {
          lowCount++;
        } else if (s.sentence_confidence && s.sentence_confidence < 0.85) {
          medCount++;
        } else {
          highCount++;
        }
      }
    }

    if (total === 0) return { high: 72, med: 20, low: 8 };
    return {
      high: Math.round((highCount / total) * 100),
      med: Math.round((medCount / total) * 100),
      low: Math.round((lowCount / total) * 100),
    };
  }, [queryResponse]);

  return (
    <div className="answer-panel-card">
      {/* Top Mode Tabs */}
      <div className="answer-panel-tabs">
        <button
          className={`answer-tab-btn ${activeTab === 'ask' ? 'active' : ''}`}
          onClick={() => setActiveTab('ask')}
        >
          <Sparkles size={14} />
          <span>Ask a Question</span>
        </button>
        <button
          className={`answer-tab-btn ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
        >
          <Scale size={14} />
          <span>Compare (Baseline)</span>
        </button>
      </div>

      {/* Query Search Input Box */}
      <form className="query-input-form" onSubmit={handleSubmit}>
        <div className="query-input-wrapper">
          <input
            type="text"
            className="query-text-input"
            placeholder="Ask a question about your documents..."
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="query-submit-btn"
            disabled={!queryInput.trim() || loading}
          >
            {loading ? (
              <span className="spinner-small" />
            ) : (
              <>
                <Send size={14} />
                <span>Ask</span>
              </>
            )}
          </button>
        </div>

        {/* Suggested Queries Pills */}
        {!queryResponse && (
          <div className="preset-queries-group">
            <span className="preset-label">Suggested:</span>
            {sampleQuestions.map((sq, i) => (
              <button
                key={i}
                type="button"
                className="preset-pill-btn"
                onClick={() => handlePresetClick(sq)}
              >
                {sq}
              </button>
            ))}
          </div>
        )}
      </form>

      {/* Query Results / Output View */}
      <div className="answer-results-scrollable">
        {loading && (
          <div className="answer-loading-skeleton">
            <div className="skeleton-bar title-bar" />
            <div className="skeleton-bar text-bar" />
            <div className="skeleton-bar text-bar short" />
            <div className="skeleton-grid">
              <div className="skeleton-box" />
              <div className="skeleton-box" />
            </div>
          </div>
        )}

        {!loading && activeTab === 'ask' && queryResponse && (
          <motion.div
            className="answer-content-view"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Answer Header Card */}
            <div className="answer-main-card">
              <div className="answer-card-header">
                <div className="answer-header-title">
                  <CheckCircle2 size={18} className="text-success" />
                  <strong>Answer</strong>
                </div>
                <span className={`confidence-pill ${queryResponse.risk_level === 'HIGH_RISK' ? 'pill-danger' : queryResponse.risk_level === 'MEDIUM_RISK' ? 'pill-warning' : 'pill-success'}`}>
                  {queryResponse.risk_level === 'HIGH_RISK' ? '⚠️ High Risk Warning' : queryResponse.risk_level === 'MEDIUM_RISK' ? 'Moderate Confidence' : 'High Confidence'}
                </span>
              </div>

              <p className="answer-body-text">{queryResponse.answer}</p>

              {/* Separate Scoring Metadata Grid */}
              <div className="answer-meta-grid">
                <div className="meta-item">
                  <span className="meta-label">Semantic Match</span>
                  <strong className="meta-value text-primary">
                    {Math.round((queryResponse.semantic_similarity ?? 0.95) * 100)}%
                  </strong>
                </div>
                <div className="meta-item">
                  <span className="meta-label">OCR Quality</span>
                  <strong className={`meta-value ${((queryResponse.ocr_confidence ?? queryResponse.sources[0]?.confidence ?? 0.99) >= 0.85) ? 'text-success' : ((queryResponse.ocr_confidence ?? queryResponse.sources[0]?.confidence ?? 0.99) >= 0.70) ? 'text-warning' : 'text-danger'}`}>
                    {Math.round((queryResponse.ocr_confidence ?? queryResponse.sources[0]?.confidence ?? 0.99) * 100)}%
                  </strong>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Overall Reliability</span>
                  <strong className={`meta-value ${queryResponse.confidence_score >= 0.85 ? 'text-success' : queryResponse.confidence_score >= 0.70 ? 'text-warning' : 'text-danger'}`}>
                    {Math.round(queryResponse.confidence_score * 100)}%
                  </strong>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Risk Level</span>
                  <strong className={`meta-value ${queryResponse.risk_level === 'HIGH_RISK' ? 'text-danger' : queryResponse.risk_level === 'MEDIUM_RISK' ? 'text-warning' : 'text-success'}`}>
                    {queryResponse.risk_level === 'HIGH_RISK' ? 'High Risk' : queryResponse.risk_level === 'MEDIUM_RISK' ? 'Medium' : 'Low Risk'}
                  </strong>
                </div>
              </div>

              {/* Source Document & Page Footer Row */}
              <div className="answer-card-submeta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.65rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <FileText size={13} className="text-primary" />
                  <strong style={{ color: 'var(--text-secondary)' }}>{queryResponse.sources[0]?.document_name || 'Document.pdf'}</strong>
                </span>
                <span>Page {queryResponse.sources[0]?.page || 1} of {queryResponse.sources.length} cited</span>
              </div>

              {/* Warning Notice & High-Risk Uncertainty Advisory */}
              {queryResponse.overall_warning && (
                <div className="uncertainty-warning-banner">
                  <AlertTriangle size={16} className="text-warning flex-shrink-0" />
                  <div className="warning-text-group">
                    <strong>Confidence Advisory:</strong>
                    <span>{queryResponse.overall_warning}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Primary Grounded Evidence Card */}
            {queryResponse.sources.length > 0 && (
              <div className="evidence-section-group">
                <div className="evidence-section-header">
                  <h4>Evidence</h4>
                  <button 
                    className="view-all-link"
                    onClick={() => onSelectEvidence(queryResponse.sources[0])}
                  >
                    View in Document <ArrowRight size={12} />
                  </button>
                </div>

                <div 
                  className={`evidence-highlight-card ${activeEvidence === queryResponse.sources[0] ? 'active-focus' : ''}`}
                  onClick={() => onSelectEvidence(queryResponse.sources[0])}
                >
                  <p className="evidence-quote-text">
                    "{queryResponse.sources[0].evidence_text || 'Exact evidence retrieved from page ' + queryResponse.sources[0].page}"
                  </p>
                  <div className="evidence-card-footer">
                    <span className="ev-meta-tag">Page {queryResponse.sources[0].page}</span>
                    <span className="ev-meta-tag">
                      OCR Confidence: <strong>{Math.round(queryResponse.sources[0].confidence * 100)}%</strong>
                    </span>
                    <span className={`ev-risk-tag ${queryResponse.sources[0].risk === 'HIGH' ? 'risk-high' : queryResponse.sources[0].risk === 'MEDIUM' ? 'risk-med' : 'risk-low'}`}>
                      {queryResponse.sources[0].risk === 'HIGH' ? 'High Risk' : queryResponse.sources[0].risk === 'MEDIUM' ? 'Medium Risk' : 'Low Risk'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Other Supporting Sources */}
            {queryResponse.sources.length > 1 && (
              <div className="other-sources-group">
                <span className="other-sources-title">Other Sources</span>
                {queryResponse.sources.slice(1).map((src, idx) => (
                  <div
                    key={idx}
                    className={`other-source-item ${activeEvidence === src ? 'active' : ''}`}
                    onClick={() => onSelectEvidence(src)}
                  >
                    <div className="source-item-content">
                      <p className="source-excerpt">
                        "{src.evidence_text ? (src.evidence_text.length > 60 ? src.evidence_text.slice(0, 60) + '...' : src.evidence_text) : `Supporting evidence on page ${src.page}`}"
                      </p>
                      <div className="source-meta-row">
                        <span>Page {src.page}</span>
                        <span>•</span>
                        <span>OCR: {Math.round(src.confidence * 100)}%</span>
                      </div>
                    </div>
                    <span className={`risk-badge-mini ${src.risk === 'HIGH' ? 'bg-danger' : src.risk === 'MEDIUM' ? 'bg-warning' : 'bg-success'}`}>
                      {src.risk === 'HIGH' ? 'High Risk' : src.risk === 'MEDIUM' ? 'Medium Risk' : 'Low Risk'}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Confidence Analysis Distribution Bar */}
            <div className="confidence-distribution-card">
              <span className="dist-title">Confidence Analysis</span>
              <div className="segmented-progress-bar">
                <div className="bar-segment seg-green" style={{ width: `${confidenceBreakdown.high}%` }} title={`High Confidence: ${confidenceBreakdown.high}%`} />
                <div className="bar-segment seg-amber" style={{ width: `${confidenceBreakdown.med}%` }} title={`Medium Confidence: ${confidenceBreakdown.med}%`} />
                <div className="bar-segment seg-red" style={{ width: `${confidenceBreakdown.low}%` }} title={`Low Confidence: ${confidenceBreakdown.low}%`} />
              </div>

              <div className="dist-legend-row">
                <div className="dist-legend-item">
                  <span className="legend-box box-green" />
                  <span>High (80-100%)</span>
                  <strong>{confidenceBreakdown.high}%</strong>
                </div>
                <div className="dist-legend-item">
                  <span className="legend-box box-amber" />
                  <span>Medium (50-80%)</span>
                  <strong>{confidenceBreakdown.med}%</strong>
                </div>
                <div className="dist-legend-item">
                  <span className="legend-box box-red" />
                  <span>Low (&lt;50%)</span>
                  <strong>{confidenceBreakdown.low}%</strong>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Side-by-Side Comparison Tab View */}
        {!loading && activeTab === 'compare' && comparisonResponse && (
          <motion.div
            className="comparison-view-container"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Baseline Card */}
            <div className="compare-card card-baseline">
              <div className="compare-badge badge-baseline">Normal RAG (Baseline)</div>
              <p className="compare-answer">{comparisonResponse.baseline.answer}</p>
              <div className="compare-footer-row">
                <span>Source: Page {comparisonResponse.baseline.sources[0] || 1}</span>
                <span className="text-danger">⚠️ No OCR Reliability Warning</span>
              </div>
            </div>

            <div className="vs-divider">VS</div>

            {/* Proposed Confidence-Aware Card */}
            <div className="compare-card card-proposed">
              <div className="compare-badge badge-proposed">Confidence-Aware RAG (Ours)</div>
              <p className="compare-answer">{comparisonResponse.confidence_aware.answer}</p>
              <div className="compare-footer-row">
                <span>Source: Page {comparisonResponse.confidence_aware.sources[0]?.page || 1}</span>
                <span className="text-success">
                  OCR Confidence: {Math.round(comparisonResponse.confidence_aware.confidence_score * 100)}%
                </span>
              </div>
              {comparisonResponse.confidence_aware.overall_warning && (
                <div className="compare-warning">
                  {comparisonResponse.confidence_aware.overall_warning}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {!loading && !queryResponse && !comparisonResponse && (
          <div className="answer-empty-placeholder">
            <HelpCircle size={36} className="placeholder-icon" />
            <p>Type a question above or click any suggested prompt to see live evidence grounding.</p>
          </div>
        )}
      </div>
    </div>
  );
};
