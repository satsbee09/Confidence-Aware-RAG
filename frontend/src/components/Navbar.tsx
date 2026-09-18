import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Activity, Sun, Moon, FileText, Search, Columns, BarChart3 } from 'lucide-react';

interface NavbarProps {
  activeTab: 'documents' | 'query' | 'compare' | 'benchmark';
  setActiveTab: (tab: 'documents' | 'query' | 'compare' | 'benchmark') => void;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  backendOnline: boolean;
}

const TABS = [
  { id: 'documents' as const, label: 'Documents & Ingestion', icon: FileText },
  { id: 'query' as const, label: 'Confidence Query', icon: Search },
  { id: 'compare' as const, label: 'Side-by-Side Comparison', icon: Columns },
  { id: 'benchmark' as const, label: 'Evaluation Benchmark', icon: BarChart3 },
];

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  theme,
  toggleTheme,
  backendOnline,
}) => {
  return (
    <header className="navbar-container">
      <div className="navbar-inner">
        {/* Brand */}
        <motion.div
          className="navbar-brand"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <motion.div
            className="brand-icon-wrapper"
            whileHover={{ scale: 1.1, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            <ShieldCheck className="brand-icon" size={24} />
          </motion.div>
          <div>
            <div className="brand-title">
              Confidence-Aware <span className="brand-accent">RAG</span>
            </div>
            <div className="brand-subtitle">Indian Legal & Government Document Intelligence</div>
          </div>
        </motion.div>

        {/* Navigation Tabs with Animated Slider */}
        <nav className="nav-tabs">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                className={`nav-tab-btn ${isActive ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
                {isActive && (
                  <motion.div
                    className="active-tab-indicator"
                    layoutId="activeTabIndicator"
                    transition={{ type: 'spring', stiffness: 450, damping: 35 }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Actions & Status */}
        <motion.div
          className="navbar-actions"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className={`status-badge ${backendOnline ? 'status-online' : 'status-offline'}`}>
            <Activity size={14} className={backendOnline ? 'pulse-icon' : ''} />
            <span>{backendOnline ? 'Backend Online' : 'Connecting...'}</span>
          </div>

          <motion.button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
            whileHover={{ scale: 1.1, rotate: 180 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </motion.button>
        </motion.div>
      </div>
    </header>
  );
};
