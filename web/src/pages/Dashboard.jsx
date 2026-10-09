import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { fetchDashboardKpis, fetchAtRiskStudents } from '../api/client';
import RiskCard from '../components/RiskCard';
import { SkeletonCard, SkeletonTable } from '../components/Skeleton/Skeleton';

function KpiCard({ title, value, subtitle, accent, loading }) {
  return (
    <div className="kpi-card" style={accent ? { borderTopColor: accent } : {}}>
      {loading ? (
        <div className="kpi-card-loading">
          <div className="skeleton" style={{ width: '60%', height: '0.875rem' }} />
          <div className="skeleton skeleton-mt-2" style={{ width: '40%', height: '2rem' }} />
        </div>
      ) : (
        <>
          <div className="kpi-card-title">{title}</div>
          <div className="kpi-card-value">{value ?? '—'}</div>
          {subtitle && <div className="kpi-card-subtitle">{subtitle}</div>}
        </>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'overview';

  const {
    data: kpis,
    loading: kpisLoading,
    error: kpisError,
  } = useApi(fetchDashboardKpis);

  const {
    data: atRiskData,
    loading: riskLoading,
    error: riskError,
  } = useApi(() => fetchAtRiskStudents({ top_n: 20 }));

  const atRiskStudents = atRiskData?.data || atRiskData || [];

  return (
    <div className="dashboard">
      <div className="page-header">
        <h2 className="page-title">Dashboard</h2>
        <p className="page-subtitle">Overview of institute metrics and at-risk students</p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard
          title="Total Students"
          value={kpis?.total_students?.toLocaleString()}
          accent="var(--accent-primary)"
          loading={kpisLoading}
        />
        <KpiCard
          title="Fees Expected"
          value={kpis ? `₹${(kpis.total_fees_expected / 100000).toFixed(1)}L` : null}
          accent="var(--accent-info)"
          loading={kpisLoading}
        />
        <KpiCard
          title="Fees Collected"
          value={kpis ? `₹${(kpis.total_fees_collected / 100000).toFixed(1)}L` : null}
          subtitle={kpis ? `${kpis.collection_rate}% collection rate` : null}
          accent="var(--accent-success)"
          loading={kpisLoading}
        />
        <KpiCard
          title="At-Risk Students"
          value={kpis?.at_risk_count ?? '—'}
          accent={kpis?.at_risk_count > 0 ? 'var(--accent-danger)' : 'var(--accent-success)'}
          subtitle={kpis?.model_version ? `Model: ${kpis.model_version}` : null}
          loading={kpisLoading}
        />
      </div>

      {/* Tabs */}
      <div className="tabs" role="tablist">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'overview'}
          onClick={() => setSearchParams({ tab: 'overview' })}
        >
          Overview
        </button>
        <button
          className={`tab ${activeTab === 'risk' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'risk'}
          onClick={() => setSearchParams({ tab: 'risk' })}
        >
          At-Risk Students
          {atRiskStudents.length > 0 && (
            <span className="tab-badge">{atRiskStudents.length}</span>
          )}
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="tab-content">
          <div className="section">
            <h3 className="section-title">Recent At-Risk Students</h3>
            {riskLoading ? (
              <SkeletonTable rows={4} cols={3} />
            ) : riskError ? (
              <div className="empty-state">
                <p>Could not load at-risk data.</p>
              </div>
            ) : atRiskStudents.length === 0 ? (
              <div className="empty-state">
                <p>No at-risk students identified.</p>
              </div>
            ) : (
              <div className="risk-card-list">
                {atRiskStudents.slice(0, 5).map((student) => (
                  <RiskCard
                    key={student.student_id}
                    studentId={student.student_id}
                    studentName={student.name}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Risk Tab */}
      {activeTab === 'risk' && (
        <div className="tab-content">
          <div className="section">
            <h3 className="section-title">All At-Risk Students</h3>
            <p className="section-description">
              Students flagged by the ML model with SHAP-powered explanations.
              Each card shows the top contributing factors for the risk assessment.
            </p>
            {riskLoading ? (
              <SkeletonTable rows={6} cols={3} />
            ) : riskError ? (
              <div className="empty-state">
                <p>Could not load at-risk data.</p>
              </div>
            ) : atRiskStudents.length === 0 ? (
              <div className="empty-state">
                <p>No at-risk students identified.</p>
              </div>
            ) : (
              <div className="risk-card-list">
                {atRiskStudents.map((student) => (
                  <RiskCard
                    key={student.student_id}
                    studentId={student.student_id}
                    studentName={student.name}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
