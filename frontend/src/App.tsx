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
import { Settings as SettingsIcon } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTabType>('dashboard');
  const [theme, setTheme] = useState<'dark' | 'light'>('light'); // default modern light mode matching reference
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
                className="viewport-tab-page settings-card-view"
              >
                <div className="card-glass p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <SettingsIcon size={24} className="text-primary" />
                    <h2 className="text-xl font-bold">System Configuration & API Settings</h2>
                  </div>
                  <div className="settings-grid-info">
                    <div className="setting-item">
                      <span className="text-muted">FastAPI Backend Status:</span>
                      <strong className={backendOnline ? 'text-success' : 'text-danger'}>
                        {backendOnline ? 'Online & Healthy (http://127.0.0.1:8000)' : 'Offline / Disconnected'}
                      </strong>
                    </div>
                    <div className="setting-item">
                      <span className="text-muted">Active Embedding Model:</span>
                      <strong>all-MiniLM-L6-v2 (384-dimensional dense vectors)</strong>
                    </div>
                    <div className="setting-item">
                      <span className="text-muted">Confidence Reranking Weights:</span>
                      <strong>50% Cosine Similarity + 50% OCR Confidence</strong>
                    </div>
                    <div className="setting-item">
                      <span className="text-muted">Risk Level Thresholds:</span>
                      <strong>LOW (≥85%), MEDIUM (70-84%), HIGH (&lt;70%)</strong>
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
