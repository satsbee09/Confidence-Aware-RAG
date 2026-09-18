import React, { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, FileSearch, Sparkles } from 'lucide-react';
import type { EvidenceQualityReport, AnalyzedEvidenceChunk } from '../types';

interface EvidenceViewerProps {
  evidenceReport?: EvidenceQualityReport;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evidenceReport }) => {
  const [expandedChunkId, setExpandedChunkId] = useState<string | null>(null);

  if (!evidenceReport || evidenceReport.analyzed_chunks.length === 0) {
    return null;
  }

  const toggleChunk = (chunkId: string) => {
    setExpandedChunkId(expandedChunkId === chunkId ? null : chunkId);
  };

  const renderHighlightedSentence = (text: string, lowConfWords: { text: string; confidence: number }[]) => {
    if (!lowConfWords || lowConfWords.length === 0) {
      return <span>{text}</span>;
    }

    // Split text into tokens and highlight matches
    const flaggedWordsMap = new Map<string, number>();
    lowConfWords.forEach((w) => flaggedWordsMap.set(w.text.toLowerCase().trim(), w.confidence));

    const words = text.split(/(\s+)/);
    return (
      <span>
        {words.map((w, idx) => {
          const cleanWord = w.replace(/[^\w]/g, '').toLowerCase();
          if (cleanWord && flaggedWordsMap.has(cleanWord)) {
            const conf = flaggedWordsMap.get(cleanWord)!;
            return (
              <mark
                key={idx}
                className="token-highlight-bad"
                title={`OCR Confidence: ${(conf * 100).toFixed(0)}% (Uncertain token)`}
              >
                {w}
                <span className="token-conf-tag">{(conf * 100).toFixed(0)}%</span>
              </mark>
            );
          }
          return <span key={idx}>{w}</span>;
        })}
      </span>
    );
  };

  return (
    <div className="evidence-viewer-card">
      <div className="evidence-viewer-header">
        <div className="evidence-header-left">
          <FileSearch size={20} className="evidence-icon" />
          <div>
            <h4 className="evidence-title">Retrieved Evidence & Token Reliability Inspection</h4>
            <p className="evidence-subtitle">
              Chunks ranked by blended score: <code className="formula-code">0.5 × Similarity + 0.5 × OCR Confidence</code>
            </p>
          </div>
        </div>

        <div className="evidence-header-right">
          <div className="evidence-stat">
            <span className="stat-label">Analyzed Chunks</span>
            <span className="stat-value">{evidenceReport.analyzed_chunks.length}</span>
          </div>
          <div className="evidence-stat">
            <span className="stat-label">Flagged Chunks</span>
            <span className={`stat-value ${evidenceReport.flagged_count > 0 ? 'text-warning' : 'text-success'}`}>
              {evidenceReport.flagged_count}
            </span>
          </div>
          <div className="evidence-stat">
            <span className="stat-label">Overall Evidence Quality</span>
            <span className="stat-value">{(evidenceReport.overall_confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {(evidenceReport.warning_message || evidenceReport.summary) && (
        <div className="evidence-summary-banner">
          <Sparkles size={16} className="text-primary" />
          <span>{evidenceReport.warning_message || evidenceReport.summary}</span>
        </div>
      )}

      {/* Chunk Accordions */}
      <div className="chunks-accordion-list">
        {evidenceReport.analyzed_chunks.map((chunk: AnalyzedEvidenceChunk, index: number) => {
          const isExpanded = expandedChunkId === chunk.chunk_id || index === 0;
          const similarityPct = ((chunk.similarity ?? 0.85) * 100).toFixed(1);
          const ocrPct = (chunk.chunk_confidence * 100).toFixed(1);
          const finalScorePct = ((chunk.final_score ?? (0.5 * (chunk.similarity ?? 0.85) + 0.5 * chunk.chunk_confidence)) * 100).toFixed(1);

          return (
            <div
              key={chunk.chunk_id || index}
              className={`chunk-item ${chunk.flagged ? 'chunk-item-flagged' : 'chunk-item-clean'}`}
            >
              <div className="chunk-header" onClick={() => toggleChunk(chunk.chunk_id)}>
                <div className="chunk-header-main">
                  <div className="chunk-rank-badge">Rank #{index + 1}</div>
                  <span className="chunk-page-badge">Page {chunk.page}</span>

                  {chunk.flagged ? (
                    <span className="chunk-status-flagged">
                      <AlertTriangle size={13} /> Flagged (Low OCR Conf)
                    </span>
                  ) : (
                    <span className="chunk-status-clean">
                      <CheckCircle2 size={13} /> High Reliability
                    </span>
                  )}
                </div>

                <div className="chunk-scores-row">
                  <div className="score-badge" title="Vector Cosine Similarity">
                    <span className="score-lbl">Sim:</span>
                    <span className="score-num">{similarityPct}%</span>
                  </div>
                  <div className="score-badge" title="Mean OCR Confidence of words in chunk">
                    <span className="score-lbl">OCR:</span>
                    <span className="score-num">{ocrPct}%</span>
                  </div>
                  <div className="score-badge score-badge-primary" title="Blended Ranking Score">
                    <span className="score-lbl">Score:</span>
                    <span className="score-num">{finalScorePct}%</span>
                  </div>
                  <button className="btn-toggle-icon">
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="chunk-content-body">
                  <div className="sentence-analysis-header">
                    <span>Sentence-Level Evidence Breakdown & Token Inspection</span>
                    <span className="min-word-conf-tag">
                      Min Token Confidence: {(chunk.min_word_confidence * 100).toFixed(1)}%
                    </span>
                  </div>

                  {chunk.key_sentences && chunk.key_sentences.length > 0 ? (
                    <div className="sentences-list">
                      {chunk.key_sentences.map((sent, sIdx) => {
                        const sText = sent.sentence_text || sent.text || '';
                        const sConf = ((sent.sentence_confidence ?? sent.confidence ?? 0) * 100).toFixed(1);
                        return (
                          <div
                            key={sIdx}
                            className={`sentence-row ${sent.flagged ? 'sentence-flagged' : 'sentence-clean'}`}
                          >
                            <div className="sentence-text">
                              {renderHighlightedSentence(sText, sent.low_confidence_words)}
                            </div>
                            <div className="sentence-conf-meta">
                              {sConf}% conf
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="raw-chunk-text">
                      <p>{chunk.chunk_text}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
