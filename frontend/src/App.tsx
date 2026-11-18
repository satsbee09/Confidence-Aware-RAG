import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from './components/Sidebar';
import type { NavTabType } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { BackgroundGlow } from './components/BackgroundGlow';
import { DocSageDashboard } from './components/DocSageDashboard';
import { DocumentUploadCard } from './components/DocumentUploadCard';
import { QuerySection } from './components/QuerySection';
import { SideBySideView } from './components/SideBySideView';
import { BenchmarkDashboard } from './components/BenchmarkDashboard';
import { HelpGuideModal } from './components/HelpGuideModal';
import { AuthProfileModal, DEMO_USERS } from './components/AuthProfileModal';
import type { DocumentSummary, UserProfile } from './types';
import { fetchDocuments, fetchHealth } from './api';
import { Settings as SettingsIcon, Cpu, Gauge, ShieldAlert, Server } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTabType>('dashboard');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);
  const [isProfileOpen, setIsProfileOpen] = useState<boolean>(false);

  // User Profile state (persisted to localStorage)
  const [currentUser, setCurrentUser] = useState<UserProfile>(() => {
    const saved = localStorage.getItem('docsage_user_profile');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Fallback to default
      }
    }
    return DEMO_USERS[0];
  });

  const handleUpdateUser = (updated: UserProfile) => {
    setCurrentUser(updated);
    localStorage.setItem('docsage_user_profile', JSON.stringify(updated));
  };

  const handleLogin = (user: UserProfile) => {
    setCurrentUser(user);
    localStorage.setItem('docsage_user_profile', JSON.stringify(user));
  };

  const handleLogout = () => {
    const guestUser: UserProfile = {
      id: 'guest',
      name: 'Guest User',
      email: 'guest@docsage.io',
      role: 'Visitor',
      avatarText: 'GU',
      isLoggedIn: false,
    };
    setCurrentUser(guestUser);
    localStorage.setItem('docsage_user_profile', JSON.stringify(guestUser));
  };

  // Sync theme with html root attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const loadDocuments = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      if (selectedDocId && !docs.some((d) => d.document_id === selectedDocId)) {
        setSelectedDocId(docs[0]?.document_id || null);
      } else if (!selectedDocId && docs.length > 0) {
        setSelectedDocId(docs[0].document_id);
      }
    } catch (err) {
      console.warn('Could not load documents list', err);
    }
  };

  const checkHealth = async () => {
    try {
      await fetchHealth();
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  };

  useEffect(() => {
    checkHealth();
    loadDocuments();
    const interval = setInterval(() => {
      checkHealth();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleGlobalSearch = (_q: string) => {
    setActiveTab('dashboard');
  };

  return (
    <div className="docsage-app-container">
      {/* Background glow & subtle canvas grid */}
      <BackgroundGlow />

      {/* Left Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        theme={theme}
        toggleTheme={toggleTheme}
        onOpenHelp={() => setIsHelpOpen(true)}
        currentUser={currentUser}
        onOpenProfile={() => setIsProfileOpen(true)}
      />

      {/* Main App Content Body */}
      <div className="docsage-main-wrapper">
        {/* Top Search & Actions Header */}
        <TopHeader
          theme={theme}
          toggleTheme={toggleTheme}
          backendOnline={backendOnline}
          onGlobalSearch={handleGlobalSearch}
          onOpenHelp={() => setIsHelpOpen(true)}
          currentUser={currentUser}
          onOpenProfile={() => setIsProfileOpen(true)}
        />

        {/* Tab Router Content Views */}
        <main className="docsage-viewport-content">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' && (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="viewport-tab-page"
              >
                <DocSageDashboard
                  documents={documents}
                  selectedDocId={selectedDocId}
                  onSelectDocId={setSelectedDocId}
                  onOpenUpload={() => setActiveTab('upload')}
                  onOpenHelp={() => setIsHelpOpen(true)}
                />
              </motion.div>
            )}

            {(activeTab === 'upload' || activeTab === 'documents') && (
              <motion.div
                key="upload-docs"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="viewport-tab-page"
              >
                <DocumentUploadCard
                  documents={documents}
                  selectedDocId={selectedDocId}
                  onSelectDocId={setSelectedDocId}
                  onRefresh={loadDocuments}
                />
              </motion.div>
            )}

            {activeTab === 'query' && (
              <motion.div
                key="query"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="viewport-tab-page"
              >
                <QuerySection
                  documents={documents}
                  selectedDocId={selectedDocId}
                  onSelectDocId={setSelectedDocId}
                />
              </motion.div>
            )}

            {activeTab === 'compare' && (
              <motion.div
                key="compare"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="viewport-tab-page"
              >
                <SideBySideView
                  documents={documents}
                  selectedDocId={selectedDocId}
                  onSelectDocId={setSelectedDocId}
                />
              </motion.div>
            )}

            {activeTab === 'evaluation' && (
              <motion.div
                key="evaluation"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="viewport-tab-page"
              >
                <BenchmarkDashboard />
              </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div
                key="settings"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="viewport-tab-page"
                style={{ maxWidth: 860 }}
              >
                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
                    <SettingsIcon size={24} className="text-primary" />
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 600, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em' }}>System Configuration</h2>
                  </div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Runtime settings, model configuration, and API connection details.
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '1rem' }}>
                  <div className="setting-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.65rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <Server size={18} className="text-primary" />
                      <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>Backend Connection</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>FastAPI Status</span>
                      <span className={`backend-status-pill ${backendOnline ? 'online' : 'offline'}`} style={{ fontSize: '0.72rem' }}>
                        <span className="status-pulse-dot" style={{ width: 6, height: 6 }} />
                        {backendOnline ? 'Online & Healthy' : 'Offline'}
                      </span>
                    </div>
                  </div>

                  <div className="setting-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.65rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <Cpu size={18} className="text-primary" />
                      <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>Embedding Model</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Model</span>
                      <strong style={{ fontSize: '0.82rem' }}>all-MiniLM-L6-v2</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Vector Dimensions</span>
                      <span className="badge badge-primary">384-d dense</span>
                    </div>
                  </div>

                  <div className="setting-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.65rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <Gauge size={18} className="text-primary" />
                      <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>Confidence Reranking</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Weights</span>
                      <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-color)', background: 'rgba(255,255,255,0.06)', padding: '0.15rem 0.45rem', borderRadius: 4 }}>
                        0.5×Sim + 0.5×OCR
                      </code>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Strategy</span>
                      <strong style={{ fontSize: '0.82rem' }}>Hybrid Cosine + OCR</strong>
                    </div>
                  </div>

                  <div className="setting-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.65rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <ShieldAlert size={18} className="text-primary" />
                      <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>Risk Level Thresholds</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="badge badge-low-risk">LOW RISK</span>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>OCR Confidence ≥ 85%</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="badge badge-medium-risk">MEDIUM RISK</span>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>OCR Confidence 70–84%</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="badge badge-high-risk">HIGH RISK</span>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>OCR Confidence &lt; 70%</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      {/* Help & Guided Tour Modal */}
      <HelpGuideModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />

      {/* User Profile & Authentication Modal */}
      <AuthProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        currentUser={currentUser}
        onUpdateUser={handleUpdateUser}
        onLogin={handleLogin}
        onLogout={handleLogout}
      />
    </div>
  );
}
