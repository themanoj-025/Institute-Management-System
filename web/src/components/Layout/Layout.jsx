import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import CommandPalette from '../CommandPalette/CommandPalette';
import { useAuth } from '../../hooks/useAuth';

export default function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { user } = useAuth();

  // Command palette keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="app-layout">
      {/* Skip-to-content link for keyboard accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>

      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        onOpenPalette={() => setPaletteOpen(true)}
      />

      <main className="main-content" role="main" id="main-content" tabIndex={-1}>
        <header className="main-header">
          <div className="main-header-left">
            <kbd className="cmd-hint" onClick={() => setPaletteOpen(true)}>
              ⌘K <span className="cmd-hint-text">Commands</span>
            </kbd>
          </div>
          <div className="main-header-right">
            <div className="header-user">
              <span className="header-user-name">{user?.username}</span>
              <span className="header-badge">{user?.role}</span>
            </div>
          </div>
        </header>

        <div className="content-area">
          <Outlet />
        </div>
      </main>

      {paletteOpen && (
        <CommandPalette onClose={() => setPaletteOpen(false)} />
      )}
    </div>
  );
}
