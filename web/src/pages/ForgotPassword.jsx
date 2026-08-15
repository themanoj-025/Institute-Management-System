import { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../api/client';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const data = await forgotPassword(email);
      setMessage(data.message || 'If an account with that email exists, a password reset link has been sent.');
    } catch (err) {
      setError(err.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container" style={{ maxWidth: '420px' }}>
        <div className="login-header">
          <div className="login-logo">BB-IMS</div>
          <h1 className="login-title">Forgot Password</h1>
          <p className="login-subtitle">Enter your email to receive a reset link</p>
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
            <label htmlFor="email" className="form-label">Email Address</label>
            <input
              id="email"
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your registered email"
              required
              autoFocus
              autoComplete="email"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={loading}
          >
            {loading ? 'Sending…' : 'Send Reset Link'}
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
