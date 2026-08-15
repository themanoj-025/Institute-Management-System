import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const MENU_ITEMS = {
  admin: [
    { label: 'Dashboard', icon: '◆', path: '/' },
    { label: 'Analytics', icon: '📊', path: '/analytics' },
    { label: 'Students', icon: '▣', path: '/students' },
    { label: 'Staff', icon: '👤', path: '/staff' },
    { label: 'Courses', icon: '📚', path: '/courses' },
    { label: 'Attendance', icon: '📅', path: '/attendance' },
    { label: 'Fees', icon: '💰', path: '/fees' },
    { label: 'Results', icon: '📊', path: '/results' },
    { label: 'Leaves', icon: '📝', path: '/leaves' },
    { label: 'Placements', icon: '🎓', path: '/placements' },
    { label: 'Notices', icon: '📢', path: '/notices' },
    { label: 'Feedback', icon: '💬', path: '/feedback' },
    { label: 'At-Risk', icon: '⚠', path: '/?tab=risk' },
    { label: 'Settings', icon: '⚙', path: '/settings' },
  ],
  staff: [
    { label: 'Dashboard', icon: '◆', path: '/' },
    { label: 'Students', icon: '▣', path: '/students' },
    { label: 'Attendance', icon: '📅', path: '/attendance' },
    { label: 'Fees', icon: '💰', path: '/fees' },
    { label: 'Results', icon: '📊', path: '/results' },
    { label: 'Leaves', icon: '📝', path: '/leaves' },
    { label: 'Notices', icon: '📢', path: '/notices' },
    { label: 'Placements', icon: '🎓', path: '/placements' },
    { label: 'Feedback', icon: '💬', path: '/feedback' },
    { label: 'Settings', icon: '⚙', path: '/settings' },
  ],
  student: [
    { label: 'Dashboard', icon: '◆', path: '/' },
    { label: 'Attendance', icon: '📅', path: '/attendance' },
    { label: 'Fees', icon: '💰', path: '/fees' },
    { label: 'Results', icon: '📊', path: '/results' },
    { label: 'Leaves', icon: '📝', path: '/leaves' },
    { label: 'Notices', icon: '📢', path: '/notices' },
    { label: 'Placements', icon: '🎓', path: '/placements' },
    { label: 'Feedback', icon: '💬', path: '/feedback' },
    { label: 'Settings', icon: '⚙', path: '/settings' },
  ],
};

export default function Sidebar({ collapsed, onToggle, onOpenPalette }) {
  const { user, logout } = useAuth();
  const items = MENU_ITEMS[user?.role] || MENU_ITEMS.student;

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`} role="navigation" aria-label="Main navigation">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          {collapsed ? 'BB' : 'BB-IMS'}
        </div>
        <button
          className="sidebar-toggle"
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? '→' : '←'}
        </button>
      </div>

      <nav className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            tabIndex={0}
          >
            <span className="sidebar-link-icon" aria-hidden="true">{item.icon}</span>
            {!collapsed && <span className="sidebar-link-label">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button
          className="sidebar-link sidebar-palette-btn"
          onClick={onOpenPalette}
          aria-label="Open command palette"
          tabIndex={0}
        >
          <span className="sidebar-link-icon">⌘</span>
          {!collapsed && <span className="sidebar-link-label">Commands</span>}
        </button>

        <div className="sidebar-user">
          <div className="sidebar-avatar" aria-hidden="true">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          {!collapsed && (
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user?.username}</span>
              <span className="sidebar-user-role">{user?.role}</span>
            </div>
          )}
        </div>

        <button
          className="sidebar-link sidebar-logout"
          onClick={logout}
          aria-label="Logout"
        >
          <span className="sidebar-link-icon">⇢</span>
          {!collapsed && <span className="sidebar-link-label">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
