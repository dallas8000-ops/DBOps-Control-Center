import { Fragment, useEffect, useState } from "react";
import PropTypes from "prop-types";

const INCIDENT_CARD_DENSITY_KEY = "dbops_incident_card_density";
const INCIDENT_FILTER_PRESETS_KEY_PREFIX = "dbops_incident_filter_presets";
const INCIDENT_FILTER_FIELDS = ["search", "status", "severity", "owner", "startDate", "endDate", "sort", "overdue"];

function normalizePresetFilters(raw) {
  return {
    search: String(raw?.search ?? ""),
    status: String(raw?.status ?? ""),
    severity: String(raw?.severity ?? ""),
    owner: String(raw?.owner ?? ""),
    startDate: String(raw?.startDate ?? ""),
    endDate: String(raw?.endDate ?? ""),
    sort: String(raw?.sort ?? "newest"),
    overdue: Boolean(raw?.overdue),
  };
}

function presetStorageKeyForUser(userKey = "") {
  const safe = String(userKey || "anonymous").trim().toLowerCase() || "anonymous";
  return `${INCIDENT_FILTER_PRESETS_KEY_PREFIX}:${safe}`;
}

function formatIncidentDue(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
  } catch {
    return "-";
  }
}

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
  onAddIncidentComment,
  hasActiveFilters,
  canCreateIncident,
  presetStorageKey,
  currentUserEmail,
  bulkActionBusy,
  onBulkIncidentAction,
}) {
  const canUseBulkSelection = canEditIncidents || canResolve;

  function canSelectIncident(incident) {
    return canUseBulkSelection && incident.status === "open";
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

  let emptyMessage = "No incidents available yet. Ask a DBA or Analyst to create one so you can monitor status and trends.";
  if (hasActiveFilters) {
    emptyMessage = "No incidents match the current filters. Clear filters or broaden your search to continue.";
  } else if (canCreateIncident) {
    emptyMessage = "No incidents yet. Start by creating your first incident to unlock trend and SLA tracking.";
  }

  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [mobileDensity, setMobileDensity] = useState(() => {
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.getItem !== "function") return "comfortable";
    const raw = store.getItem(INCIDENT_CARD_DENSITY_KEY);
    return raw === "compact" ? "compact" : "comfortable";
  });
  const [presets, setPresets] = useState([]);
  const [selectedPresetName, setSelectedPresetName] = useState("");
  const [newPresetName, setNewPresetName] = useState("");
  const [selectedIncidentIds, setSelectedIncidentIds] = useState([]);
  const [bulkAssignOwner, setBulkAssignOwner] = useState("");
  const [commentDraft, setCommentDraft] = useState("");
  const [commentBusy, setCommentBusy] = useState(false);
  const [commentError, setCommentError] = useState("");

  const userPresetStorageKey = presetStorageKeyForUser(presetStorageKey);

  const hasAdvancedFilters = Boolean(
    incidentFilters.status ||
      incidentFilters.severity ||
      incidentFilters.owner ||
      incidentFilters.startDate ||
      incidentFilters.endDate ||
      incidentFilters.overdue,
  );

  useEffect(() => {
    if (hasAdvancedFilters) {
      setShowAdvancedFilters(true);
    }
  }, [hasAdvancedFilters]);

  useEffect(() => {
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.setItem !== "function") return;
    store.setItem(INCIDENT_CARD_DENSITY_KEY, mobileDensity);
  }, [mobileDensity]);

  useEffect(() => {
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.getItem !== "function") {
      setPresets([]);
      setSelectedPresetName("");
      return;
    }
    const raw = store.getItem(userPresetStorageKey);
    if (!raw) {
      setPresets([]);
      setSelectedPresetName("");
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      const normalized = Array.isArray(parsed)
        ? parsed
            .filter((item) => item && typeof item.name === "string")
            .map((item) => ({
              name: item.name,
              filters: normalizePresetFilters(item.filters),
            }))
        : [];
      setPresets(normalized);
      setSelectedPresetName((prev) =>
        prev && normalized.some((item) => item.name === prev) ? prev : "",
      );
    } catch {
      setPresets([]);
      setSelectedPresetName("");
    }
  }, [userPresetStorageKey]);

  function persistPresets(nextPresets) {
    setPresets(nextPresets);
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.setItem !== "function") return;
    store.setItem(userPresetStorageKey, JSON.stringify(nextPresets));
  }

  function applyPresetByName(name) {
    const preset = presets.find((item) => item.name === name);
    if (!preset) return;
    const nextFilters = normalizePresetFilters(preset.filters);
    INCIDENT_FILTER_FIELDS.forEach((field) => {
      onIncidentFilterChange(field, nextFilters[field]);
    });
    setShowAdvancedFilters(true);
  }

  function saveCurrentAsPreset() {
    const name = newPresetName.trim();
    if (!name) return;
    const nextEntry = {
      name,
      filters: normalizePresetFilters(incidentFilters),
    };
    const nextPresets = [...presets.filter((item) => item.name.toLowerCase() !== name.toLowerCase()), nextEntry]
      .sort((a, b) => a.name.localeCompare(b.name));
    persistPresets(nextPresets);
    setSelectedPresetName(name);
    setNewPresetName("");
  }

  function deleteSelectedPreset() {
    if (!selectedPresetName) return;
    const nextPresets = presets.filter((item) => item.name !== selectedPresetName);
    persistPresets(nextPresets);
    setSelectedPresetName("");
  }

  const eligibleIncidentIdsKey = incidents
    .filter((incident) => canSelectIncident(incident))
    .map((incident) => incident.id)
    .join(",");
  const eligibleIncidentIds = eligibleIncidentIdsKey
    ? eligibleIncidentIdsKey.split(",").map(Number)
    : [];
  const eligibleIncidentIdSet = new Set(eligibleIncidentIds);
  const selectedEligibleCount = selectedIncidentIds.filter((id) => eligibleIncidentIdSet.has(id)).length;
  const allEligibleSelected = eligibleIncidentIds.length > 0 && selectedEligibleCount === eligibleIncidentIds.length;

  useEffect(() => {
    if (!canUseBulkSelection) {
      setSelectedIncidentIds((prev) => (prev.length === 0 ? prev : []));
      return;
    }

    const eligibleIdSet = new Set(eligibleIncidentIds);
    setSelectedIncidentIds((prev) => {
      const next = prev.filter((id) => eligibleIdSet.has(id));
      if (next.length === prev.length && next.every((id, index) => id === prev[index])) {
        return prev;
      }
      return next;
    });
  }, [canUseBulkSelection, eligibleIncidentIdsKey]);

  useEffect(() => {
    setCommentDraft("");
    setCommentError("");
    setCommentBusy(false);
  }, [incidentHistoryOpenId]);

  function toggleIncidentSelected(incidentId, nextChecked) {
    setSelectedIncidentIds((prev) => {
      if (nextChecked) {
        if (prev.includes(incidentId)) return prev;
        return [...prev, incidentId];
      }
      return prev.filter((id) => id !== incidentId);
    });
  }

  function toggleSelectAllEligible(nextChecked) {
    if (!nextChecked) {
      setSelectedIncidentIds([]);
      return;
    }
    setSelectedIncidentIds(eligibleIncidentIds);
  }

  async function runBulkAction(action, ownerOverride = "") {
    if (selectedIncidentIds.length === 0 || typeof onBulkIncidentAction !== "function") return;
    const ownerValue = ownerOverride || bulkAssignOwner;
    const payload = action === "assign" ? { owner: ownerValue.trim() } : {};
    const ok = await onBulkIncidentAction({ action, incidentIds: selectedIncidentIds, ...payload });
    if (!ok) return;
    setSelectedIncidentIds([]);
    if (action === "assign") {
      setBulkAssignOwner("");
    }
  }

  async function submitIncidentComment() {
    if (!incidentHistoryOpenId || typeof onAddIncidentComment !== "function") return;
    const comment = commentDraft.trim();
    if (!comment) {
      setCommentError("Enter a comment before posting.");
      return;
    }
    setCommentBusy(true);
    setCommentError("");
    const result = await onAddIncidentComment(incidentHistoryOpenId, comment);
    setCommentBusy(false);
    if (!result?.ok) {
      setCommentError("Comment could not be saved. Please try again.");
      return;
    }
    setCommentDraft("");
  }

  return (
    <section className="stack-gap">
      <h2 className="panel-title">Incidents</h2>
      <div className="incident-filter-toolbar">
        <input
          type="text"
          placeholder="Search title, description, owner"
          value={incidentFilters.search}
          onChange={(e) => onIncidentFilterChange("search", e.target.value)}
        />
        <button
          type="button"
          className="btn btn-ghost incident-filter-toggle"
          onClick={() => setShowAdvancedFilters((prev) => !prev)}
        >
          {showAdvancedFilters ? "Hide filters" : "Show filters"}
          {hasAdvancedFilters ? " (active)" : ""}
        </button>
        <button
          type="button"
          className="btn btn-ghost incident-density-toggle"
          onClick={() => setMobileDensity((prev) => (prev === "comfortable" ? "compact" : "comfortable"))}
        >
          Density: {mobileDensity}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onClearIncidentFilters}>
          Clear filters
        </button>
      </div>
      <div className="incident-preset-row">
        <select
          value={selectedPresetName}
          onChange={(e) => setSelectedPresetName(e.target.value)}
          aria-label="Filter preset"
        >
          <option value="">Filter presets</option>
          {presets.map((preset) => (
            <option key={preset.name} value={preset.name}>
              {preset.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!selectedPresetName}
          onClick={() => applyPresetByName(selectedPresetName)}
        >
          Apply preset
        </button>
        <input
          type="text"
          placeholder="Save current as..."
          value={newPresetName}
          onChange={(e) => setNewPresetName(e.target.value)}
        />
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!newPresetName.trim()}
          onClick={saveCurrentAsPreset}
        >
          Save preset
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!selectedPresetName}
          onClick={deleteSelectedPreset}
        >
          Delete preset
        </button>
      </div>
      <div className={`incident-filters ${showAdvancedFilters ? "" : "incident-filters--collapsed"}`}>
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
      </div>
      {canUseBulkSelection ? (
        <div className="incident-bulk-summary">
          <span>
            <strong>{selectedEligibleCount}</strong> selected of <strong>{eligibleIncidentIds.length}</strong> eligible incidents.
          </span>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={selectedIncidentIds.length === 0}
            onClick={() => setSelectedIncidentIds([])}
          >
            Clear selection
          </button>
        </div>
      ) : null}
      {canUseBulkSelection ? (
        <div className="incident-quick-actions">
          <button
            type="button"
            className="btn btn-ghost"
            disabled={bulkActionBusy || selectedIncidentIds.length === 0 || typeof onBulkIncidentAction !== "function"}
            onClick={() => {
              runBulkAction("acknowledge").catch(() => {});
            }}
          >
            Acknowledge selected
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={bulkActionBusy || selectedIncidentIds.length === 0 || typeof onBulkIncidentAction !== "function"}
            onClick={() => {
              runBulkAction("escalate").catch(() => {});
            }}
          >
            Escalate selected
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              bulkActionBusy ||
              selectedIncidentIds.length === 0 ||
              !canResolve ||
              typeof onBulkIncidentAction !== "function"
            }
            onClick={() => {
              runBulkAction("resolve").catch(() => {});
            }}
          >
            Resolve selected
          </button>
          <div className="incident-quick-actions__assign">
            <input
              type="text"
              placeholder="Assign owner"
              value={bulkAssignOwner}
              onChange={(e) => setBulkAssignOwner(e.target.value)}
            />
            <button
              type="button"
              className="btn btn-ghost"
              disabled={
                bulkActionBusy ||
                selectedIncidentIds.length === 0 ||
                !bulkAssignOwner.trim() ||
                typeof onBulkIncidentAction !== "function"
              }
              onClick={() => {
                runBulkAction("assign").catch(() => {});
              }}
            >
              Assign selected
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={
                bulkActionBusy ||
                selectedIncidentIds.length === 0 ||
                !currentUserEmail ||
                typeof onBulkIncidentAction !== "function"
              }
              onClick={() => {
                runBulkAction("assign", currentUserEmail || "").catch(() => {});
              }}
            >
              Assign to me
            </button>
          </div>
        </div>
      ) : null}
      {incidents.length === 0 ? (
        <p className="empty-state">{emptyMessage}</p>
      ) : (
        <div className="table-scroll">
          <table className={`data-table mobile-card-table mobile-card-table--${mobileDensity}`}>
            <thead>
              <tr>
                {canUseBulkSelection ? (
                  <th className="incident-select-col">
                    <label className="incident-select-all">
                      <input
                        type="checkbox"
                        aria-label="Select all eligible incidents"
                        checked={allEligibleSelected}
                        disabled={eligibleIncidentIds.length === 0}
                        onChange={(e) => toggleSelectAllEligible(e.target.checked)}
                      />
                      <span>Select</span>
                    </label>
                  </th>
                ) : null}
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
                    {canUseBulkSelection ? (
                      <td data-label="Select">
                        <input
                          type="checkbox"
                          aria-label={`Select incident ${incident.id}`}
                          checked={selectedIncidentIds.includes(incident.id)}
                          disabled={!canSelectIncident(incident)}
                          onChange={(e) => toggleIncidentSelected(incident.id, e.target.checked)}
                        />
                      </td>
                    ) : null}
                    <td data-label="Title">
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
                    <td data-label="Description">
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
                    <td data-label="Severity">
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
                    <td data-label="Owner">
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
                    <td data-label="Due">
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
                    <td data-label="Status">{incident.status}</td>
                    <td data-label="Action">
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
                      <td colSpan={canUseBulkSelection ? 8 : 7}>
                        <div className="incident-history-panel">
                          {incidentHistoryLoading ? <p className="empty-state">Loading history...</p> : null}
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
                                        : "-"}
                                    </td>
                                    <td>{entry.actor_email ? entry.actor_email : "-"}</td>
                                    <td>{entry.action}</td>
                                    <td>
                                      {entry.action === "commented" && entry.details?.comment ? (
                                        <div className="incident-history-comment">
                                          <strong>Comment</strong>
                                          <div>{entry.details.comment}</div>
                                        </div>
                                      ) : (
                                        <div className="incident-history-json">
                                          {JSON.stringify(entry.details, null, 2)}
                                        </div>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : null}
                          {!incidentHistoryLoading && !incidentHistoryError && incidentHistoryOpenId && typeof onAddIncidentComment === "function" ? (
                            <div className="incident-comment-composer">
                              <h4 className="section-lede">Add a comment</h4>
                              <textarea
                                placeholder="Write a handoff note, follow-up, or context update..."
                                value={commentDraft}
                                onChange={(e) => setCommentDraft(e.target.value)}
                              />
                              {commentError ? <p className="error-text">{commentError}</p> : null}
                              <div className="action-row">
                                <button
                                  type="button"
                                  className="btn btn-primary"
                                  disabled={commentBusy}
                                  onClick={() => {
                                    submitIncidentComment().catch(() => {});
                                  }}
                                >
                                  {commentBusy ? "Posting..." : "Post comment"}
                                </button>
                              </div>
                            </div>
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
  onAddIncidentComment: PropTypes.func,
  hasActiveFilters: PropTypes.bool,
  canCreateIncident: PropTypes.bool,
  presetStorageKey: PropTypes.string,
  currentUserEmail: PropTypes.string,
  bulkActionBusy: PropTypes.bool,
  onBulkIncidentAction: PropTypes.func,
};
