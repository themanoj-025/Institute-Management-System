import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { fetchPlacements } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';

function PackageBadge({ lpa }) {
  const cls = lpa >= 10 ? 'risk-badge-low'
    : lpa >= 5 ? 'risk-badge-medium'
    : 'risk-badge-high';
  return <span className={`risk-badge ${cls}`}>₹{lpa} LPA</span>;
}

export default function Placements() {
  const { data: placements, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchPlacements({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );

  return (
    <div className="placements-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Placements</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total placements` : 'Student placement records'}
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
        <SkeletonTable rows={6} cols={5} />
      ) : placements.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎓</div>
          <h3>No placements yet</h3>
          <p>Placement records will appear here once students are placed.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Company</th>
                <th>Job Title</th>
                <th>Package</th>
                <th>Offer Date</th>
              </tr>
            </thead>
            <tbody>
              {placements.map((p) => (
                <tr key={p.id}>
                  <td className="cell-primary">{p.student_name}</td>
                  <td>{p.company_name}</td>
                  <td className="cell-secondary">{p.job_title}</td>
                  <td><PackageBadge lpa={p.package_lpa} /></td>
                  <td className="cell-mono">{p.offer_date}</td>
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
