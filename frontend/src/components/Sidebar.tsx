import React from 'react';
import { 
  Scale, 
  LayoutDashboard, 
  UploadCloud, 
  FolderOpen, 
  Search, 
  BarChart3, 
  Settings, 
  Layers, 
  ShieldCheck, 
  Sun, 
  Moon,
  HelpCircle
} from 'lucide-react';
import type { UserProfile } from '../types';

export type NavTabType = 'dashboard' | 'upload' | 'documents' | 'query' | 'compare' | 'evaluation' | 'help' | 'settings';

interface SidebarProps {
  activeTab: NavTabType;
  setActiveTab: (tab: NavTabType) => void;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  onOpenHelp: () => void;
  currentUser: UserProfile;
  onOpenProfile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  theme,
  toggleTheme,
  onOpenHelp,
  currentUser,
  onOpenProfile,
}) => {
  return (
    <aside className="docsage-sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand-section">
        <div className="sidebar-logo-box">
          <Scale size={22} className="sidebar-logo-icon" />
        </div>
        <div className="sidebar-brand-text">
          <div className="sidebar-brand-name">DocSage</div>
          <div className="sidebar-brand-tagline">AI for Legal Documents</div>
        </div>
      </div>

      {/* Main Navigation Menu */}
      <nav className="sidebar-nav-group">
        <button
          className={`sidebar-nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <UploadCloud size={18} />
          <span>Upload Documents</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          <FolderOpen size={18} />
          <span>Documents</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'query' ? 'active' : ''}`}
          onClick={() => setActiveTab('query')}
        >
          <Search size={18} />
          <span>Query</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'evaluation' ? 'active' : ''}`}
          onClick={() => setActiveTab('evaluation')}
        >
          <BarChart3 size={18} />
          <span>Evaluation</span>
        </button>

        <button
          className="sidebar-nav-item help-trigger-btn"
          onClick={onOpenHelp}
        >
          <HelpCircle size={18} className="text-primary" />
          <span>Help & Guide</span>
          <span className="sidebar-badge-new">Tour</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </nav>

      {/* Tools Section */}
      <div className="sidebar-tools-section">
        <span className="sidebar-section-title">TOOLS</span>
        <button
          className={`sidebar-nav-item ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
        >
          <Layers size={18} />
          <span>Normal RAG (Baseline)</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <ShieldCheck size={18} className="text-success" />
          <span>Confidence-Aware RAG</span>
        </button>
      </div>

      {/* Sidebar Footer Controls */}
      <div className="sidebar-footer-section">
        {/* Theme Switcher Toggle Pill */}
        <div className="theme-segmented-control">
          <button
            className={`theme-segment-btn ${theme === 'light' ? 'active' : ''}`}
            onClick={() => theme !== 'light' && toggleTheme()}
          >
            <Sun size={14} />
            <span>Light</span>
          </button>
          <button
            className={`theme-segment-btn ${theme === 'dark' ? 'active' : ''}`}
            onClick={() => theme !== 'dark' && toggleTheme()}
          >
            <Moon size={14} />
            <span>Dark</span>
          </button>
        </div>

        {/* Interactive User Profile Card */}
        <button
          className="sidebar-user-card interactive"
          onClick={onOpenProfile}
          title="Click to view profile & account settings"
        >
          <div className="user-avatar-circle">{currentUser.avatarText || 'AS'}</div>
          <div className="user-text-info">
            <span className="user-full-name">{currentUser.name}</span>
            <span className="user-role-label">{currentUser.role}</span>
          </div>
        </button>
      </div>
    </aside>
  );
};
