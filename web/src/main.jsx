import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/variables.css';
import './App.css';

// Initialize theme from localStorage or system preference
const savedTheme = localStorage.getItem('bbims_theme');
if (savedTheme) {
  document.documentElement.className = savedTheme;
} else {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.className = prefersDark ? 'dark' : 'light';
  localStorage.setItem('bbims_theme', prefersDark ? 'dark' : 'light');
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
