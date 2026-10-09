import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePaginatedApi } from '../hooks/useApi';
import { fetchStudents } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';

export default function Students() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const { data: students, pagination, loading, error, goToPage, refresh } = usePaginatedApi(
    fetchStudents,
    [],
    { perPage: 25 }
  );

  const handleSearch = (e) => {
    e.preventDefault();
    refresh();
  };

  return (
    <div className="students-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Students</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total students` : 'Manage student records'}
            </p>
          </div>
        </div>

        <form className="search-bar" onSubmit={handleSearch}>
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="text"
            className="search-input"
            placeholder="Search students by name or enrollment…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search students"
          />
        </form>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          Failed to load students: {error.message}
          <button className="error-retry" onClick={refresh}>Retry</button>
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={8} cols={4} />
      ) : students.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <h3>No students found</h3>
          <p>Students will appear here once they are enrolled.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Enrollment No</th>
                <th>Name</th>
                <th>Email</th>
                <th>Course</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr
                  key={student.id}
                  className="table-row-clickable"
                  onClick={() => navigate(`/students/${student.id}`)}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/students/${student.id}`)}
                >
                  <td className="cell-mono">{student.enrollment_no}</td>
                  <td className="cell-primary">{student.first_name} {student.last_name}</td>
                  <td className="cell-secondary">{student.email}</td>
                  <td>{student.course_name || '—'}</td>
                  <td>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/students/${student.id}`);
                      }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {pagination && pagination.totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-ghost btn-sm"
                disabled={!pagination.prevPage}
                onClick={() => goToPage(pagination.prevPage)}
                aria-label="Previous page"
              >
                ← Previous
              </button>
              <span className="pagination-info">
                Page {pagination.page} of {pagination.totalPages}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={!pagination.nextPage}
                onClick={() => goToPage(pagination.nextPage)}
                aria-label="Next page"
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
