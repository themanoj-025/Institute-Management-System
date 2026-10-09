export function Skeleton({ width, height, rounded = false, className = '' }) {
  return (
    <div
      className={`skeleton ${rounded ? 'skeleton-rounded' : ''} ${className}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <Skeleton height="1.25rem" width="60%" />
      <Skeleton height="2rem" width="40%" className="skeleton-mt-3" />
      <Skeleton height="0.75rem" width="80%" className="skeleton-mt-2" />
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="skeleton-table">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} height="1rem" width={`${50 + Math.random() * 40}%`} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton-chart">
      <Skeleton height="1rem" width="30%" />
      <div className="skeleton-chart-bars">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton
            key={i}
            width="100%"
            height={`${3 + Math.random() * 6}rem`}
            className="skeleton-chart-bar"
          />
        ))}
      </div>
    </div>
  );
}
