import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Search, AlertTriangle, CheckCircle, ShieldAlert, ChevronRight, RefreshCw, MessageSquare } from 'lucide-react';
import type { QueryHistoryItem } from '../types';
import { fetchQueryHistory } from '../api';

interface QueryHistoryPanelProps {
  onSelectQuery: (item: QueryHistoryItem) => void;
  refreshTrigger?: number;
}

export const QueryHistoryPanel: React.FC<QueryHistoryPanelProps> = ({ onSelectQuery, refreshTrigger }) => {
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const loadHistory = async () => {
    setLoading(true);
    const data = await fetchQueryHistory(30);
    setHistory(data);
    setLoading(false);
  };

  useEffect(() => {
    loadHistory();
  }, [refreshTrigger]);

  const filtered = history.filter(
    (h) => h.query.toLowerCase().includes(filter.toLowerCase())
  );

  const riskIcon = (risk: string) => {
    if (risk === 'LOW_RISK') return <CheckCircle size={13} className="text-success" />;
    if (risk === 'MEDIUM_RISK') return <AlertTriangle size={13} className="text-warning" />;
    return <ShieldAlert size={13} className="text-danger" />;
  };

  const riskClass = (risk: string) => {
    if (risk === 'LOW_RISK') return 'qh-risk-low';
    if (risk === 'MEDIUM_RISK') return 'qh-risk-med';
    return 'qh-risk-high';
  };

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return 'Just now';
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h ago`;
      return d.toLocaleDateString();
    } catch {
      return '';
    }
  };

  return (
    <div className="qh-panel">
      <div className="qh-header">
        <div className="qh-title-row">
          <Clock size={16} />
          <h3>Query History</h3>
          <span className="qh-count">{history.length}</span>
        </div>
        <button className="qh-refresh-btn" onClick={loadHistory} title="Refresh">
          <RefreshCw size={14} className={loading ? 'qh-spin' : ''} />
        </button>
      </div>

      <div className="qh-search">
        <Search size={13} className="qh-search-icon" />
        <input
          type="text"
          placeholder="Filter queries..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="qh-search-input"
        />
      </div>

      <div className="qh-list">
        <AnimatePresence>
          {loading && history.length === 0 ? (
            <div className="qh-empty">
              <RefreshCw size={20} className="qh-spin" />
              <span>Loading history...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="qh-empty">
              <MessageSquare size={22} />
              <span>{filter ? 'No matching queries' : 'No queries yet'}</span>
              <p>Ask a question on the dashboard to see it here.</p>
            </div>
          ) : (
            filtered.map((item, i) => (
              <motion.button
                key={item.query_id}
                className={`qh-item ${selectedId === item.query_id ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedId(item.query_id);
                  onSelectQuery(item);
                }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <div className="qh-item-top">
                  <span className={`qh-risk-dot ${riskClass(item.risk_level)}`}>
                    {riskIcon(item.risk_level)}
                  </span>
                  <span className="qh-item-query">{item.query}</span>
                  <ChevronRight size={13} className="qh-chevron" />
                </div>
                <div className="qh-item-meta">
                  <span className="qh-meta-conf">{Math.round(item.confidence_score * 100)}%</span>
                  <span className="qh-meta-sep" />
                  <span>{item.source_count} sources</span>
                  <span className="qh-meta-sep" />
                  <span>{Math.round(item.execution_time_ms)}ms</span>
                  <span className="qh-meta-time">{formatTime(item.created_at)}</span>
                </div>
              </motion.button>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
