import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { fetchRiskThresholds, updateRiskThresholds } from '../api/client';
import { SkeletonCard } from '../components/Skeleton/Skeleton';

function PromotionHistory() {
  const { data, loading, error } = useApi(
    () => fetch('/v1/admin/ml/promotion-history').then(r => r.json()),
    { initialFetch: true }
  );

  if (loading) return (
    <div className="settings-section">
      <h3 className="settings-section-title">ML Promotion History</h3>
      <SkeletonCard />
    </div>
  );

  if (error) return (
    <div className="settings-section">
      <h3 className="settings-section-title">ML Promotion History</h3>
      <div className="error-banner">Unable to load promotion history</div>
    </div>
  );

  const records = data?.data || [];

  return (
    <div className="settings-section">
      <h3 className="settings-section-title">ML Promotion History</h3>
      <p className="settings-section-desc">
        Track record of model promotion decisions from training runs.
      </p>
      {records.length === 0 ? (
        <p className="text-muted">No training runs recorded yet.</p>
      ) : (
        <div className="table-wrapper">
          <table className="promotion-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Candidate</th>
                <th>AUROC</th>
                <th>F1</th>
                <th>Active AUROC</th>
                <th>Result</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className={r.promoted ? 'row-promoted' : 'row-not-promoted'}>
                  <td>{r.timestamp ? new Date(r.timestamp).toLocaleDateString() : '—'}</td>
                  <td className="cell-code">{r.candidate_model_version || '—'}</td>
                  <td>{r.candidate_auroc != null ? r.candidate_auroc.toFixed(4) : '—'}</td>
                  <td>{r.candidate_f1 != null ? r.candidate_f1.toFixed(4) : '—'}</td>
                  <td>{r.active_auroc != null ? r.active_auroc.toFixed(4) : '—'}</td>
                  <td>
                    <span className={`badge ${r.promoted ? 'badge-success' : 'badge-warning'}`}>
                      {r.promoted ? 'PROMOTED' : 'NOT PROMOTED'}
                    </span>
                  </td>
                  <td className="cell-reason">{r.reason || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('bbims_theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.className = theme;
    localStorage.setItem('bbims_theme', theme);
  }, [theme]);

  return (
    <div className="settings-section">
      <h3 className="settings-section-title">Appearance</h3>
      <div className="theme-toggle">
        <button
          className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
          onClick={() => setTheme('light')}
          aria-label="Light mode"
        >
          ☀️ Light
        </button>
        <button
          className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
          onClick={() => setTheme('dark')}
          aria-label="Dark mode"
        >
          🌙 Dark
        </button>
      </div>
    </div>
  );
}

function RiskThresholds() {
  const { data, loading, error, refresh } = useApi(fetchRiskThresholds);
  const [thresholds, setThresholds] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data?.thresholds) {
      setThresholds({ ...data.thresholds });
    }
  }, [data]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateRiskThresholds(thresholds);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      alert('Failed to save: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key, value) => {
    setThresholds((prev) => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  if (loading) return <SkeletonCard />;
  if (error) return <div className="error-banner">Failed to load thresholds</div>;

  return (
    <div className="settings-section">
      <h3 className="settings-section-title">Risk Thresholds</h3>
      <p className="settings-section-desc">
        Configure the thresholds used by the ML model to flag at-risk students.
      </p>
      <div className="thresholds-grid">
        {Object.entries(thresholds).map(([key, value]) => (
          <div key={key} className="form-group">
            <label className="form-label">
              {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </label>
            <input
              type="number"
              className="form-input"
              value={value}
              onChange={(e) => handleChange(key, e.target.value)}
              step="0.1"
            />
          </div>
        ))}
      </div>
      <button
        className="btn btn-primary"
        onClick={handleSave}
        disabled={saving}
      >
        {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save Thresholds'}
      </button>
    </div>
  );
}

export default function Settings() {
  const { isAdmin } = useAuth();

  return (
    <div className="settings-page">
      <div className="page-header">
        <h2 className="page-title">Settings</h2>
        <p className="page-subtitle">Configure your preferences and system settings</p>
      </div>

      <div className="settings-grid">
        <ThemeToggle />

        {isAdmin && <RiskThresholds />}
        {isAdmin && <PromotionHistory />}
      </div>
    </div>
  );
}
