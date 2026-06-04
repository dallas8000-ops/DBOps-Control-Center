import { useEffect, useRef } from "react";

const FEATURES = [
  {
    icon: "🔐",
    title: "Role-Based Access Control",
    desc: "Define exactly who can read, write, or execute. Granular permissions for every team member — DBA, Analyst, or Viewer.",
  },
  {
    icon: "🚨",
    title: "Incident Management",
    desc: "Detect, log, and resolve database incidents with built-in escalation workflows, bulk actions, and real-time notifications.",
  },
  {
    icon: "📋",
    title: "Audited SQL Reporting",
    desc: "Every query logged with timestamp, user, and result. Full compliance-ready audit trail with CSV export out of the box.",
  },
  {
    icon: "📊",
    title: "Business Metrics Dashboard",
    desc: "Real-time visibility into active users, open incidents, schedule runs, and MRR in a single DBA control panel.",
  },
  {
    icon: "⏰",
    title: "Scheduled Reports",
    desc: "Run approved reports automatically on daily or weekly cadence. Route results via email or webhook with notify-on-failure.",
  },
  {
    icon: "🤖",
    title: "AI Operations Assist",
    desc: "Natural language to report routing and incident handoff summaries — safe by design, mapped only to approved queries.",
  },
];

const PLANS = [
  {
    tier: "Starter",
    price: "$79",
    period: "10 users · 10 schedules",
    features: [
      { text: "Up to 10 users", ok: true },
      { text: "10 scheduled reports", ok: true },
      { text: "Incident management", ok: true },
      { text: "Report audit trail", ok: true },
      { text: "Google SSO login", ok: true },
      { text: "Unlimited schedules", ok: false },
      { text: "Priority support", ok: false },
    ],
    cta: "Start Free Trial",
    featured: false,
  },
  {
    tier: "Pro",
    price: "$149",
    period: "Up to 5,000 users · 5,000 schedules",
    features: [
      { text: "Up to 5,000 users", ok: true },
      { text: "Up to 5,000 scheduled reports", ok: true },
      { text: "Full incident workflows", ok: true },
      { text: "Report audit trail + CSV", ok: true },
      { text: "Google SSO + RBAC", ok: true },
      { text: "Bulk incident actions", ok: true },
      { text: "Custom SLA", ok: false },
    ],
    cta: "Get Started",
    featured: true,
    badge: "Most Popular",
  },
  {
    tier: "Enterprise",
    price: "$399",
    period: "Custom SLA · Dedicated onboarding",
    features: [
      { text: "Everything in Pro", ok: true },
      { text: "Custom SLA agreements", ok: true },
      { text: "Dedicated onboarding", ok: true },
      { text: "Compliance exports (SOC2)", ok: true },
      { text: "Priority support", ok: true },
      { text: "Custom integrations", ok: true },
      { text: "Invoice billing", ok: true },
    ],
    cta: "Contact Sales",
    featured: false,
  },
];

const STATS = [
  { num: "RBAC", label: "Role-Based Access" },
  { num: "100%", label: "Audited Queries" },
  { num: "99.9%", label: "Uptime SLA" },
  { num: "14-day", label: "Free Trial" },
];

