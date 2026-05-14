import PropTypes from "prop-types";

export function Card({ label, value }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

Card.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
};

export function ActivityTrendChart({ points }) {
  if (!points || points.length === 0) {
    return <p className="empty-state">Activity trend will appear once live usage starts accumulating.</p>;
  }

  const maxValue = Math.max(
    1,
    ...points.flatMap((point) => [point.incidents_created, point.report_runs, point.schedules_created]),
  );

  return (
    <div className="activity-trend">
      {points.map((point) => (
        <div key={point.day} className="activity-trend__day">
          <div
            className="activity-trend__bars"
            aria-label={`${point.label}: ${point.report_runs} runs, ${point.incidents_created} incidents, ${point.schedules_created} schedules`}
          >
            <span className="activity-trend__bar activity-trend__bar--runs" style={{ height: `${(point.report_runs / maxValue) * 100}%` }} />
            <span
              className="activity-trend__bar activity-trend__bar--incidents"
              style={{ height: `${(point.incidents_created / maxValue) * 100}%` }}
            />
            <span
              className="activity-trend__bar activity-trend__bar--schedules"
              style={{ height: `${(point.schedules_created / maxValue) * 100}%` }}
            />
          </div>
          <span className="hint activity-trend__label">{point.label}</span>
        </div>
      ))}
      <div className="activity-trend__legend hint">
        <span className="activity-trend__legend-item">
          <i className="activity-trend__dot activity-trend__dot--runs" /> Report runs
        </span>
        <span className="activity-trend__legend-item">
          <i className="activity-trend__dot activity-trend__dot--incidents" /> Incidents
        </span>
        <span className="activity-trend__legend-item">
          <i className="activity-trend__dot activity-trend__dot--schedules" /> Schedules
        </span>
      </div>
    </div>
  );
}

ActivityTrendChart.propTypes = {
  points: PropTypes.arrayOf(
    PropTypes.shape({
      day: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      incidents_created: PropTypes.number.isRequired,
      report_runs: PropTypes.number.isRequired,
      schedules_created: PropTypes.number.isRequired,
    }),
  ).isRequired,
};
