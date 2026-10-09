import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/Toast/ToastContext';
import { fetchStaff, createStaff, updateStaff, deleteStaff } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';

export default function Staff() {
  const { isAdmin } = useAuth();
  const { addToast } = useToast();
  const [searchQuery, setSearchQuery] = useState('');
  const { data: staffList, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchStaff({ ...params, search: searchQuery || undefined, per_page: 25 }),
    [searchQuery],
    { perPage: 25 }
  );
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    department: '', designation: '', join_date: '', salary: '',
  });
  const [saving, setSaving] = useState(false);

  const openCreateForm = () => {
    setEditingId(null);
    setFormData({ first_name: '', last_name: '', email: '', phone: '', department: '', designation: '', join_date: '', salary: '' });
    setShowForm(true);
  };

  const openEditForm = (staff) => {
    setEditingId(staff.id);
    setFormData({
      first_name: staff.first_name || '',
      last_name: staff.last_name || '',
      email: staff.email || '',
      phone: staff.phone || '',
      department: staff.department || '',
      designation: staff.designation || '',
      join_date: staff.join_date || '',
      salary: staff.salary?.toString() || '',
    });
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.first_name || !formData.last_name || !formData.email || !formData.join_date) {
      addToast('Name, email, and join date are required', 'error');
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await updateStaff(editingId, {
          first_name: formData.first_name,
          last_name: formData.last_name,
          email: formData.email,
          phone: formData.phone || undefined,
          department: formData.department || undefined,
          designation: formData.designation || undefined,
          join_date: formData.join_date,
          salary: formData.salary ? parseFloat(formData.salary) : undefined,
        });
        addToast('Staff updated successfully', 'success');
      } else {
        const payload = {
          first_name: formData.first_name,
          last_name: formData.last_name,
          email: formData.email,
          phone: formData.phone || undefined,
          department: formData.department || undefined,
          designation: formData.designation || undefined,
          join_date: formData.join_date,
          salary: formData.salary ? parseFloat(formData.salary) : 0,
        };
        await createStaff(payload);
        addToast('Staff created successfully', 'success');
      }
      setShowForm(false);
      setEditingId(null);
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to save staff', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete staff member "${name}"? This action cannot be undone.`)) return;
    try {
      await deleteStaff(id);
      addToast('Staff deleted', 'success');
      refresh();
    } catch (err) {
      addToast(err.message || 'Failed to delete staff', 'error');
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    refresh();
  };

  return (
    <div className="staff-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Staff Management</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total staff` : 'Manage faculty and staff records'}
            </p>
          </div>
          {isAdmin && (
            <button className="btn btn-primary" onClick={openCreateForm}>
              + Add Staff
            </button>
          )}
        </div>
        <form className="search-bar" onSubmit={handleSearch}>
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="text"
            className="search-input"
            placeholder="Search staff by name or department…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search staff"
          />
        </form>
      </div>

      {showForm && (
        <div className="detail-card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 className="detail-card-title">{editingId ? 'Edit Staff' : 'Add New Staff'}</h3>
          <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <div className="form-group">
              <label className="form-label">First Name *</label>
              <input className="form-input" value={formData.first_name} onChange={(e) => setFormData({ ...formData, first_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Last Name *</label>
              <input className="form-input" value={formData.last_name} onChange={(e) => setFormData({ ...formData, last_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Email *</label>
              <input className="form-input" type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Phone</label>
              <input className="form-input" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} placeholder="10-digit number" />
            </div>
            <div className="form-group">
              <label className="form-label">Department</label>
              <input className="form-input" value={formData.department} onChange={(e) => setFormData({ ...formData, department: e.target.value })} placeholder="e.g. Computer Science" />
            </div>
            <div className="form-group">
              <label className="form-label">Designation</label>
              <input className="form-input" value={formData.designation} onChange={(e) => setFormData({ ...formData, designation: e.target.value })} placeholder="e.g. Professor" />
            </div>
            <div className="form-group">
              <label className="form-label">Join Date *</label>
              <input className="form-input" type="date" value={formData.join_date} onChange={(e) => setFormData({ ...formData, join_date: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Salary (₹)</label>
              <input className="form-input" type="number" step="1000" value={formData.salary} onChange={(e) => setFormData({ ...formData, salary: e.target.value })} placeholder="0" />
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
        <SkeletonTable rows={8} cols={5} />
      ) : staffList.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">👤</div>
          <h3>No staff found</h3>
          <p>Staff records will appear here once added by an administrator.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Department</th>
                <th>Designation</th>
                <th>Joined</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {staffList.map((s) => (
                <tr key={s.id}>
                  <td className="cell-primary">{s.full_name || `${s.first_name} ${s.last_name}`}</td>
                  <td className="cell-secondary">{s.email || '—'}</td>
                  <td>{s.department || '—'}</td>
                  <td><span className="risk-badge risk-badge-none">{s.designation || '—'}</span></td>
                  <td className="cell-mono">{s.join_date || '—'}</td>
                  {isAdmin && (
                    <td>
                      <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => openEditForm(s)}>Edit</button>
                        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--accent-danger)' }} onClick={() => handleDelete(s.id, s.full_name || s.first_name)}>Delete</button>
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
