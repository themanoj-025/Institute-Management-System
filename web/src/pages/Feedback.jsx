import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { fetchFeedback, submitFeedback } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';
import { useToast } from '../components/Toast/ToastContext';

export default function Feedback() {
  const { addToast } = useToast();
  const { data: feedback, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchFeedback({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ subject: '', message: '', rating: '5' });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.subject || !formData.message) {
      addToast('Subject and message are required', 'error');
      return;
    }
    setSaving(true);
    try {
      await submitFeedback({
        subject: formData.subject,
        message: formData.message,
        rating: parseInt(formData.rating),
      });
      addToast('Feedback submitted', 'success');
      setShowForm(false);
      setFormData({ subject: '', message: '', rating: '5' });
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to submit feedback', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="feedback-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Feedback</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total entries` : 'Submit and view feedback'}
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? '× Cancel' : '+ New Feedback'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="detail-card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 className="detail-card-title">Submit Feedback</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Subject</label>
              <input className="form-input" value={formData.subject} onChange={(e) => setFormData({ ...formData, subject: e.target.value })} required placeholder="Brief subject line" />
            </div>
            <div className="form-group">
              <label className="form-label">Message</label>
              <textarea className="form-input" rows="4" value={formData.message} onChange={(e) => setFormData({ ...formData, message: e.target.value })} required placeholder="Share your feedback…" />
            </div>
            <div className="form-group">
              <label className="form-label">Rating</label>
              <select className="form-input" value={formData.rating} onChange={(e) => setFormData({ ...formData, rating: e.target.value })}>
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>{'★'.repeat(n)}{'☆'.repeat(5 - n)}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Submitting…' : 'Submit'}
              </button>
            </div>
          </form>
        </div>
      )}

      {error && (
        <div className="error-banner" role="alert">
          {error.message}
          <button className="error-retry" onClick={refresh}>Retry</button>
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={6} cols={4} />
      ) : feedback.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">💬</div>
          <h3>No feedback yet</h3>
          <p>Feedback entries will appear here once submitted.</p>
        </div>
      ) : (
        <div className="feedback-list" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {feedback.map((f) => (
            <div key={f.id} className="detail-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-2)' }}>
                <div>
                  <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--font-semibold)', margin: 0 }}>{f.subject}</h4>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
                    {f.created_at || f.submitted_at || '—'} · Rating: {'★'.repeat(f.rating || 0)}{'☆'.repeat(5 - (f.rating || 0))}
                  </span>
                </div>
                {f.status && <span className={`risk-badge ${f.status === 'resolved' ? 'risk-badge-low' : 'risk-badge-medium'}`}>{f.status}</span>}
              </div>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 0, lineHeight: 'var(--leading-normal)' }}>
                {f.message || f.content}
              </p>
              {f.reply && (
                <div style={{ marginTop: 'var(--space-3)', padding: 'var(--space-3)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--accent-primary)' }}>
                  <span style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', color: 'var(--accent-primary)' }}>Reply:</span>
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 'var(--space-1) 0 0 0' }}>{f.reply}</p>
                </div>
              )}
            </div>
          ))}

          {pagination && pagination.totalPages > 1 && (
            <div className="pagination" style={{ marginTop: 'var(--space-4)' }}>
              <button className="btn btn-ghost btn-sm" disabled={!pagination.prevPage} onClick={() => goToPage(pagination.prevPage)}>
                ← Previous
              </button>
              <span className="pagination-info">Page {pagination.page} of {pagination.totalPages}</span>
              <button className="btn btn-ghost btn-sm" disabled={!pagination.nextPage} onClick={() => goToPage(pagination.nextPage)}>
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
