import React, { useState } from 'react';
import { Search, Bell, HelpCircle, User } from 'lucide-react';
import type { UserProfile } from '../types';

interface TopHeaderProps {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  backendOnline: boolean;
  onGlobalSearch: (q: string) => void;
  onOpenHelp: () => void;
  currentUser: UserProfile;
  onOpenProfile: () => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  theme,
  toggleTheme,
  backendOnline,
  onGlobalSearch,
  onOpenHelp,
  currentUser,
  onOpenProfile,
}) => {
  const [searchValue, setSearchValue] = useState<string>('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchValue.trim()) {
      onGlobalSearch(searchValue.trim());
    }
  };

  return (
    <header className="docsage-top-header">
      {/* Global Search Input */}
      <div className="header-search-container">
        <Search size={16} className="header-search-icon" />
        <input
          type="text"
          className="header-search-input"
          placeholder="Ask a question about your documents..."
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="search-shortcut-badge">
          <span>Ctrl</span>
          <span>K</span>
        </div>
      </div>

      {/* Header Right Actions */}
      <div className="header-right-actions">
        {/* Backend Online Pill */}
        <div className={`backend-status-pill ${backendOnline ? 'online' : 'offline'}`}>
          <span className="status-pulse-dot" />
          <span>{backendOnline ? 'API Ready' : 'Connecting...'}</span>
        </div>

        {/* Help Tour Trigger */}
        <button className="header-icon-btn" onClick={onOpenHelp} title="Open System Guide">
          <HelpCircle size={18} />
        </button>

        {/* Notification Bell with Badge */}
        <button 
          className="header-icon-btn notification-btn" 
          onClick={onOpenProfile} 
          title="Notifications & Activity"
        >
          <Bell size={18} />
          <span className="notification-dot" />
        </button>

        {/* Dark Mode Switcher */}
        <div className="header-theme-toggle">
          <label className="switch-toggle">
            <input
              type="checkbox"
              checked={theme === 'dark'}
              onChange={toggleTheme}
            />
            <span className="slider-round" />
          </label>
          <span className="theme-toggle-label">Dark Mode</span>
        </div>

        {/* Interactive User Avatar Button */}
        <button
          className="header-avatar-circle"
          onClick={onOpenProfile}
          title={`Profile: ${currentUser.name} (${currentUser.role})`}
        >
          {currentUser.avatarText || <User size={16} />}
        </button>
      </div>
    </header>
  );
};
