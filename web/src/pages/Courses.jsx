import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/Toast/ToastContext';
import { fetchCourses, createCourse, updateCourse, deleteCourse } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';

export default function Courses() {
  const { isAdmin } = useAuth();
  const { addToast } = useToast();
  const { data: courses, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchCourses({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    code: '', name: '', duration_months: '', fee: '', description: '',
  });
  const [saving, setSaving] = useState(false);

  const openCreateForm = () => {
    setEditingId(null);
    setFormData({ code: '', name: '', duration_months: '6', fee: '', description: '' });
    setShowForm(true);
  };

  const openEditForm = (course) => {
    setEditingId(course.id);
    setFormData({
      code: course.code || '',
      name: course.name || '',
      duration_months: course.duration_months?.toString() || '',
      fee: course.fee?.toString() || '',
      description: course.description || '',
    });
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.code || !formData.name || !formData.duration_months || !formData.fee) {
      addToast('Code, name, duration, and fee are required', 'error');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        code: formData.code,
        name: formData.name,
        duration_months: parseInt(formData.duration_months),
        fee: parseFloat(formData.fee),
        description: formData.description || undefined,
      };
      if (editingId) {
        await updateCourse(editingId, payload);
        addToast('Course updated successfully', 'success');
      } else {
        await createCourse(payload);
        addToast('Course created successfully', 'success');
      }
      setShowForm(false);
      setEditingId(null);
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to save course', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete course "${name}"? This will also remove associated subjects and enrollments.`)) return;
    try {
      await deleteCourse(id);
      addToast('Course deleted', 'success');
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to delete course', 'error');
    }
  };

  return (
    <div className="courses-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Courses</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total courses` : 'Manage courses, subjects, and curriculum'}
            </p>
          </div>
          {isAdmin && (
            <button className="btn btn-primary" onClick={openCreateForm}>
              + Add Course
            </button>
          )}
        </div>
      </div>

      {showForm && (
        <div className="detail-card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 className="detail-card-title">{editingId ? 'Edit Course' : 'Add New Course'}</h3>
          <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">Course Code *</label>
              <input className="form-input" value={formData.code} onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })} required placeholder="e.g. CS101" />
            </div>
            <div className="form-group">
              <label className="form-label">Course Name *</label>
              <input className="form-input" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required placeholder="e.g. Computer Science" />
            </div>
            <div className="form-group">
              <label className="form-label">Duration (Months) *</label>
              <input className="form-input" type="number" min="1" value={formData.duration_months} onChange={(e) => setFormData({ ...formData, duration_months: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Fee (₹) *</label>
              <input className="form-input" type="number" step="1000" min="0" value={formData.fee} onChange={(e) => setFormData({ ...formData, fee: e.target.value })} required />
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Description</label>
              <textarea className="form-input" rows="3" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="Course description and key highlights…" />
            </div>
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-ghost" onClick={() => { setShowForm(false); setEditingId(null); }}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving…' : editingId ? 'Update' : 'Create'}
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
        <SkeletonTable rows={8} cols={4} />
      ) : courses.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <h3>No courses found</h3>
          <p>Courses will appear here once they are created by an administrator.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Duration</th>
                <th>Fee (₹)</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id}>
                  <td className="cell-mono"><span className="risk-badge risk-badge-none">{c.code}</span></td>
                  <td className="cell-primary">{c.name}</td>
                  <td>{c.duration_months ? `${c.duration_months} months` : '—'}</td>
                  <td>{c.fee?.toLocaleString()}</td>
                  {isAdmin && (
                    <td>
                      <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => openEditForm(c)}>Edit</button>
                        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--accent-danger)' }} onClick={() => handleDelete(c.id, c.name)}>Delete</button>
                      </div>
                    </td>
                  )}
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
