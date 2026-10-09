import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { fetchNotices } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';

function TargetBadge({ target }) {
  const cls = target === 'all' ? 'risk-badge-low'
    : target === 'staff' ? 'risk-badge-medium'
    : target === 'students' ? 'risk-badge-none'
    : 'risk-badge-high';
  return <span className={`risk-badge ${cls}`}>{target || 'all'}</span>;
}

export default function Notices() {
  const { data: notices, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchNotices({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );

  return (
    <div className="notices-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Notices</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total notices` : 'Announcements and notices'}
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error.message}
          <button className="error-retry" onClick={refresh}>Retry</button>
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={6} cols={4} />
      ) : notices.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📢</div>
          <h3>No notices</h3>
          <p>Notices will appear here once published by the administration.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Target</th>
                <th>Created</th>
                <th>Content</th>
              </tr>
            </thead>
            <tbody>
              {notices.map((n) => (
                <tr key={n.id}>
                  <td className="cell-primary">{n.title}</td>
                  <td><TargetBadge target={n.target_role || n.audience} /></td>
                  <td className="cell-mono">{n.created_at || n.created_date || '—'}</td>
                  <td className="cell-secondary" style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {n.content || n.message || '—'}
                  </td>
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
