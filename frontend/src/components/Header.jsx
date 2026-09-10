import React from 'react';
import PackTrueLogo from './PackTrueLogo';
import { ArrowLeft } from 'lucide-react';

export default function Header({ currentView, onNavigate }) {
  return (
    <header className="clean-app-header">
      <div className="header-inner">
        <div className="header-brand-group">
          <div className="header-logo-badge" onClick={() => onNavigate('home')} style={{ cursor: 'pointer' }}>
            <PackTrueLogo size={32} />
            <div className="brand-text-block">
              <span className="brand-main-name">PackTrue</span>
              <span className="brand-dept-tag">Accurate label compliance checks, no false alarms.</span>
            </div>
          </div>
        </div>

        <div className="header-nav-actions">
          {currentView === 'scanner' ? (
            <button
              className="btn btn-nav-secondary"
              onClick={() => onNavigate('home')}
            >
              <ArrowLeft size={16} />
              <span>Back to Overview</span>
            </button>
          ) : (
            <button
              className="btn btn-nav-primary"
              onClick={() => onNavigate('scanner')}
            >
              <span>Scan Label</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
