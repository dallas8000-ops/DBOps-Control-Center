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

export function ReportRunsTrendChart({ runs }) {
  if (!runs || runs.length === 0) {
    return (
      <p className="empty-state">
        No report history yet. Run a report to unlock daily success/failure trend insights.
      </p>
    );
  }

  const buckets = new Map();
  runs.forEach((run) => {
    const raw = String(run.created_at || "");
    const day = raw.slice(0, 10) || "unknown";
    if (!buckets.has(day)) {
      buckets.set(day, { day, success: 0, failed: 0 });
    }
    const bucket = buckets.get(day);
    if (run.success) {
      bucket.success += 1;
    } else {
      bucket.failed += 1;
    }
  });

  const points = Array.from(buckets.values())
    .sort((a, b) => b.day.localeCompare(a.day))
    .slice(0, 7)
    .reverse()
    .map((p) => ({
      ...p,
      label: p.day.slice(5),
    }));

  const maxValue = Math.max(1, ...points.flatMap((point) => [point.success, point.failed]));

  return (
    <div className="activity-trend report-runs-trend">
      {points.map((point) => (
        <div key={point.day} className="activity-trend__day">
          <div
            className="activity-trend__bars"
            aria-label={`${point.day}: ${point.success} successful runs, ${point.failed} failed runs`}
          >
            <span
              className="activity-trend__bar activity-trend__bar--runs"
              style={{ height: `${(point.success / maxValue) * 100}%` }}
            />
            <span
              className="activity-trend__bar activity-trend__bar--incidents"
              style={{ height: `${(point.failed / maxValue) * 100}%` }}
            />
          </div>
          <span className="hint activity-trend__label">{point.label}</span>
        </div>
      ))}
      <div className="activity-trend__legend hint">
        <span className="activity-trend__legend-item">
          <i className="activity-trend__dot activity-trend__dot--runs" /> Successful runs
        </span>
        <span className="activity-trend__legend-item">
          <i className="activity-trend__dot activity-trend__dot--incidents" /> Failed runs
        </span>
      </div>
    </div>
  );
}

ReportRunsTrendChart.propTypes = {
  runs: PropTypes.arrayOf(
    PropTypes.shape({
      created_at: PropTypes.string,
      success: PropTypes.bool,
    }),
  ).isRequired,
};

export function SlaStatusWidget({ openIncidents, overdueIncidents, incidentsWithSla }) {
  const onTrack = Math.max(incidentsWithSla - overdueIncidents, 0);
  const noSla = Math.max(openIncidents - incidentsWithSla, 0);
  const healthPct = incidentsWithSla === 0 ? 100 : Math.round((onTrack / incidentsWithSla) * 100);
  const isBreach = overdueIncidents > 0;

  if (openIncidents === 0) {
    return <p className="empty-state">No open incidents — SLA health is perfect.</p>;
  }

  return (
    <div className="sla-widget">
      <div className="sla-widget__badges">
        <div className={`sla-widget__badge ${isBreach ? "sla-widget__badge--breach" : "sla-widget__badge--ok"}`}>
          <span className="sla-widget__count">{overdueIncidents}</span>
          <span className="sla-widget__label">Overdue</span>
        </div>
        <div className="sla-widget__badge sla-widget__badge--ok">
          <span className="sla-widget__count">{onTrack}</span>
          <span className="sla-widget__label">On track</span>
        </div>
        <div className="sla-widget__badge">
          <span className="sla-widget__count">{noSla}</span>
          <span className="sla-widget__label">No SLA set</span>
        </div>
      </div>
      {incidentsWithSla > 0 && (
        <div className="sla-widget__bar-wrap">
          <div className="sla-widget__bar" aria-label={`SLA health ${healthPct}%`}>
            <div
              className={`sla-widget__bar-fill ${isBreach ? "sla-widget__bar-fill--breach" : ""}`}
              style={{ width: `${healthPct}%` }}
            />
          </div>
          <span className="hint">{healthPct}% of tracked incidents on track</span>
        </div>
      )}
    </div>
  );
}

SlaStatusWidget.propTypes = {
  openIncidents: PropTypes.number.isRequired,
  overdueIncidents: PropTypes.number.isRequired,
  incidentsWithSla: PropTypes.number.isRequired,
};
