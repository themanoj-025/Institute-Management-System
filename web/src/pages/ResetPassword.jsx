import { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { resetPassword } from '../api/client';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const userId = parseInt(searchParams.get('user_id') || '0', 10);
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])/.test(newPassword)) {
      setError('Password must contain uppercase, lowercase, digit, and special character');
      return;
    }

    if (!userId || !token) {
      setError('Invalid reset link. Please request a new one.');
      return;
    }

    setLoading(true);
    try {
      const data = await resetPassword(userId, token, newPassword);
      setMessage(data.message || 'Password reset successfully!');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.message || 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  if (!userId || !token) {
    return (
      <div className="login-page">
        <div className="login-container" style={{ maxWidth: '420px' }}>
          <div className="login-header">
            <div className="login-logo">BB-IMS</div>
            <h1 className="login-title">Invalid Reset Link</h1>
          </div>
          <p style={{ textAlign: 'center', color: 'var(--text-secondary, #6c757d)', margin: '2rem 0' }}>
            This password reset link is invalid or has expired.
          </p>
          <div className="login-footer">
            <Link to="/forgot-password" className="login-footer-link" style={{
              color: 'var(--accent, #4f8cf7)',
              textDecoration: 'none',
            }}>
              Request a new reset link →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-container" style={{ maxWidth: '420px' }}>
        <div className="login-header">
          <div className="login-logo">BB-IMS</div>
          <h1 className="login-title">Reset Password</h1>
          <p className="login-subtitle">Enter your new password</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error" role="alert">{error}</div>
          )}
          {message && (
            <div className="login-success" role="alert" style={{
              background: 'var(--success-bg, #d4edda)',
              color: 'var(--success-text, #155724)',
              padding: '0.75rem 1rem',
              borderRadius: '6px',
              marginBottom: '1rem',
              fontSize: '0.9rem',
              lineHeight: 1.4,
            }}>{message}</div>
          )}

          <div className="form-group">
            <label htmlFor="newPassword" className="form-label">New Password</label>
            <input
              id="newPassword"
              type="password"
              className="form-input"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              className="form-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter new password"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={loading}
          >
            {loading ? 'Resetting…' : 'Reset Password'}
          </button>
        </form>

        <div className="login-footer">
          <Link to="/login" className="login-footer-link" style={{
            color: 'var(--accent, #4f8cf7)',
            textDecoration: 'none',
          }}>
            ← Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
