import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { fetchAnalyticsSummary } from '../api/client';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend,
} from 'recharts';
import { SkeletonCard } from '../components/Skeleton/Skeleton';

const COLORS = ['#89b4fa', '#a6e3a1', '#fab387', '#f38ba8', '#cba6f7', '#94e2d5', '#f9e2af', '#b4befe'];

function ChartCard({ title, loading, error, children }) {
  return (
    <div className="chart-card">
      <h3 className="chart-card-title">{title}</h3>
      {loading ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-tertiary)' }}>
          Loading chart...
        </div>
      ) : error ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--accent-danger)' }}>
          Failed to load: {error.message}
        </div>
      ) : (
        children
      )}
    </div>
  );
}

function KpiCard({ title, value, accent, subtitle }) {
  return (
    <div className="kpi-card" style={{ borderTopColor: accent || 'var(--border-primary)' }}>
      <div className="kpi-card-title">{title}</div>
      <div className="kpi-card-value">{value ?? '—'}</div>
      {subtitle && <div className="kpi-card-subtitle">{subtitle}</div>}
    </div>
  );
}

export default function Analytics() {
  const [activeTab, setActiveTab] = useState('charts');

  const { data, loading, error, refresh } = useApi(fetchAnalyticsSummary);

  const attendance = data?.attendance || {};
  const fees = data?.fees || {};
  const perf = data?.performance || {};
  const placements = data?.placements || {};
  const trend = data?.attendance_trend || [];
  const coursePerf = data?.course_performance || [];

  // Prepare chart data
  const trendData = trend.map((t) => ({
    month: t.month,
    rate: t.rate,
    sessions: t.total_sessions,
  }));

  const courseData = coursePerf.map((c) => ({
    name: c.course_code || c.course_name?.slice(0, 12),
    attendance: c.avg_attendance_rate,
    marks: c.avg_marks_pct,
  }));

  const feePieData = [
    { name: 'Paid', value: fees.paid_count || 0 },
    { name: 'Partial', value: Math.max((fees.total_records || 0) - (fees.paid_count || 0) - (fees.unpaid_count || 0), 0) },
    { name: 'Unpaid', value: fees.unpaid_count || 0 },
  ].filter((d) => d.value > 0);

  const topCompanies = (placements.top_companies || []).slice(0, 8);
  const companyData = [...topCompanies]
    .reverse()
    .map((c) => ({ name: c.name?.slice(0, 18), placements: c.placements }));

  const overallPct = perf.average_percentage || 0;
  const presentRate = attendance.present_rate || 0;

  return (
    <div className="analytics-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Analytics Dashboard</h2>
            <p className="page-subtitle">
              Deep dive into attendance trends, course performance, fee collection, and placement stats.
            </p>
          </div>
          <div className="page-header-right">
            <button
              className="btn btn-ghost"
              onClick={refresh}
              disabled={loading}
            >
              {loading ? '⏳ Loading...' : '🔄 Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard
          title="📈 Avg Attendance"
          value={loading ? '—' : `${presentRate}%`}
          accent="var(--accent-success)"
        />
        <KpiCard
          title="🎯 Avg Marks"
          value={loading ? '—' : `${overallPct}%`}
          accent="var(--accent-primary)"
        />
        <KpiCard
          title="💼 Total Placements"
          value={loading ? '—' : String(placements.total_placements || 0)}
          subtitle={placements.average_package_lpa ? `Avg: ₹${placements.average_package_lpa}L` : null}
          accent="var(--accent-info)"
        />
        <KpiCard
          title="💰 Collection Rate"
          value={loading ? '—' : `${fees.collection_rate || 0}%`}
          subtitle={fees.outstanding_balance ? `Outstanding: ₹${(fees.outstanding_balance / 100000).toFixed(1)}L` : null}
          accent="var(--accent-warning)"
        />
      </div>

      {/* Tabs */}
      <div className="tabs" role="tablist">
        <button
          className={`tab ${activeTab === 'charts' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'charts'}
          onClick={() => setActiveTab('charts')}
        >
          📊 Charts
        </button>
        <button
          className={`tab ${activeTab === 'courses' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'courses'}
          onClick={() => setActiveTab('courses')}
        >
          🏫 Courses
        </button>
      </div>

      {/* Charts Tab */}
      {activeTab === 'charts' && (
        <div className="tab-content">
          <div className="charts-grid">
            {/* Chart 1: Attendance Trend */}
            <ChartCard title="📈 Attendance Trend (6 months)" loading={loading} error={error}>
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={trendData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--text-tertiary)" />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="var(--text-tertiary)" unit="%" />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="rate"
                      stroke="#89b4fa"
                      strokeWidth={2}
                      dot={{ r: 4, fill: '#89b4fa' }}
                      name="Attendance %"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">No attendance trend data available</div>
              )}
            </ChartCard>

            {/* Chart 2: Fee Collection Donut */}
            <ChartCard title="💰 Fee Collection Status" loading={loading} error={error}>
              {feePieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={feePieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={4}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {feePieData.map((_, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">No fee data available</div>
              )}
            </ChartCard>

            {/* Chart 3: Course Performance Grouped Bar */}
            <ChartCard title="📊 Course Performance" loading={loading} error={error}>
              {courseData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={courseData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="var(--text-tertiary)" />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="var(--text-tertiary)" unit="%" />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Bar dataKey="attendance" fill="#89b4fa" name="Attendance %" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="marks" fill="#a6e3a1" name="Marks %" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">No course performance data available</div>
              )}
            </ChartCard>

            {/* Chart 4: Top Placement Companies Horizontal Bar */}
            <ChartCard title="🎓 Top Placement Companies" loading={loading} error={error}>
              {companyData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart
                    data={companyData}
                    layout="vertical"
                    margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                    <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--text-tertiary)" />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 10 }}
                      stroke="var(--text-tertiary)"
                      width={140}
                    />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="placements" fill="#fab387" name="Placements" radius={[0, 4, 4, 0]}>
                      {companyData.map((_, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">No placement data available</div>
              )}
            </ChartCard>
          </div>
        </div>
      )}

      {/* Courses Tab */}
      {activeTab === 'courses' && (
        <div className="tab-content">
          <div className="section">
            <h3 className="section-title">Course Performance Breakdown</h3>
            <p className="section-description">
              Per-course metrics: attendance rate, marks, fee collection, and placement rates.
            </p>
            {loading ? (
              <SkeletonCard />
            ) : error ? (
              <div className="empty-state"><p>Could not load course data.</p></div>
            ) : courseData.length === 0 ? (
              <div className="empty-state"><p>No course data available.</p></div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Course</th>
                      <th>Students</th>
                      <th>Attendance</th>
                      <th>Marks (avg)</th>
                      <th>Fee Collection</th>
                      <th>Placement Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coursePerf.map((c) => (
                      <tr key={c.course_id}>
                        <td className="cell-primary">
                          {c.course_name}
                          <span className="cell-mono" style={{ marginLeft: '0.5rem' }}>{c.course_code}</span>
                        </td>
                        <td>{c.student_count}</td>
                        <td>
                          <span className={`badge ${c.avg_attendance_rate >= 75 ? 'badge-success' : c.avg_attendance_rate >= 50 ? 'badge-warning' : ''}`}>
                            {c.avg_attendance_rate}%
                          </span>
                        </td>
                        <td>{c.avg_marks_pct}%</td>
                        <td>{c.fee_collection_rate}%</td>
                        <td>{c.placement_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
