import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { fetchResults, recordResults } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';
import { useToast } from '../components/Toast/ToastContext';

function ScoreBar({ obtained, total }) {
  const pct = total > 0 ? Math.round((obtained / total) * 100) : 0;
  const color = pct >= 75 ? 'var(--accent-success)' : pct >= 40 ? 'var(--accent-warning)' : 'var(--accent-danger)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      <div style={{ flex: 1, height: '6px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 'var(--radius-full)', transition: 'width var(--transition-slow)' }} />
      </div>
      <span style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', color, minWidth: '3rem', textAlign: 'right' }}>
        {obtained}/{total} ({pct}%)
      </span>
    </div>
  );
}

export default function Results() {
  const { isStaff, isAdmin } = useAuth();
  const canRecord = isAdmin || isStaff;
  const { addToast } = useToast();
  const { data: results, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchResults({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    student_id: '', subject_id: '', session_id: '1', exam_type: 'Midterm',
    marks_obtained: '', total_marks: '100',
  });
  const [saving, setSaving] = useState(false);

  const handleRecord = async (e) => {
    e.preventDefault();
    if (!formData.student_id || !formData.marks_obtained) {
      addToast('Student ID and marks are required', 'error');
      return;
    }
    setSaving(true);
    try {
      await recordResults([{
        student_id: parseInt(formData.student_id),
        subject_id: parseInt(formData.subject_id) || 1,
        session_id: parseInt(formData.session_id),
        exam_type: formData.exam_type,
        marks_obtained: parseFloat(formData.marks_obtained),
        total_marks: parseFloat(formData.total_marks),
      }]);
      addToast('Result recorded', 'success');
      setShowForm(false);
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to record result', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="results-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Results</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total results` : 'Exam and assessment results'}
            </p>
          </div>
          {canRecord && (
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? '× Cancel' : '+ Record Result'}
            </button>
          )}
        </div>
      </div>

      {showForm && (
        <div className="detail-card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 className="detail-card-title">Record Exam Result</h3>
          <form onSubmit={handleRecord} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">Student ID</label>
              <input className="form-input" type="number" value={formData.student_id} onChange={(e) => setFormData({ ...formData, student_id: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Subject ID</label>
              <input className="form-input" type="number" value={formData.subject_id} onChange={(e) => setFormData({ ...formData, subject_id: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Exam Type</label>
              <select className="form-input" value={formData.exam_type} onChange={(e) => setFormData({ ...formData, exam_type: e.target.value })}>
                <option>Midterm</option>
                <option>Final</option>
                <option>Quiz</option>
                <option>Assignment</option>
                <option>Practical</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Total Marks</label>
              <input className="form-input" type="number" step="0.1" value={formData.total_marks} onChange={(e) => setFormData({ ...formData, total_marks: e.target.value })} />
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Marks Obtained</label>
              <input className="form-input" type="number" step="0.1" value={formData.marks_obtained} onChange={(e) => setFormData({ ...formData, marks_obtained: e.target.value })} required />
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
      ) : results.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <h3>No results yet</h3>
          <p>Exam results will appear once they are entered by staff.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Subject ID</th>
                <th>Exam Type</th>
                <th>Score</th>
                <th>Grade</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td className="cell-mono">{r.student_id}</td>
                  <td className="cell-mono">{r.subject_id}</td>
                  <td><span className="risk-badge risk-badge-none">{r.exam_type}</span></td>
                  <td><ScoreBar obtained={r.marks_obtained} total={r.total_marks} /></td>
                  <td>{r.grade || '—'}</td>
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
