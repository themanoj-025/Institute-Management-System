import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { fetchStudent, updateStudent } from '../api/client';
import RiskCard from '../components/RiskCard';
import { SkeletonCard } from '../components/Skeleton/Skeleton';

export default function StudentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: student, loading, error, refresh } = useApi(() => fetchStudent(id), [id]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({});

  if (loading) {
    return (
      <div className="detail-page">
        <div className="page-header">
          <button className="btn btn-ghost" onClick={() => navigate('/students')}>← Back</button>
        </div>
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="detail-page">
        <div className="page-header">
          <button className="btn btn-ghost" onClick={() => navigate('/students')}>← Back</button>
        </div>
        <div className="error-banner" role="alert">
          {error.message}
        </div>
      </div>
    );
  }

  if (!student) return null;

  const handleEdit = () => {
    setForm({
      first_name: student.first_name || '',
      last_name: student.last_name || '',
      email: student.email || '',
      phone: student.phone || '',
    });
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateStudent(id, form);
      setEditing(false);
      refresh();
    } catch (err) {
      alert('Failed to save: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
  };

  return (
    <div className="detail-page">
      <div className="page-header">
        <button className="btn btn-ghost" onClick={() => navigate('/students')}>← Back</button>
        <div className="page-header-right">
          {editing ? (
            <>
              <button className="btn btn-ghost" onClick={handleCancel}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <button className="btn btn-primary" onClick={handleEdit}>Edit</button>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-card">
          <h3 className="detail-card-title">Student Information</h3>
          <div className="detail-fields">
            <div className="detail-field">
              <span className="detail-label">Enrollment No</span>
              <span className="detail-value cell-mono">{student.enrollment_no}</span>
            </div>

            {editing ? (
              <>
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input
                    className="form-input"
                    value={form.first_name}
                    onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input
                    className="form-input"
                    value={form.last_name}
                    onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input
                    className="form-input"
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input
                    className="form-input"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </div>
              </>
            ) : (
              <>
                <div className="detail-field">
                  <span className="detail-label">Name</span>
                  <span className="detail-value">{student.first_name} {student.last_name}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-label">Email</span>
                  <span className="detail-value">{student.email}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-label">Phone</span>
                  <span className="detail-value">{student.phone || '—'}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-label">Gender</span>
                  <span className="detail-value">{student.gender || '—'}</span>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="detail-card">
          <h3 className="detail-card-title">Risk Assessment</h3>
          <RiskCard studentId={student.id} studentName={`${student.first_name} ${student.last_name}`} />
        </div>
      </div>
    </div>
  );
}
