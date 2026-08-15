import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { fetchLeaves, applyLeave } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';
import { useToast } from '../components/Toast/ToastContext';

function LeaveStatusBadge({ status }) {
  const cls = status === 'approved' ? 'risk-badge-low'
    : status === 'rejected' ? 'risk-badge-high'
    : 'risk-badge-medium';
  return <span className={`risk-badge ${cls}`}>{status}</span>;
}

export default function Leaves() {
  const { addToast } = useToast();
  const { data: leaves, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchLeaves({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    student_id: '', reason: '', start_date: '', end_date: '', leave_type: 'Sick',
  });
  const [saving, setSaving] = useState(false);

  const handleApply = async (e) => {
    e.preventDefault();
    if (!formData.reason || !formData.start_date || !formData.end_date) {
      addToast('Reason, start date, and end date are required', 'error');
      return;
    }
    setSaving(true);
    try {
      await applyLeave({
        ...formData,
        student_id: parseInt(formData.student_id) || undefined,
      });
      addToast('Leave applied successfully', 'success');
      setShowForm(false);
      setFormData({ student_id: '', reason: '', start_date: '', end_date: '', leave_type: 'Sick' });
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to apply leave', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="leaves-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Leaves</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total leaves` : 'Leave applications'}
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? '× Cancel' : '+ Apply Leave'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="detail-card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 className="detail-card-title">Apply for Leave</h3>
          <form onSubmit={handleApply} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">Leave Type</label>
              <select className="form-input" value={formData.leave_type} onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}>
                <option>Sick</option>
                <option>Casual</option>
                <option>Personal</option>
                <option>Emergency</option>
                <option>Other</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <input className="form-input" type="date" value={formData.start_date} onChange={(e) => setFormData({ ...formData, start_date: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">End Date</label>
              <input className="form-input" type="date" value={formData.end_date} onChange={(e) => setFormData({ ...formData, end_date: e.target.value })} required />
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Reason</label>
              <textarea className="form-input" rows="3" value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })} required />
            </div>
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
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
        <SkeletonTable rows={6} cols={5} />
      ) : leaves.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📝</div>
          <h3>No leave records</h3>
          <p>Leave applications will appear here once submitted.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Type</th>
                <th>From</th>
                <th>To</th>
                <th>Days</th>
                <th>Status</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {leaves.map((l) => {
                const days = l.start_date && l.end_date
                  ? Math.max(0, (new Date(l.end_date) - new Date(l.start_date)) / (1000 * 60 * 60 * 24) + 1)
                  : 0;
                return (
                  <tr key={l.id}>
                    <td className="cell-mono">{l.student_id}</td>
                    <td><span className="risk-badge risk-badge-none">{l.leave_type || '—'}</span></td>
                    <td className="cell-mono">{l.start_date}</td>
                    <td className="cell-mono">{l.end_date}</td>
                    <td className="cell-mono">{days}</td>
                    <td><LeaveStatusBadge status={l.status || 'pending'} /></td>
                    <td className="cell-secondary" style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {l.reason || '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {pagination && pagination.totalPages > 1 && (
            <div className="pagination">
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
