import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Download, 
  FileText, 
  AlertTriangle, 
  RefreshCw
} from 'lucide-react';
import type { EvidenceWord, SourceCitation } from '../types';
import { getPageImageUrl } from '../api';

interface PDFPageViewerProps {
  documentId: string | null;
  documentName?: string;
  totalPages?: number;
  currentPage: number;
  onPageChange: (newPage: number) => void;
  activeEvidence?: SourceCitation | null;
  allSources?: SourceCitation[];
  allEvidenceTokens?: EvidenceWord[];
}

export const PDFPageViewer: React.FC<PDFPageViewerProps> = ({
  documentId,
  documentName = 'Document.pdf',
  totalPages = 1,
  currentPage,
  onPageChange,
  activeEvidence,
  allSources = [],
  allEvidenceTokens = [],
}) => {
  const [zoom, setZoom] = useState<number>(100);
  const [imageLoaded, setImageLoaded] = useState<boolean>(false);
  const [imageError, setImageError] = useState<boolean>(false);
  const [hoveredToken, setHoveredToken] = useState<EvidenceWord | null>(null);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number }>({ width: 595, height: 842 });
  
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const effectiveTotalPages = Math.max(1, totalPages || 1);

  // Reset zoom on document change
  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [documentId, currentPage]);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDimensions({
      width: img.naturalWidth || 595,
      height: img.naturalHeight || 842,
    });
    setImageLoaded(true);
    setImageError(false);
  };

  const handleImageError = () => {
    setImageLoaded(false);
    setImageError(true);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < effectiveTotalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handleZoomIn = () => setZoom((z) => Math.min(200, z + 15));
  const handleZoomOut = () => setZoom((z) => Math.max(60, z - 15));
  const handleFitScreen = () => setZoom(100);

  // Set of token keys belonging specifically to the active selected evidence citation
  const activeTokenKeySet = React.useMemo<Set<string>>(() => {
    const set = new Set<string>();
    if (activeEvidence && activeEvidence.page === currentPage && activeEvidence.tokens) {
      for (const t of activeEvidence.tokens) {
        if (t.bbox && t.bbox.length === 4) {
          set.add(`${t.text}_${Math.round(t.bbox[0])}_${Math.round(t.bbox[1])}`);
        }
      }
    }
    return set;
  }, [activeEvidence, currentPage]);

  // Aggregate all evidence tokens on the current page across all sources & evidence chunks
  const pageTokens = React.useMemo<EvidenceWord[]>(() => {
    const tokens: EvidenceWord[] = [];
    const seen = new Set<string>();

    const addToken = (t: EvidenceWord) => {
      if (!t.bbox || t.bbox.length !== 4) return;
      const key = `${t.text}_${Math.round(t.bbox[0])}_${Math.round(t.bbox[1])}`;
      if (!seen.has(key)) {
        seen.add(key);
        tokens.push(t);
      }
    };

    // 1. From allSources citations matching currentPage & documentId
    if (allSources && allSources.length > 0) {
      for (const src of allSources) {
        const matchesDoc = !src.document_id || !documentId || src.document_id === documentId;
        if (matchesDoc && src.page === currentPage && src.tokens && src.tokens.length > 0) {
          for (const t of src.tokens) {
            addToken(t);
          }
        }
      }
    }

    // 2. From activeEvidence if on currentPage
    if (activeEvidence && activeEvidence.page === currentPage && activeEvidence.tokens) {
      const matchesDoc = !activeEvidence.document_id || !documentId || activeEvidence.document_id === documentId;
      if (matchesDoc) {
        for (const t of activeEvidence.tokens) {
          addToken(t);
        }
      }
    }

    // 3. From allEvidenceTokens if provided
    if (allEvidenceTokens && allEvidenceTokens.length > 0) {
      for (const t of allEvidenceTokens) {
        addToken(t);
      }
    }

    return tokens;
  }, [allSources, activeEvidence, allEvidenceTokens, currentPage, documentId]);

  // Group active evidence tokens into contiguous, clean highlight lines
  interface HighlightLine {
    id: string;
    bbox: [number, number, number, number];
    text: string;
    tokens: EvidenceWord[];
    avgConfidence: number;
    hasLowConf: boolean;
    isActive: boolean;
  }

  const highlightLines = React.useMemo<HighlightLine[]>(() => {
    if (!pageTokens || pageTokens.length === 0) return [];

    const validTokens = pageTokens.filter(t => t.bbox && t.bbox.length === 4);
    if (validTokens.length === 0) return [];

    // Sort tokens in reading order (top-to-bottom, left-to-right)
    const sorted = [...validTokens].sort((a, b) => {
      const yDiff = a.bbox![1] - b.bbox![1];
      if (Math.abs(yDiff) > 4.5) return yDiff;
      return a.bbox![0] - b.bbox![0];
    });

    const lines: HighlightLine[] = [];
    let currentLineTokens: EvidenceWord[] = [];

    const flushLine = (toks: EvidenceWord[]) => {
      if (toks.length === 0) return;
      const x0 = Math.min(...toks.map(t => t.bbox![0]));
      const y0 = Math.min(...toks.map(t => t.bbox![1]));
      const x1 = Math.max(...toks.map(t => t.bbox![2]));
      const y1 = Math.max(...toks.map(t => t.bbox![3]));
      const avgConf = toks.reduce((s, t) => s + t.confidence, 0) / toks.length;
      const hasLow = toks.some(t => t.is_low_confidence || t.confidence < 0.70);
      const isLineActive = toks.some(t => {
        if (!t.bbox || t.bbox.length !== 4) return false;
        const key = `${t.text}_${Math.round(t.bbox[0])}_${Math.round(t.bbox[1])}`;
        return activeTokenKeySet.has(key);
      });

      lines.push({
        id: `line_${lines.length}_${x0}_${y0}`,
        bbox: [x0, y0, x1, y1],
        text: toks.map(t => t.text).join(' '),
        tokens: toks,
        avgConfidence: avgConf,
        hasLowConf: hasLow,
        isActive: isLineActive,
      });
    };

    for (const token of sorted) {
      if (currentLineTokens.length === 0) {
        currentLineTokens.push(token);
      } else {
        const lastToken = currentLineTokens[currentLineTokens.length - 1];
        const lastY = lastToken.bbox![1];
        const currY = token.bbox![1];
        if (Math.abs(currY - lastY) <= 4.5) {
          currentLineTokens.push(token);
        } else {
          flushLine(currentLineTokens);
          currentLineTokens = [token];
        }
      }
    }

    if (currentLineTokens.length > 0) {
      flushLine(currentLineTokens);
    }

    return lines;
  }, [pageTokens, activeTokenKeySet]);

  // Compute reference coordinate system dimensions for 100% accurate alignment
  const { coordWidth, coordHeight } = React.useMemo(() => {
    let w = activeEvidence?.page === currentPage ? activeEvidence?.page_width : undefined;
    let h = activeEvidence?.page === currentPage ? activeEvidence?.page_height : undefined;

    if (!w || !h) {
      const pageSrc = allSources?.find(s => s.page === currentPage && s.page_width && s.page_height);
      if (pageSrc) {
        w = pageSrc.page_width;
        h = pageSrc.page_height;
      }
    }

    const maxTokenX = pageTokens.reduce((max, t) => Math.max(max, t.bbox?.[2] || 0), 0);
    const maxTokenY = pageTokens.reduce((max, t) => Math.max(max, t.bbox?.[3] || 0), 0);

    if (!w || !h || w <= 0 || h <= 0) {
      if (maxTokenX > 0 && maxTokenX <= 650 && maxTokenY <= 900 && imageDimensions.width > 900) {
        w = imageDimensions.width / 2.0;
        h = imageDimensions.height / 2.0;
      } else {
        w = imageDimensions.width || 595;
        h = imageDimensions.height || 842;
      }
    } else {
      if (maxTokenX > w && maxTokenX <= imageDimensions.width) {
        w = imageDimensions.width;
        h = imageDimensions.height;
      }
    }
    return { coordWidth: w || 595, coordHeight: h || 842 };
  }, [activeEvidence, allSources, currentPage, pageTokens, imageDimensions]);

  if (!documentId) {
    return (
      <div className="pdf-viewer-empty-state">
        <FileText size={48} className="empty-icon" />
        <h3>No Document Selected</h3>
        <p>Select a document from the left list or ask a question to view live evidence highlights.</p>
      </div>
    );
  }

  const imageUrl = getPageImageUrl(documentId, currentPage);

  return (
    <div className="pdf-page-viewer-card" ref={containerRef}>
      {/* Top Header Controls Toolbar */}
      <div className="pdf-viewer-toolbar">
        <div className="pdf-viewer-title-group">
          <FileText size={16} className="text-primary" />
          <span className="pdf-viewer-filename" title={documentName}>
            {documentName}
          </span>
        </div>

        {/* Page Navigator */}
        <div className="pdf-viewer-pager">
          <button
            className="pager-btn"
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            title="Previous Page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="pager-text">
            <strong>{currentPage}</strong> / {effectiveTotalPages}
          </span>
          <button
            className="pager-btn"
            onClick={handleNextPage}
            disabled={currentPage >= effectiveTotalPages}
            title="Next Page"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Zoom & Action Controls */}
        <div className="pdf-viewer-actions">
          <button className="zoom-btn" onClick={handleZoomOut} disabled={zoom <= 60} title="Zoom Out">
            <ZoomOut size={14} />
          </button>
          <span className="zoom-level">{zoom}%</span>
          <button className="zoom-btn" onClick={handleZoomIn} disabled={zoom >= 200} title="Zoom In">
            <ZoomIn size={14} />
          </button>
          <div className="toolbar-divider" />
          <button className="action-icon-btn" onClick={handleFitScreen} title="Fit to Screen">
            <Maximize2 size={14} />
          </button>
          <a
            href={imageUrl}
            target="_blank"
            rel="noreferrer"
            download={`${documentName}_p${currentPage}.png`}
            className="action-icon-btn"
            title="Download Page Image"
          >
            <Download size={14} />
          </a>
        </div>
      </div>

      {/* Main Canvas / Image Area */}
      <div className="pdf-canvas-container">
        <div
          className="pdf-page-wrapper"
          style={{
            transform: `scale(${zoom / 100})`,
            transformOrigin: 'top center',
            transition: 'transform 0.2s cubic-bezier(0.2, 0, 0, 1)',
          }}
        >
          {/* Loading Skeleton */}
          {!imageLoaded && !imageError && (
            <div className="pdf-page-skeleton">
              <RefreshCw size={28} className="animate-spin text-primary" />
              <span>Rendering high-resolution scan...</span>
            </div>
          )}

          {/* Error State */}
          {imageError && (
            <div className="pdf-page-error">
              <AlertTriangle size={32} className="text-warning" />
              <h4>Page Image Unavailable</h4>
              <p>Could not render page {currentPage} of {documentName}.</p>
            </div>
          )}

          {/* Rendered Document Page Image */}
          <img
            ref={imageRef}
            src={imageUrl}
            alt={`Page ${currentPage} of ${documentName}`}
            className={`pdf-page-image ${imageLoaded ? 'loaded' : 'hidden'}`}
            onLoad={handleImageLoad}
            onError={handleImageError}
          />

          {/* Dynamic Evidence Bounding Box Highlights (Line-level marker overlay) */}
          {imageLoaded && highlightLines.length > 0 && (
            <div className="bounding-box-overlay-layer">
              {highlightLines.map((line, idx) => {
                const [x0, y0, x1, y1] = line.bbox;
                
                // Scale coordinates as exact percentages of original page space
                const leftPercent = (x0 / coordWidth) * 100;
                const topPercent = (y0 / coordHeight) * 100;
                const widthPercent = Math.max(1.0, ((x1 - x0) / coordWidth) * 100);
                const heightPercent = Math.max(1.2, ((y1 - y0) / coordHeight) * 100);

                const isLow = line.hasLowConf || line.avgConfidence < 0.70;
                const isMed = line.avgConfidence >= 0.70 && line.avgConfidence < 0.85;
                const confColorClass = isLow ? 'highlight-red' : isMed ? 'highlight-amber' : 'highlight-green';

                const activeFocusClass = line.isActive ? 'active-evidence-focus' : '';

                return (
                  <motion.div
                    key={line.id}
                    className={`evidence-highlight-line ${confColorClass} ${activeFocusClass}`}
                    style={{
                      left: `${leftPercent}%`,
                      top: `${topPercent}%`,
                      width: `${widthPercent}%`,
                      height: `${heightPercent}%`,
                    }}
                    initial={{ scaleX: 0.96, opacity: 0 }}
                    animate={{ scaleX: 1, opacity: 1 }}
                    transition={{ duration: 0.25, delay: idx * 0.02 }}
                    onMouseEnter={() => setHoveredToken(line.tokens[0] || null)}
                    onMouseLeave={() => setHoveredToken(null)}
                  >
                    {/* Visual highlighter bar */}
                    <span className="line-highlight-bar" />
                  </motion.div>
                );
              })}
            </div>
          )}

          {/* Hover Token Tooltip Card */}
          <AnimatePresence>
            {hoveredToken && (
              <motion.div
                className="token-inspect-tooltip"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
              >
                <div className="tooltip-row">
                  <span className="tooltip-label">OCR Evidence:</span>
                  <strong className="tooltip-val">"{hoveredToken.text}"</strong>
                </div>
                <div className="tooltip-row">
                  <span className="tooltip-label">OCR Confidence:</span>
                  <span className={`tooltip-badge ${hoveredToken.confidence >= 0.85 ? 'badge-green' : hoveredToken.confidence >= 0.70 ? 'badge-amber' : 'badge-red'}`}>
                    {(hoveredToken.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="tooltip-row">
                  <span className="tooltip-label">Coordinates:</span>
                  <code className="tooltip-coords">
                    [{hoveredToken.bbox?.map(c => Math.round(c)).join(', ')}]
                  </code>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="pdf-viewer-footer">
        <div className="footer-status-left">
          <span className="status-indicator live-pulse" />
          <span className="status-text">
            {pageTokens.length > 0
              ? `${pageTokens.length} active supporting OCR tokens highlighted on Page ${currentPage}`
              : `Page ${currentPage} of ${effectiveTotalPages}`}
          </span>
        </div>
        <div className="footer-legend">
          <span className="legend-item">
            <span className="legend-dot dot-green" /> High (≥85%)
          </span>
          <span className="legend-item">
            <span className="legend-dot dot-amber" /> Med (70-84%)
          </span>
          <span className="legend-item">
            <span className="legend-dot dot-red" /> Low / Risk (&lt;70%)
          </span>
        </div>
      </div>
    </div>
  );
};