export default function LandingPage({ onGetStarted }) {
  const formRef = useRef(null);

  useEffect(() => {
    const style = document.createElement("style");
    style.id = "landing-styles";
    style.textContent = `
      .lp-root { font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0a0b; color: #f0efe8; min-height: 100vh; overflow-x: hidden; }
      .lp-root *, .lp-root *::before, .lp-root *::after { box-sizing: border-box; margin: 0; padding: 0; }
      .lp-grid-bg { position: fixed; inset: 0; background-image: linear-gradient(rgba(240,180,41,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(240,180,41,0.03) 1px, transparent 1px); background-size: 60px 60px; pointer-events: none; z-index: 0; }
      .lp-nav { position: fixed; top: 0; left: 0; right: 0; z-index: 100; display: flex; align-items: center; justify-content: space-between; padding: 1rem 2rem; background: rgba(10,10,11,0.9); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,0.08); }
      .lp-logo { font-family: monospace; font-size: 1rem; color: #f0b429; letter-spacing: 0.05em; text-decoration: none; cursor: pointer; background: none; border: none; }
      .lp-logo span { color: #f0efe8; }
      .lp-nav-links { display: flex; gap: 2rem; list-style: none; }
      .lp-nav-links a { color: #8a8a8a; text-decoration: none; font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: color 0.2s; }
      .lp-nav-links a:hover { color: #f0efe8; }
      .lp-nav-cta { background: #f0b429; color: #000; padding: 0.5rem 1.25rem; border-radius: 4px; font-size: 0.875rem; font-weight: 700; border: none; cursor: pointer; transition: background 0.2s; }
      .lp-nav-cta:hover { background: #f7d070; }
      .lp-hero { position: relative; z-index: 1; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 8rem 2rem 4rem; }
      .lp-badge { display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(240,180,41,0.1); border: 1px solid rgba(240,180,41,0.3); color: #f0b429; font-family: monospace; font-size: 0.75rem; padding: 0.35rem 0.85rem; border-radius: 100px; margin-bottom: 2rem; }
      .lp-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; animation: lp-pulse 2s infinite; }
      @keyframes lp-pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      .lp-hero h1 { font-family: monospace; font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 700; line-height: 1.1; letter-spacing: -0.02em; margin-bottom: 1.5rem; }
      .lp-hero h1 em { font-style: normal; color: #f0b429; }
      .lp-hero p { font-size: 1.2rem; color: #8a8a8a; max-width: 560px; margin: 0 auto 2.5rem; font-weight: 300; }
      .lp-actions { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
      .lp-btn-primary { background: #f0b429; color: #000; padding: 0.85rem 2rem; border-radius: 4px; font-weight: 700; font-size: 1rem; border: none; cursor: pointer; transition: all 0.2s; }
      .lp-btn-primary:hover { background: #f7d070; transform: translateY(-2px); }
      .lp-btn-secondary { background: transparent; color: #f0efe8; padding: 0.85rem 2rem; border-radius: 4px; font-weight: 500; font-size: 1rem; border: 1px solid rgba(255,255,255,0.15); cursor: pointer; transition: all 0.2s; }
      .lp-btn-secondary:hover { border-color: #f0b429; color: #f0b429; transform: translateY(-2px); }
      .lp-stats { position: relative; z-index: 1; display: flex; justify-content: center; border-top: 1px solid rgba(255,255,255,0.08); border-bottom: 1px solid rgba(255,255,255,0.08); background: #111113; padding: 1.5rem 2rem; flex-wrap: wrap; }
      .lp-stat { text-align: center; padding: 0 3rem; border-right: 1px solid rgba(255,255,255,0.08); }
      .lp-stat:last-child { border-right: none; }
      .lp-stat-num { font-family: monospace; font-size: 1.75rem; font-weight: 700; color: #f0b429; }
      .lp-stat-label { font-size: 0.8rem; color: #8a8a8a; text-transform: uppercase; letter-spacing: 0.1em; }
      .lp-section { position: relative; z-index: 1; padding: 6rem 2rem; max-width: 1100px; margin: 0 auto; }
      .lp-label { font-family: monospace; font-size: 0.75rem; color: #f0b429; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 1rem; }
      .lp-section-title { font-family: monospace; font-size: clamp(1.75rem, 3vw, 2.5rem); font-weight: 700; line-height: 1.2; margin-bottom: 1rem; }
      .lp-section-sub { color: #8a8a8a; font-size: 1.1rem; max-width: 520px; margin-bottom: 3rem; }
      .lp-features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; overflow: hidden; }
      .lp-feature-card { background: #111113; padding: 2rem; transition: background 0.2s; }
      .lp-feature-card:hover { background: #1a1a1e; }
      .lp-feature-icon { font-size: 1.5rem; margin-bottom: 1rem; display: block; }
      .lp-feature-card h3 { font-family: monospace; font-size: 1rem; font-weight: 700; margin-bottom: 0.5rem; }
      .lp-feature-card p { font-size: 0.9rem; color: #8a8a8a; line-height: 1.6; }
      .lp-pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; }
      .lp-pricing-card { background: #111113; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 2rem; position: relative; transition: border-color 0.2s, transform 0.2s; }
      .lp-pricing-card:hover { border-color: rgba(255,255,255,0.15); transform: translateY(-4px); }
      .lp-pricing-card.featured { border-color: #f0b429; background: rgba(240,180,41,0.05); }
      .lp-pricing-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #f0b429; color: #000; font-family: monospace; font-size: 0.7rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: 100px; white-space: nowrap; }
      .lp-tier { font-family: monospace; font-size: 0.75rem; color: #f0b429; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
      .lp-price { font-family: monospace; font-size: 2.5rem; font-weight: 700; margin-bottom: 0.25rem; }
      .lp-price span { font-size: 1rem; font-weight: 400; }
      .lp-period { font-size: 0.85rem; color: #8a8a8a; margin-bottom: 1.5rem; }
      .lp-plan-features { list-style: none; margin-bottom: 2rem; }
      .lp-plan-features li { font-size: 0.9rem; color: #8a8a8a; padding: 0.4rem 0; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; align-items: center; gap: 0.5rem; }
      .lp-check { color: #22c55e; font-weight: 700; font-size: 0.8rem; }
      .lp-cross { color: #ef4444; font-weight: 700; font-size: 0.8rem; opacity: 0.4; }
      .lp-plan-btn { width: 100%; padding: 0.85rem; border-radius: 4px; font-weight: 700; font-size: 0.95rem; cursor: pointer; transition: all 0.2s; border: 1px solid rgba(255,255,255,0.15); background: transparent; color: #f0efe8; }
      .lp-pricing-card.featured .lp-plan-btn { background: #f0b429; color: #000; border-color: #f0b429; }
      .lp-plan-btn:hover { opacity: 0.9; transform: translateY(-1px); }
      .lp-contact-wrapper { display: grid; grid-template-columns: 1fr 1fr; gap: 4rem; align-items: start; }
      .lp-contact-info h3 { font-family: monospace; font-size: 1.5rem; margin-bottom: 1rem; }
      .lp-contact-info p { color: #8a8a8a; margin-bottom: 1.5rem; }
      .lp-contact-detail { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; font-size: 0.9rem; }
      .lp-contact-icon { width: 32px; height: 32px; background: rgba(240,180,41,0.1); border: 1px solid rgba(240,180,41,0.2); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; }
      .lp-contact-form { display: flex; flex-direction: column; gap: 1rem; }
      .lp-form-group { display: flex; flex-direction: column; gap: 0.4rem; }
      .lp-form-group label { font-size: 0.8rem; color: #8a8a8a; font-family: monospace; text-transform: uppercase; letter-spacing: 0.05em; }
      .lp-form-group input, .lp-form-group textarea, .lp-form-group select { background: #111113; border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; padding: 0.75rem 1rem; color: #f0efe8; font-family: inherit; font-size: 0.95rem; transition: border-color 0.2s; outline: none; }
      .lp-form-group input:focus, .lp-form-group textarea:focus, .lp-form-group select:focus { border-color: #f0b429; }
      .lp-form-group textarea { resize: vertical; min-height: 120px; }
      .lp-form-group select option { background: #111113; }
      .lp-footer { position: relative; z-index: 1; border-top: 1px solid rgba(255,255,255,0.08); padding: 2rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
      .lp-footer p { font-size: 0.85rem; color: #8a8a8a; }
      .lp-footer-links { display: flex; gap: 1.5rem; }
      .lp-footer-links a { font-size: 0.85rem; color: #8a8a8a; text-decoration: none; cursor: pointer; transition: color 0.2s; }
      .lp-footer-links a:hover { color: #f0b429; }
      .lp-form-success { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); color: #22c55e; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.9rem; text-align: center; }
      @media (max-width: 700px) {
        .lp-nav-links { display: none; }
        .lp-stat { padding: 1rem; border-right: none; }
        .lp-contact-wrapper { grid-template-columns: 1fr; gap: 2rem; }
      }
    `;
    document.head.appendChild(style);
    return () => {
      const s = document.getElementById("landing-styles");
      if (s) s.remove();
    };
  }, []);

  function scrollTo(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

  function handleSubmit(e) {
    e.preventDefault();
    const btn = e.target.querySelector("button[type='submit']");
    const orig = btn.textContent;
    btn.textContent = "✓ Message sent!";
    btn.style.background = "#22c55e";
    btn.style.color = "#000";
    setTimeout(() => {
      btn.textContent = orig;
      btn.style.background = "";
      btn.style.color = "";
      e.target.reset();
    }, 3000);
  }

  return (
    <div className="lp-root">
      <div className="lp-grid-bg" />

      {/* NAV */}
      <nav className="lp-nav">
        <button className="lp-logo" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          DB<span>Ops</span>
        </button>
        <ul className="lp-nav-links">
          <li><a onClick={() => scrollTo("features")}>Features</a></li>
          <li><a onClick={() => scrollTo("pricing")}>Pricing</a></li>
          <li><a onClick={() => scrollTo("contact")}>Contact</a></li>
          <li><a onClick={onGetStarted}>Sign In</a></li>
        </ul>
        <button className="lp-nav-cta" onClick={onGetStarted}>Start Free Trial</button>
      </nav>

      {/* HERO */}
      <div className="lp-hero">
        <div className="lp-badge"><span className="lp-dot" /> Live in production — trusted by teams</div>
        <h1>Database ops,<br /><em>under control.</em></h1>
        <p>Role-based access, incident tracking, scheduled reports, and audited SQL — all in one secure PostgreSQL operations platform.</p>
        <div className="lp-actions">
          <button className="lp-btn-primary" onClick={onGetStarted}>Start Free Trial →</button>
          <button className="lp-btn-secondary" onClick={() => scrollTo("pricing")}>View Pricing</button>
        </div>
      </div>

      {/* STATS */}
      <div className="lp-stats">
        {STATS.map((s) => (
          <div key={s.label} className="lp-stat">
            <div className="lp-stat-num">{s.num}</div>
            <div className="lp-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* FEATURES */}
      <section className="lp-section" id="features">
        <div className="lp-label">// features</div>
        <h2 className="lp-section-title">Everything your team needs<br />to run database ops safely.</h2>
        <p className="lp-section-sub">Built for teams that can&apos;t afford mistakes — every action tracked, every access controlled.</p>
        <div className="lp-features-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="lp-feature-card">
              <span className="lp-feature-icon">{f.icon}</span>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* PRICING */}
      <section className="lp-section" id="pricing">
        <div className="lp-label">// pricing</div>
        <h2 className="lp-section-title">Simple, transparent pricing.</h2>
        <p className="lp-section-sub">Start free for 14 days. No credit card required.</p>
        <div className="lp-pricing-grid">
          {PLANS.map((plan) => (
            <div key={plan.tier} className={`lp-pricing-card${plan.featured ? " featured" : ""}`}>
              {plan.badge && <div className="lp-pricing-badge">{plan.badge}</div>}
              <div className="lp-tier">{plan.tier}</div>
              <div className="lp-price">{plan.price}<span>/mo</span></div>
              <div className="lp-period">{plan.period}</div>
              <ul className="lp-plan-features">
                {plan.features.map((f) => (
                  <li key={f.text}>
                    <span className={f.ok ? "lp-check" : "lp-cross"}>{f.ok ? "✓" : "✕"}</span>
                    {f.text}
                  </li>
                ))}
              </ul>
              <button
                className="lp-plan-btn"
                onClick={plan.tier === "Enterprise" ? () => scrollTo("contact") : onGetStarted}
              >
                {plan.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* CONTACT */}
      <section className="lp-section" id="contact">
        <div className="lp-label">// contact</div>
        <div className="lp-contact-wrapper">
          <div className="lp-contact-info">
            <h3>Let&apos;s talk about<br />your database ops.</h3>
            <p>Have questions about DBOps or need a custom plan? Reach out and we&apos;ll get back to you within 24 hours.</p>
            <div className="lp-contact-detail">
              <div className="lp-contact-icon">✉</div>
              <span>barney@gilliomfrontlinedigital.com</span>
            </div>
            <div className="lp-contact-detail">
              <div className="lp-contact-icon">🌐</div>
              <span>gilliomfrontlinedigital.com</span>
            </div>
            <div className="lp-contact-detail">
              <div className="lp-contact-icon">📍</div>
              <span>Tampa, FL — Remote worldwide</span>
            </div>
          </div>
          <form className="lp-contact-form" ref={formRef} onSubmit={handleSubmit}>
            <div className="lp-form-group">
              <label>Your Name</label>
              <input type="text" placeholder="John Smith" required />
            </div>
            <div className="lp-form-group">
              <label>Email Address</label>
              <input type="email" placeholder="john@company.com" required />
            </div>
            <div className="lp-form-group">
              <label>Interest</label>
              <select>
                <option>Start Free Trial</option>
                <option>Pro Plan</option>
                <option>Enterprise Plan</option>
                <option>Custom Integration</option>
                <option>General Inquiry</option>
              </select>
            </div>
            <div className="lp-form-group">
              <label>Message</label>
              <textarea placeholder="Tell us about your database setup and team size..." />
            </div>
            <button type="submit" className="lp-btn-primary" style={{ width: "100%" }}>
              Send Message →
            </button>
          </form>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="lp-footer">
        <p>© 2026 Gilliom Frontline Digital. Built by Barney R. Gilliom.</p>
        <div className="lp-footer-links">
          <a onClick={() => window.open("https://gilliomfrontlinedigital.com", "_blank")}>Portfolio</a>
          <a onClick={() => window.open("/terms-of-service.html", "_blank")}>Terms of Service</a>
          <a onClick={onGetStarted}>Sign In</a>
          <a onClick={() => window.open("mailto:barney@gilliomfrontlinedigital.com")}>Email</a>
        </div>
      </footer>
    </div>
  );
}
