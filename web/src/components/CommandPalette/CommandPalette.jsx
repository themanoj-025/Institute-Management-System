import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const COMMANDS = [
  { id: 'dashboard', label: 'Dashboard', icon: '⌂', path: '/' },
  { id: 'students', label: 'Students', icon: '👤', path: '/students' },
  { id: 'attendance', label: 'Attendance', icon: '📅', path: '/attendance' },
  { id: 'fees', label: 'Fees', icon: '💰', path: '/fees' },
  { id: 'results', label: 'Results', icon: '📊', path: '/results' },
  { id: 'leaves', label: 'Leaves', icon: '📝', path: '/leaves' },
  { id: 'notices', label: 'Notices', icon: '📢', path: '/notices' },
  { id: 'placements', label: 'Placements', icon: '🎓', path: '/placements' },
  { id: 'feedback', label: 'Feedback', icon: '💬', path: '/feedback' },
  { id: 'at-risk', label: 'At-Risk Students', icon: '⚠', path: '/?tab=risk' },
  { id: 'settings', label: 'Settings', icon: '⚙', path: '/settings' },
  { id: 'logout', label: 'Logout', icon: '⇢', path: '/logout' },
];

export default function CommandPalette({ onClose }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const filtered = query.trim()
    ? COMMANDS.filter((cmd) =>
        cmd.label.toLowerCase().includes(query.toLowerCase())
      )
    : COMMANDS;

  useEffect(() => {
    inputRef.current?.focus();
    setSelectedIndex(0);
  }, [query]);

  const execute = useCallback((cmd) => {
    onClose();
    if (cmd.path === '/logout') {
      localStorage.removeItem('bbims_token');
      localStorage.removeItem('bbims_user');
      navigate('/login');
    } else {
      navigate(cmd.path);
    }
  }, [navigate, onClose]);

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      execute(filtered[selectedIndex]);
    }
  };

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div
        className="command-palette"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Command palette"
      >
        <div className="command-palette-input-wrapper">
          <span className="command-palette-prefix">⌘</span>
          <input
            ref={inputRef}
            type="text"
            className="command-palette-input"
            placeholder="Search commands…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Search commands"
          />
        </div>
        <div className="command-palette-results" role="listbox">
          {filtered.length === 0 && (
            <div className="command-palette-empty">No results found</div>
          )}
          {filtered.map((cmd, i) => (
            <div
              key={cmd.id}
              className={`command-palette-item ${i === selectedIndex ? 'selected' : ''}`}
              role="option"
              aria-selected={i === selectedIndex}
              onClick={() => execute(cmd)}
              onMouseEnter={() => setSelectedIndex(i)}
            >
              <span className="command-palette-item-icon">{cmd.icon}</span>
              <span className="command-palette-item-label">{cmd.label}</span>
            </div>
          ))}
        </div>
        <div className="command-palette-footer">
          <span>↑↓ Navigate</span>
          <span>↵ Open</span>
          <span>Esc Close</span>
        </div>
      </div>
    </div>
  );
}
