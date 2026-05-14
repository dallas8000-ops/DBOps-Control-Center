import { Fragment } from "react";
import PropTypes from "prop-types";

function IncidentResolveCell({ incident, canResolve, onResolve }) {
  if (incident.status === "open" && canResolve) {
    return (
      <button type="button" className="btn btn-primary" onClick={() => onResolve(incident.id)}>
        Resolve
      </button>
    );
  }
  if (incident.status === "open") {
    return <span className="pill-muted">DBA only</span>;
  }
  return "Closed";
}

IncidentResolveCell.propTypes = {
  incident: PropTypes.shape({
    id: PropTypes.number.isRequired,
    status: PropTypes.string.isRequired,
  }).isRequired,
  canResolve: PropTypes.bool.isRequired,
  onResolve: PropTypes.func.isRequired,
};

export function IncidentsSection({
  incidents,
  incidentFilters,
  onIncidentFilterChange,
  onClearIncidentFilters,
  canEditIncidents,
  editingIncidentId,
  incidentEditForm,
  incidentEditError,
  onStartIncidentEdit,
  onChangeIncidentEditField,
  onSaveIncidentEdit,
  onCancelIncidentEdit,
  canResolve,
  onResolveIncident,
  incidentHistoryOpenId,
  incidentHistoryLoading,
  incidentHistoryEntries,
  incidentHistoryError,
  onToggleIncidentHistory,
  onDownloadIncidentHistoryCsv,
}) {
  function formatIncidentDue(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
    } catch {
      return "—";
    }
  }

  function renderEditActions(incident) {
    if (!canEditIncidents) return null;
    if (editingIncidentId !== incident.id) {
      return (
        <button type="button" className="btn btn-ghost" onClick={() => onStartIncidentEdit(incident)}>
          Edit
        </button>
      );
    }
    return (
      <>
        <button type="button" className="btn btn-primary" onClick={() => onSaveIncidentEdit(incident.id)}>
          Save
        </button>
        <button type="button" className="btn btn-ghost" onClick={onCancelIncidentEdit}>
          Cancel
        </button>
      </>
    );
  }

  return (
    <section className="stack-gap">
      <h2 className="panel-title">Incidents</h2>
      <div className="incident-filters">
        <input
          type="text"
          placeholder="Search title, description, owner"
          value={incidentFilters.search}
          onChange={(e) => onIncidentFilterChange("search", e.target.value)}
        />
        <select value={incidentFilters.status} onChange={(e) => onIncidentFilterChange("status", e.target.value)}>
          <option value="">All status</option>
          <option value="open">open</option>
          <option value="resolved">resolved</option>
        </select>
        <select value={incidentFilters.severity} onChange={(e) => onIncidentFilterChange("severity", e.target.value)}>
          <option value="">All severity</option>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>
        <input
          type="text"
          placeholder="Owner contains"
          value={incidentFilters.owner}
          onChange={(e) => onIncidentFilterChange("owner", e.target.value)}
        />
        <input
          type="date"
          value={incidentFilters.startDate}
          onChange={(e) => onIncidentFilterChange("startDate", e.target.value)}
        />
        <input
          type="date"
          value={incidentFilters.endDate}
          onChange={(e) => onIncidentFilterChange("endDate", e.target.value)}
        />
        <select value={incidentFilters.sort} onChange={(e) => onIncidentFilterChange("sort", e.target.value)}>
          <option value="newest">Sort: newest</option>
          <option value="oldest">Sort: oldest</option>
          <option value="severity">Sort: severity</option>
        </select>
        <label className="incident-filter-overdue">
          <input
            type="checkbox"
            checked={Boolean(incidentFilters.overdue)}
            onChange={(e) => onIncidentFilterChange("overdue", e.target.checked)}
          />{" "}
          Overdue (open)
        </label>
        <button type="button" className="btn btn-ghost" onClick={onClearIncidentFilters}>
          Clear filters
        </button>
      </div>
      {incidents.length === 0 ? (
        <p className="empty-state">No incidents yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Description</th>
                <th>Severity</th>
                <th>Owner</th>
                <th>Due</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => (
                <Fragment key={incident.id}>
                  <tr>
                    <td>
                      {editingIncidentId === incident.id ? (
                        <input
                          className="inline-input"
                          value={incidentEditForm.title}
                          onChange={(e) => onChangeIncidentEditField("title", e.target.value)}
                        />
                      ) : (
                        incident.title
                      )}
                    </td>
                    <td>
                      {editingIncidentId === incident.id ? (
                        <input
                          className="inline-input"
                          value={incidentEditForm.description}
                          onChange={(e) => onChangeIncidentEditField("description", e.target.value)}
                        />
                      ) : (
                        incident.description
                      )}
                    </td>
                    <td>
                      {editingIncidentId === incident.id ? (
                        <select
                          className="inline-input"
                          value={incidentEditForm.severity}
                          onChange={(e) => onChangeIncidentEditField("severity", e.target.value)}
                        >
                          <option value="low">low</option>
                          <option value="medium">medium</option>
                          <option value="high">high</option>
                        </select>
                      ) : (
                        incident.severity
                      )}
                    </td>
                    <td>
                      {editingIncidentId === incident.id ? (
                        <input
                          className="inline-input"
                          value={incidentEditForm.owner}
                          onChange={(e) => onChangeIncidentEditField("owner", e.target.value)}
                        />
                      ) : (
                        incident.owner
                      )}
                    </td>
                    <td>
                      {editingIncidentId === incident.id ? (
                        <input
                          type="datetime-local"
                          className="inline-input"
                          value={incidentEditForm.dueAt}
                          onChange={(e) => onChangeIncidentEditField("dueAt", e.target.value)}
                        />
                      ) : (
                        formatIncidentDue(incident.due_at)
                      )}
                    </td>
                    <td>{incident.status}</td>
                    <td>
                      <div className="action-row">
                        <IncidentResolveCell incident={incident} canResolve={canResolve} onResolve={onResolveIncident} />
                        <button
                          type="button"
                          className="btn btn-ghost"
                          onClick={() => {
                            onToggleIncidentHistory(incident.id).catch(() => {});
                          }}
                        >
                          {incidentHistoryOpenId === incident.id ? "Hide history" : "History"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          onClick={() => {
                            onDownloadIncidentHistoryCsv(incident.id).catch(() => {});
                          }}
                        >
                          History CSV
                        </button>
                        {renderEditActions(incident)}
                      </div>
                    </td>
                  </tr>
                  {incidentHistoryOpenId === incident.id ? (
                    <tr className="incident-history-row">
                      <td colSpan={7}>
                        <div className="incident-history-panel">
                          {incidentHistoryLoading ? <p className="empty-state">Loading history…</p> : null}
                          {incidentHistoryError ? <p className="error-text">{incidentHistoryError}</p> : null}
                          {!incidentHistoryLoading && !incidentHistoryError && incidentHistoryEntries.length === 0 ? (
                            <p className="empty-state">No history entries yet.</p>
                          ) : null}
                          {!incidentHistoryLoading && incidentHistoryEntries.length > 0 ? (
                            <table className="incident-history-table">
                              <thead>
                                <tr>
                                  <th>When</th>
                                  <th>Actor</th>
                                  <th>Action</th>
                                  <th>Details</th>
                                </tr>
                              </thead>
                              <tbody>
                                {incidentHistoryEntries.map((entry) => (
                                  <tr key={entry.id}>
                                    <td>
                                      {entry.created_at
                                        ? new Date(entry.created_at).toLocaleString(undefined, {
                                            dateStyle: "short",
                                            timeStyle: "short",
                                          })
                                        : "—"}
                                    </td>
                                    <td>{entry.actor_email ? entry.actor_email : "—"}</td>
                                    <td>{entry.action}</td>
                                    <td>
                                      <div className="incident-history-json">
                                        {JSON.stringify(entry.details, null, 2)}
                                      </div>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {incidentEditError ? <p className="error-text">{incidentEditError}</p> : null}
    </section>
  );
}

IncidentsSection.propTypes = {
  incidents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      title: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      severity: PropTypes.string.isRequired,
      owner: PropTypes.string.isRequired,
      status: PropTypes.string.isRequired,
      due_at: PropTypes.string,
    }),
  ).isRequired,
  incidentFilters: PropTypes.shape({
    search: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    severity: PropTypes.string.isRequired,
    owner: PropTypes.string.isRequired,
    startDate: PropTypes.string.isRequired,
    endDate: PropTypes.string.isRequired,
    sort: PropTypes.string.isRequired,
    overdue: PropTypes.bool.isRequired,
  }).isRequired,
  onIncidentFilterChange: PropTypes.func.isRequired,
  onClearIncidentFilters: PropTypes.func.isRequired,
  canEditIncidents: PropTypes.bool.isRequired,
  editingIncidentId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  incidentEditForm: PropTypes.shape({
    title: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    severity: PropTypes.string.isRequired,
    owner: PropTypes.string.isRequired,
    dueAt: PropTypes.string.isRequired,
  }).isRequired,
  incidentEditError: PropTypes.string.isRequired,
  onStartIncidentEdit: PropTypes.func.isRequired,
  onChangeIncidentEditField: PropTypes.func.isRequired,
  onSaveIncidentEdit: PropTypes.func.isRequired,
  onCancelIncidentEdit: PropTypes.func.isRequired,
  canResolve: PropTypes.bool.isRequired,
  onResolveIncident: PropTypes.func.isRequired,
  incidentHistoryOpenId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  incidentHistoryLoading: PropTypes.bool.isRequired,
  incidentHistoryEntries: PropTypes.arrayOf(PropTypes.object).isRequired,
  incidentHistoryError: PropTypes.string.isRequired,
  onToggleIncidentHistory: PropTypes.func.isRequired,
  onDownloadIncidentHistoryCsv: PropTypes.func.isRequired,
};
