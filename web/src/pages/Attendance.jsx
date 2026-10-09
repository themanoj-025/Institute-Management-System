import { useState } from 'react';
import { useApi, usePaginatedApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { fetchAttendance, recordAttendance } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';
import { useToast } from '../components/Toast/ToastContext';

function StatusBadge({ status }) {
  const cls = status === 'present' ? 'risk-badge-low'
    : status === 'late' ? 'risk-badge-medium'
    : status === 'excused' ? 'risk-badge-none'
    : 'risk-badge-high';
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
  return <span className={`risk-badge ${cls}`}>{label}</span>;
}

export default function Attendance() {
  const { isStaff, isAdmin } = useAuth();
  const canMark = isAdmin || isStaff;
  const { addToast } = useToast();
  const { data: records, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchAttendance({ ...params, per_page: 30 }),
    [],
    { perPage: 30 }
  );
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ student_id: '', subject_id: '', session_id: '', date: '', status: 'present' });
  const [saving, setSaving] = useState(false);

  const handleRecord = async (e) => {
    e.preventDefault();
    if (!formData.student_id || !formData.subject_id || !formData.date) {
      addToast('Student ID, Subject ID, and Date are required', 'error');
      return;
    }
    setSaving(true);
    try {
      await recordAttendance([{
        student_id: parseInt(formData.student_id),
        subject_id: parseInt(formData.subject_id),
        session_id: parseInt(formData.session_id) || 1,
        date: formData.date,
        status: formData.status,
      }]);
      addToast('Attendance recorded', 'success');
      setShowForm(false);
      setFormData({ student_id: '', subject_id: '', session_id: '', date: '', status: 'present' });
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to record attendance', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="attendance-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Attendance</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} records` : 'Track student attendance'}
            </p>
          </div>
          {canMark && (
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? '× Cancel' : '+ Mark Attendance'}
            </button>
          )}
        </div>
      </div>

      {showForm && (
        <div className="detail-card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 className="detail-card-title">Record Attendance</h3>
          <form onSubmit={handleRecord} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">Student ID</label>
              <input className="form-input" type="number" value={formData.student_id} onChange={(e) => setFormData({ ...formData, student_id: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Subject ID</label>
              <input className="form-input" type="number" value={formData.subject_id} onChange={(e) => setFormData({ ...formData, subject_id: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Date</label>
              <input className="form-input" type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value })}>
                <option value="present">Present</option>
                <option value="absent">Absent</option>
                <option value="late">Late</option>
                <option value="excused">Excused</option>
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Record'}
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
        <SkeletonTable rows={8} cols={5} />
      ) : records.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <h3>No attendance records</h3>
          <p>Attendance records will appear once they are marked by staff.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Subject ID</th>
                <th>Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td className="cell-mono">{r.student_id}</td>
                  <td className="cell-mono">{r.subject_id}</td>
                  <td>{r.date}</td>
                  <td><StatusBadge status={r.status} /></td>
                </tr>
              ))}
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
