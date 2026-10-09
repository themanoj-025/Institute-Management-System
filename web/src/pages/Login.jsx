import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const { login, verifyOtp } = useAuth();
  const navigate = useNavigate();

  // Step 1: credentials
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Step 2: OTP
  const [otpRequired, setOtpRequired] = useState(false);
  const [userId, setUserId] = useState(null);
  const [otp, setOtp] = useState('');
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState('');
  const [otpSuccess, setOtpSuccess] = useState('');
  const otpRef = useRef(null);

  // Focus OTP input when step 2 appears
  useEffect(() => {
    if (otpRequired && otpRef.current) {
      otpRef.current.focus();
    }
  }, [otpRequired]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(username, password);
      if (data.status === 'otp_required') {
        setUserId(data.user_id);
        setOtpRequired(true);
        setOtpSuccess('OTP sent! Check your email (or console in dev mode).');
      } else {
        // Fallback: direct JWT login (legacy)
        navigate('/');
      }
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
      setOtpError('Please enter a valid 6-digit OTP.');
      return;
    }
    setOtpError('');
    setOtpLoading(true);
    try {
      await verifyOtp(userId, otp);
      navigate('/');
    } catch (err) {
      setOtpError(err.message || 'Invalid OTP. Please try again.');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleOtpChange = (e) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 6);
    setOtp(val);
    if (otpError) setOtpError('');
  };

  const handleBackToLogin = () => {
    setOtpRequired(false);
    setUserId(null);
    setOtp('');
    setOtpError('');
    setOtpSuccess('');
  };

  // ── OTP Step UI ──
  if (otpRequired) {
    return (
      <div className="login-page">
        <div className="login-container">
          <div className="login-header">
            <div className="login-logo">BB-IMS</div>
            <h1 className="login-title">Binary Brain Institute</h1>
            <p className="login-subtitle">Two-Factor Authentication</p>
          </div>

          <form className="login-form" onSubmit={handleVerifyOtp}>
            {otpError && (
              <div className="login-error" role="alert">
                {otpError}
              </div>
            )}
            {otpSuccess && (
              <div className="login-success" role="status">
                {otpSuccess}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="otp" className="form-label">
                Verification Code
              </label>
              <input
                ref={otpRef}
                id="otp"
                type="text"
                className="form-input"
                value={otp}
                onChange={handleOtpChange}
                placeholder="000000"
                maxLength={6}
                required
                autoComplete="one-time-code"
                inputMode="numeric"
                style={{ fontSize: '1.5rem', letterSpacing: '0.5em', textAlign: 'center' }}
              />
              <p className="form-hint">
                Enter the 6-digit code sent to your registered email.
              </p>
            </div>

            <button
              type="submit"
              className="btn btn-primary login-btn"
              disabled={otpLoading || otp.length !== 6}
            >
              {otpLoading ? 'Verifying…' : 'Verify & Sign in'}
            </button>

            <button
              type="button"
              className="btn btn-ghost back-btn"
              onClick={handleBackToLogin}
              disabled={otpLoading}
            >
              ← Back to login
            </button>
          </form>

          <div className="login-footer">
            <span className="login-footer-hint">
              Didn't receive the code? Check your spam folder or try logging in again.
            </span>
          </div>
        </div>
      </div>
    );
  }

  // ── Credential Step UI ──
  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="login-logo">BB-IMS</div>
          <h1 className="login-title">Binary Brain Institute</h1>
          <p className="login-subtitle">Management System</p>
        </div>

        <form className="login-form" onSubmit={handleLogin}>
          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="username" className="form-label">Username</label>
            <input
              id="username"
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              autoFocus
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={loading}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="login-footer">
          <Link to="/forgot-password" className="login-footer-link" style={{
            color: 'var(--accent, #4f8cf7)',
            textDecoration: 'none',
            fontSize: '0.85rem',
          }}>
            Forgot password?
          </Link>
          <span className="login-footer-hint" style={{ display: 'block', marginTop: '0.5rem' }}>
            Use your institute credentials
          </span>
        </div>
      </div>
    </div>
  );
}
