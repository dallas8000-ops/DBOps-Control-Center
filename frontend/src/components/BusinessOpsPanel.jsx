import PropTypes from "prop-types";
import { ActivityTrendChart, Card } from "./DashboardWidgets.jsx";
import { formatCurrencyFromCents, formatUtcIsoAsLocal } from "../formatters.js";

export function BusinessOpsPanel({
  adminOverview,
  billingForm,
  setBillingForm,
  billingBusy,
  billingFeedback,
  onSaveBilling,
  onStartBillingCheckout,
}) {
  if (!adminOverview) {
    return (
      <section className="panel">
        <h2 className="panel-title">Business Metrics (DBA)</h2>
        <p className="empty-state">Loading business metrics...</p>
      </section>
    );
  }

  const { metrics, onboarding, plan_usage: planUsage, activity_trend: activityTrend } = adminOverview;

  return (
    <section className="panel">
      <h2 className="panel-title">Business Metrics (DBA)</h2>
      <div className="summary-grid summary-grid--compact">
        <Card label="Active Users" value={`${metrics.active_users}/${metrics.total_users}`} />
        <Card label="Open Incidents" value={metrics.open_incidents} />
        <Card label="Enabled Schedules" value={metrics.enabled_schedules} />
        <Card label="Runs (24h)" value={metrics.report_runs_last_24h} />
      </div>
      <div className="summary-grid summary-grid--compact">
        <Card label="Successful Runs (24h)" value={metrics.successful_report_runs_last_24h} />
        <Card
          label="Onboarding"
          value={`${metrics.onboarding_completed_steps}/${metrics.onboarding_total_steps}`}
        />
        <Card label="Plan" value={billingForm.plan_key || "starter"} />
        <Card label="MRR Scaffold" value={formatCurrencyFromCents(billingForm.monthly_price_cents)} />
      </div>
      <div className="summary-grid summary-grid--compact">
        <Card label="User Seats Left" value={planUsage.user_slots_remaining} />
        <Card label="Schedule Slots Left" value={planUsage.schedule_slots_remaining} />
        <Card label="Billing Status" value={billingForm.billing_status} />
        <Card label="Plan Price" value={formatCurrencyFromCents(billingForm.monthly_price_cents)} />
      </div>

      <h3 className="section-lede">Billing scaffold</h3>
      <button type="button" className="btn btn-primary schedule-submit" onClick={onStartBillingCheckout} disabled={billingBusy}>
        {billingBusy ? "Working..." : "Subscribe with Stripe"}
      </button>
      <form className="form-grid schedule-form" onSubmit={onSaveBilling}>
        <label className="field">
          <span className="field-label">Plan key</span>
          <input
            type="text"
            value={billingForm.plan_key}
            onChange={(e) => setBillingForm({ ...billingForm, plan_key: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Billing status</span>
          <input
            type="text"
            value={billingForm.billing_status}
            onChange={(e) => setBillingForm({ ...billingForm, billing_status: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Monthly price (cents)</span>
          <input
            type="number"
            min="0"
            value={billingForm.monthly_price_cents}
            onChange={(e) => setBillingForm({ ...billingForm, monthly_price_cents: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Max users</span>
          <input
            type="number"
            min="1"
            value={billingForm.max_users}
            onChange={(e) => setBillingForm({ ...billingForm, max_users: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Max schedules</span>
          <input
            type="number"
            min="1"
            value={billingForm.max_schedules}
            onChange={(e) => setBillingForm({ ...billingForm, max_schedules: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Stripe customer ID</span>
          <input
            type="text"
            value={billingForm.stripe_customer_id}
            onChange={(e) => setBillingForm({ ...billingForm, stripe_customer_id: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Stripe subscription ID</span>
          <input
            type="text"
            value={billingForm.stripe_subscription_id}
            onChange={(e) => setBillingForm({ ...billingForm, stripe_subscription_id: e.target.value })}
          />
        </label>
        <button type="submit" className="btn btn-primary schedule-submit" disabled={billingBusy}>
          {billingBusy ? "Saving…" : "Save billing settings"}
        </button>
      </form>
      {billingFeedback ? <p className="hint">{billingFeedback}</p> : null}

      <h3 className="section-lede">Activity trend (last 7 days)</h3>
      <ActivityTrendChart points={activityTrend} />

      <h3 className="section-lede">Onboarding progress</h3>
      <div className="onboarding-list">
        {onboarding.map((item) => (
          <div key={item.key} className={`onboarding-item ${item.completed ? "onboarding-item--done" : ""}`}>
            <strong>{item.completed ? "Done" : "Pending"}</strong> {item.label}
            {item.completed_at ? <span className="hint"> · {formatUtcIsoAsLocal(item.completed_at)}</span> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

BusinessOpsPanel.propTypes = {
  adminOverview: PropTypes.object,
  billingForm: PropTypes.object.isRequired,
  setBillingForm: PropTypes.func.isRequired,
  billingBusy: PropTypes.bool.isRequired,
  billingFeedback: PropTypes.string.isRequired,
  onSaveBilling: PropTypes.func.isRequired,
  onStartBillingCheckout: PropTypes.func.isRequired,
};
