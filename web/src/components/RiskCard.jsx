import { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { fetchRiskExplanation } from '../api/client';

function RiskLevelBadge({ level }) {
  const cls = level === 'High' ? 'risk-badge-high'
    : level === 'Medium' ? 'risk-badge-medium'
    : level === 'Low' ? 'risk-badge-low'
    : 'risk-badge-none';
  return <span className={`risk-badge ${cls}`}>{level}</span>;
}

function RiskGauge({ score }) {
  const pct = Math.min(score * 100, 100);
  const color = pct >= 70 ? 'var(--risk-high)' : pct >= 40 ? 'var(--risk-medium)' : 'var(--risk-low)';
  return (
    <div className="risk-gauge">
      <svg viewBox="0 0 36 36" className="risk-gauge-svg">
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="var(--border-primary)"
          strokeWidth="3"
        />
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeDasharray={`${pct}, 100`}
          strokeLinecap="round"
        />
      </svg>
      <div className="risk-gauge-text">
        <span className="risk-gauge-value" style={{ color }}>{Math.round(pct)}%</span>
      </div>
    </div>
  );
}

function ExplanationBar({ explanation }) {
  const direction = explanation.direction === 'increases' ? 1 : -1;
  const barWidth = Math.min(Math.abs(explanation.importance) * 100, 100);
  const color = direction > 0 ? 'var(--accent-danger)' : 'var(--accent-success)';

  return (
    <div className="explanation-bar">
      <div className="explanation-bar-header">
        <span className="explanation-bar-label">{explanation.label}</span>
        <span className="explanation-bar-value">{explanation.value}</span>
      </div>
      <div className="explanation-bar-track">
        <div
          className="explanation-bar-fill"
          style={{
            width: `${barWidth}%`,
            backgroundColor: color,
            alignSelf: direction > 0 ? 'flex-start' : 'flex-end',
          }}
        />
      </div>
      <div className="explanation-bar-impact">
        {direction > 0 ? '↑ Increases risk' : '↓ Decreases risk'} ({explanation.importance.toFixed(3)})
      </div>
    </div>
  );
}

export default function RiskCard({ studentId, studentName }) {
  const [expanded, setExpanded] = useState(false);
  const hasFetched = useRef(false);
  const { data, loading, error, execute } = useApi(
    () => fetchRiskExplanation(studentId),
    [studentId],
    { immediate: false }
  );

  const handleToggle = () => {
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);
    if (nextExpanded && !hasFetched.current) {
      hasFetched.current = true;
      execute();
    }
  };

  // Re-fetch if studentId changes while expanded
  useEffect(() => {
    if (expanded) {
      hasFetched.current = true;
      execute();
    }
  }, [studentId]); // eslint-disable-line react-hooks/exhaustive-deps

  const showData = expanded && data;

  return (
    <div className="risk-card">
      <button
        className="risk-card-header"
        onClick={handleToggle}
        aria-expanded={expanded}
        aria-controls={`risk-detail-${studentId}`}
      >
        <div className="risk-card-title">
          <span className="risk-card-name">{studentName}</span>
          {data && <RiskLevelBadge level={data.risk_level} />}
        </div>
        <span className="risk-card-toggle">{expanded ? '−' : '+'}</span>
      </button>

      {loading && expanded && (
        <div className="risk-card-loading">
          <div className="skeleton" style={{ width: '100%', height: '4rem' }} />
        </div>
      )}

      {error && expanded && (
        <div className="risk-card-error">
          Failed to load explanation: {error.message}
        </div>
      )}

      {showData && (
        <div className="risk-card-body" id={`risk-detail-${studentId}`}>
          <div className="risk-card-gauge-row">
            <RiskGauge score={data.risk_score} />
            <div className="risk-card-meta">
              <div className="risk-card-meta-item">
                <span className="risk-card-meta-label">Risk Score</span>
                <span className="risk-card-meta-value">{data.risk_score.toFixed(4)}</span>
              </div>
              <div className="risk-card-meta-item">
                <span className="risk-card-meta-label">Model</span>
                <span className="risk-card-meta-value">{data.model || 'heuristic'}</span>
              </div>
            </div>
          </div>

          <div className="risk-card-explanations">
            <h4 className="risk-card-explanations-title">Why this student is at risk</h4>
            {data.explanations && data.explanations.length > 0 ? (
              data.explanations.map((exp, i) => (
                <ExplanationBar key={i} explanation={exp} />
              ))
            ) : (
              <p className="risk-card-no-data">No explanation data available.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
