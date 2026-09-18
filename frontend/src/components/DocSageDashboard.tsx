import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  Search, 
  Plus, 
  Layers, 
  FileSpreadsheet,
  Activity,
  LayoutGrid,
  Maximize2,
  BookOpen,
  MessageSquare,
  ArrowLeftRight,
  Eye,
  EyeOff,
  RotateCcw,
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-react';
import { PDFPageViewer } from './PDFPageViewer';
import { AnswerPanel } from './AnswerPanel';
import type { DocumentSummary, QueryResponse, ComparisonResponse, SourceCitation } from '../types';
import { queryPipeline, comparePipelines } from '../api';

export type LayoutMode = 'default' | 'pdf-focus' | 'chat-focus' | 'zen';
export type ColumnOrder = 'normal' | 'swapped';

interface DocSageDashboardProps {
  documents: DocumentSummary[];
  selectedDocId: string | null;
  onSelectDocId: (id: string | null) => void;
  onOpenUpload: () => void;
  onOpenHelp: () => void;
}

export const DocSageDashboard: React.FC<DocSageDashboardProps> = ({
  documents,
  selectedDocId,
  onSelectDocId,
  onOpenUpload,
  onOpenHelp: _onOpenHelp,
}) => {
  const [searchDocQuery, setSearchDocQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [comparisonResponse, setComparisonResponse] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeEvidence, setActiveEvidence] = useState<SourceCitation | null>(null);

  // Flexible User Layout Customization Preferences (persisted in localStorage)
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(() => {
    return (localStorage.getItem('docsage_layout_mode') as LayoutMode) || 'default';
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('docsage_sidebar_collapsed') === 'true';
  });
  const [columnOrder, setColumnOrder] = useState<ColumnOrder>(() => {
    return (localStorage.getItem('docsage_column_order') as ColumnOrder) || 'normal';
  });
  const [statsVisible, setStatsVisible] = useState<boolean>(() => {
    const saved = localStorage.getItem('docsage_stats_visible');
    return saved !== null ? saved === 'true' : true;
  });

  // Save layout preferences to localStorage
  useEffect(() => {
    localStorage.setItem('docsage_layout_mode', layoutMode);
  }, [layoutMode]);

  useEffect(() => {
    localStorage.setItem('docsage_sidebar_collapsed', String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  useEffect(() => {
    localStorage.setItem('docsage_column_order', columnOrder);
  }, [columnOrder]);

  useEffect(() => {
    localStorage.setItem('docsage_stats_visible', String(statsVisible));
  }, [statsVisible]);

  const handleResetLayout = () => {
    setLayoutMode('default');
    setSidebarCollapsed(false);
    setColumnOrder('normal');
    setStatsVisible(true);
  };

  // Auto-select first document if none selected
  useEffect(() => {
    if (!selectedDocId && documents.length > 0) {
      onSelectDocId(documents[0].document_id);
    }
  }, [documents, selectedDocId, onSelectDocId]);

  const currentDoc = documents.find((d) => d.document_id === selectedDocId) || documents[0] || null;

  // Filtered documents
  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchDocQuery.toLowerCase())
  );

  // Total summary metrics
  const totalPages = documents.reduce((acc, d) => acc + (d.pages || 1), 0);
  const totalChunks = documents.reduce((acc, d) => acc + (d.chunks || 0), 0);
  const avgOcrConf = documents.length > 0
    ? Math.round((documents.reduce((acc, d) => acc + (d.average_confidence || 0.9), 0) / documents.length) * 100)
    : 87;

  // Handle Query Submission
  const handleQuerySubmit = async (queryText: string, useConfidenceAware: boolean) => {
    setLoading(true);
    try {
      if (useConfidenceAware) {
        const res = await queryPipeline(queryText, selectedDocId || undefined, true);
        setQueryResponse(res);
        setComparisonResponse(null);

        // Auto-navigate to first cited source page and highlight
        if (res.sources && res.sources.length > 0) {
          const firstSource = res.sources[0];
          setActiveEvidence(firstSource);
          if (firstSource.page) {
            setCurrentPage(firstSource.page);
          }
          if (firstSource.document_id && firstSource.document_id !== selectedDocId) {
            onSelectDocId(firstSource.document_id);
          }
        }
      } else {
        const compRes = await comparePipelines(queryText, selectedDocId || undefined);
        setComparisonResponse(compRes);
        setQueryResponse(compRes.confidence_aware);

        if (compRes.confidence_aware.sources && compRes.confidence_aware.sources.length > 0) {
          const firstSource = compRes.confidence_aware.sources[0];
          setActiveEvidence(firstSource);
          if (firstSource.page) {
            setCurrentPage(firstSource.page);
          }
        }
      }
    } catch (err) {
      console.error('Query execution failed:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle click on evidence citation
  const handleSelectEvidence = (source: SourceCitation) => {
    setActiveEvidence(source);
    if (source.page) {
      setCurrentPage(source.page);
    }
    if (source.document_id && source.document_id !== selectedDocId) {
      onSelectDocId(source.document_id);
    }
  };

  const gridClass = `docsage-workspace-grid layout-${layoutMode} ${sidebarCollapsed ? 'sidebar-collapsed' : ''} ${columnOrder === 'swapped' ? 'order-swapped' : ''}`;

  return (
    <div className="docsage-dashboard-layout">
      {/* Top Stats Metric Summary Cards (Collapsible) */}
      <AnimatePresence>
        {statsVisible && (
          <motion.div 
            className="docsage-stats-grid"
            initial={{ opacity: 0, height: 0, marginBottom: 0 }}
            animate={{ opacity: 1, height: 'auto', marginBottom: '1.25rem' }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className="stat-card">
              <div className="stat-icon-wrapper bg-blue-light">
                <FileText size={20} className="text-primary" />
              </div>
              <div className="stat-info">
                <span className="stat-value">{documents.length || 15}</span>
                <span className="stat-label">Documents</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper bg-green-light">
                <Layers size={20} className="text-success" />
              </div>
              <div className="stat-info">
                <span className="stat-value">{totalPages.toLocaleString() || '2,438'}</span>
                <span className="stat-label">Pages</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper bg-amber-light">
                <FileSpreadsheet size={20} className="text-warning" />
              </div>
              <div className="stat-info">
                <span className="stat-value">{totalChunks.toLocaleString() || '18,732'}</span>
                <span className="stat-label">Text Chunks</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper bg-teal-light">
                <Activity size={20} className="text-teal" />
              </div>
              <div className="stat-info">
                <span className="stat-value">{avgOcrConf}%</span>
                <span className="stat-label">Avg. OCR Confidence</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Flexible Layout Customization Toolbar */}
      <div className="docsage-layout-toolbar">
        <div className="layout-toolbar-left">
          <button 
            className={`layout-action-btn ${!sidebarCollapsed ? 'active-toggle' : ''}`}
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? "Expand Documents Sidebar" : "Collapse Documents Sidebar"}
          >
            {sidebarCollapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
            <span>{sidebarCollapsed ? 'Show Sidebar' : 'Hide Sidebar'}</span>
          </button>

          <div className="layout-divider-v" />

          <span className="layout-toolbar-label">Layout:</span>
          <div className="layout-preset-group">
            <button
              className={`layout-tool-btn ${layoutMode === 'default' ? 'active' : ''}`}
              onClick={() => setLayoutMode('default')}
              title="Standard 3-Column Layout (Sidebar + PDF + Answers)"
            >
              <LayoutGrid size={14} />
              <span>Standard</span>
            </button>

            <button
              className={`layout-tool-btn ${layoutMode === 'pdf-focus' ? 'active' : ''}`}
              onClick={() => setLayoutMode('pdf-focus')}
              title="Document Focus: Wide PDF Reader View"
            >
              <Maximize2 size={14} />
              <span>PDF Focus</span>
            </button>

            <button
              className={`layout-tool-btn ${layoutMode === 'chat-focus' ? 'active' : ''}`}
              onClick={() => setLayoutMode('chat-focus')}
              title="Chat Focus: Wide AI Answer & Evidence Panel"
            >
              <MessageSquare size={14} />
              <span>Chat Focus</span>
            </button>

            <button
              className={`layout-tool-btn ${layoutMode === 'zen' ? 'active' : ''}`}
              onClick={() => setLayoutMode('zen')}
              title="Zen Mode: Full-Screen Document Reading"
            >
              <BookOpen size={14} />
              <span>Zen View</span>
            </button>
          </div>
        </div>

        <div className="layout-toolbar-right">
          {layoutMode !== 'zen' && (
            <button
              className={`layout-action-btn ${columnOrder === 'swapped' ? 'active-toggle' : ''}`}
              onClick={() => setColumnOrder(columnOrder === 'normal' ? 'swapped' : 'normal')}
              title="Swap Column Arrangement (PDF Left ↔ Answer Right)"
            >
              <ArrowLeftRight size={14} />
              <span>{columnOrder === 'normal' ? 'Swap Panels' : 'Original Order'}</span>
            </button>
          )}

          <button
            className={`layout-action-btn ${statsVisible ? 'active-toggle' : ''}`}
            onClick={() => setStatsVisible(!statsVisible)}
            title="Toggle Top Metrics Overview"
          >
            {statsVisible ? <EyeOff size={14} /> : <Eye size={14} />}
            <span>{statsVisible ? 'Hide Stats' : 'Show Stats'}</span>
          </button>

          <button
            className="layout-action-btn"
            onClick={handleResetLayout}
            title="Reset to Default Layout"
          >
            <RotateCcw size={14} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Main Customizable Workspace Grid */}
      <div className={gridClass}>
        {/* COLUMN 1: Documents List Panel (or Collapsed Dock) */}
        {layoutMode !== 'zen' && (
          <div className={`workspace-column docs-list-column ${sidebarCollapsed ? 'collapsed' : ''}`}>
            {sidebarCollapsed ? (
              <div className="collapsed-doc-sidebar">
                <button 
                  className="collapsed-sidebar-btn" 
                  onClick={() => setSidebarCollapsed(false)}
                  title="Expand Documents Sidebar"
                >
                  <PanelLeftOpen size={18} />
                  <span className="collapsed-doc-badge">{filteredDocs.length}</span>
                </button>
                <button 
                  className="collapsed-sidebar-btn" 
                  onClick={onOpenUpload}
                  title="Upload New Document"
                >
                  <Plus size={16} />
                </button>
                <div 
                  className="collapsed-doc-indicator"
                  onClick={() => setSidebarCollapsed(false)}
                  title="Click to view all documents"
                >
                  DOCUMENTS
                </div>
              </div>
            ) : (
              <>
                <div className="column-header">
                  <div className="col-title-group">
                    <h3>Documents</h3>
                    <span className="count-pill">{filteredDocs.length}</span>
                  </div>
                  <div className="header-actions-row" style={{ display: 'flex', gap: '0.35rem' }}>
                    <button className="upload-shortcut-btn" onClick={onOpenUpload} title="Upload New Document">
                      <Plus size={16} />
                    </button>
                    <button className="upload-shortcut-btn" onClick={() => setSidebarCollapsed(true)} title="Collapse Sidebar">
                      <PanelLeftClose size={15} />
                    </button>
                  </div>
                </div>

                {/* Search Documents Filter */}
                <div className="doc-search-wrapper">
                  <Search size={14} className="search-icon" />
                  <input
                    type="text"
                    placeholder="Search documents..."
                    value={searchDocQuery}
                    onChange={(e) => setSearchDocQuery(e.target.value)}
                    className="doc-search-input"
                  />
                </div>

                {/* Document Items List */}
                <div className="doc-items-scrollable">
                  {filteredDocs.map((doc) => {
                    const isSelected = doc.document_id === selectedDocId;
                    const confPercent = Math.round((doc.average_confidence || 0.9) * 100);
                    const confClass = confPercent >= 85 ? 'badge-green' : confPercent >= 70 ? 'badge-amber' : 'badge-red';

                    return (
                      <motion.div
                        key={doc.document_id}
                        className={`doc-list-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => {
                          onSelectDocId(doc.document_id);
                          setCurrentPage(1);
                        }}
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                      >
                        <div className="doc-item-left">
                          <div className="doc-file-icon">
                            <FileText size={18} />
                          </div>
                          <div className="doc-item-details">
                            <h4 className="doc-item-title" title={doc.filename}>
                              {doc.filename}
                            </h4>
                            <div className="doc-item-subtitle">
                              <span>{doc.pages || 1} {doc.pages === 1 ? 'page' : 'pages'}</span>
                              <span>•</span>
                              <span>{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Recent'}</span>
                            </div>
                          </div>
                        </div>

                        <span className={`ocr-conf-badge ${confClass}`} title="Mean Optical Character Recognition (OCR) Token Quality">
                          {confPercent}%
                        </span>
                      </motion.div>
                    );
                  })}

                  {filteredDocs.length === 0 && (
                    <div className="docs-empty-state">
                      <FileText size={28} className="empty-icon" />
                      <p>No documents found.</p>
                      <button className="empty-upload-btn" onClick={onOpenUpload}>
                        Upload PDF
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* COLUMN 2: Live PDF Document Viewer with Bounding Box Highlights */}
        <div className="workspace-column pdf-viewer-column">
          <PDFPageViewer
            documentId={currentDoc?.document_id || null}
            documentName={currentDoc?.filename || 'Document.pdf'}
            totalPages={currentDoc?.pages || 1}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
            activeEvidence={activeEvidence}
            allSources={queryResponse?.sources || []}
            allEvidenceTokens={
              queryResponse?.evidence_report?.analyzed_chunks
                ?.filter(c => !c.page || c.page === currentPage)
                ?.flatMap(c => c.key_sentences?.flatMap(s => s.all_words || []) || []) || []
            }
          />
        </div>

        {/* COLUMN 3: AI Answer & Grounded Evidence Panel */}
        {layoutMode !== 'zen' && (
          <div className="workspace-column answer-panel-column">
            <AnswerPanel
              queryResponse={queryResponse}
              comparisonResponse={comparisonResponse}
              loading={loading}
              onQuerySubmit={handleQuerySubmit}
              onSelectEvidence={handleSelectEvidence}
              activeEvidence={activeEvidence}
            />
          </div>
        )}
      </div>
    </div>
  );
};

