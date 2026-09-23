"""Premium visual system for the VendorShield auditor workspace."""
APP_CSS = r"""
<style>
:root {
  --ink:#08111f; --navy:#0b1325; --navy2:#111c35; --cyan:#22d3ee;
  --blue:#3b82f6; --violet:#8b5cf6; --panel:#ffffff; --muted:#64748b;
  --border:#dbe5f3; --soft:#f4f7fb; --danger:#ef4444; --warning:#f59e0b; --success:#22c55e;
}
html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }
.stApp { background:
  radial-gradient(circle at 82% 2%, rgba(59,130,246,.12), transparent 24rem),
  radial-gradient(circle at 44% -5%, rgba(139,92,246,.09), transparent 20rem),
  linear-gradient(180deg,#f8fbff 0%,#eef3fa 100%); color:var(--ink); }
.block-container { padding:1rem 1.55rem 2.4rem; max-width:1580px; }
header[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#08111f 0%,#0d1830 52%,#101d36 100%); border-right:1px solid rgba(148,163,184,.16); }
[data-testid="stSidebar"] > div:first-child { padding-top:.8rem; }
[data-testid="stSidebar"] * { color:#dbeafe; }
[data-testid="stSidebar"] label { font-weight:600; }
[data-testid="stSidebar"] .stMultiSelect span,
[data-testid="stSidebar"] .stSelectbox div,
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] * { color:#0f172a !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.28rem .45rem; border-radius:10px; }

.vs-sidebrand { padding:.75rem .6rem 1rem; display:flex; gap:.75rem; align-items:center; }
.vs-logo { width:48px; height:48px; border-radius:15px; display:grid; place-items:center; color:white; font-weight:900; font-size:22px; background:linear-gradient(135deg,#2563eb,#06b6d4 60%,#8b5cf6); box-shadow:0 0 0 1px rgba(255,255,255,.12),0 14px 34px rgba(34,211,238,.20); }
.vs-side-title { font-weight:850; font-size:1.2rem; color:white; letter-spacing:-.02em; }
.vs-side-sub { color:#8fa8c7; font-size:.74rem; text-transform:uppercase; letter-spacing:.12em; margin-top:.1rem; }
.vs-live { display:inline-flex; align-items:center; gap:.45rem; color:#93c5fd; font-size:.75rem; font-weight:700; letter-spacing:.04em; padding:.4rem .65rem; border:1px solid rgba(96,165,250,.25); background:rgba(30,64,175,.17); border-radius:999px; }
.vs-live-dot { width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 5px rgba(34,197,94,.12); }

.vs-hero { position:relative; overflow:hidden; border:1px solid rgba(148,163,184,.24); border-radius:24px; padding:1.15rem 1.35rem; background:linear-gradient(115deg,#0a1224 0%,#12244a 58%,#153768 100%); box-shadow:0 18px 48px rgba(15,23,42,.16); margin-bottom:1rem; }
.vs-hero:after { content:""; position:absolute; width:310px;height:310px;border-radius:50%; right:-130px;top:-180px;background:radial-gradient(circle,rgba(34,211,238,.36),transparent 68%); }
.vs-eyebrow { color:#67e8f9; font-size:.73rem; font-weight:850; letter-spacing:.15em; text-transform:uppercase; }
.vs-hero-title { color:white; font-size:2rem; line-height:1.05; font-weight:900; letter-spacing:-.035em; margin:.3rem 0; }
.vs-hero-copy { color:#bfd0e7; font-size:.95rem; max-width:850px; }
.vs-pipeline { display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.8rem; }
.vs-chip { padding:.34rem .62rem; border-radius:999px; color:#dbeafe; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.13); font-size:.73rem; font-weight:650; }

.vs-kpi { position:relative; overflow:hidden; background:rgba(255,255,255,.96); border:1px solid var(--border); border-radius:18px; padding:1rem 1.05rem; min-height:125px; box-shadow:0 10px 28px rgba(15,23,42,.065); }
.vs-kpi:before { content:""; position:absolute; left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,#2563eb,#22d3ee); }
.vs-kpi-icon { width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:#eff6ff;color:#2563eb;font-weight:900;margin-bottom:.45rem; }
.vs-kpi-label { color:#64748b; font-size:.72rem; text-transform:uppercase; letter-spacing:.095em; font-weight:800; }
.vs-kpi-value { color:#0b1325; font-size:1.62rem; font-weight:900; margin-top:.18rem; letter-spacing:-.025em; }
.vs-kpi-note { color:#7890ad; font-size:.76rem; margin-top:.22rem; }

.vs-section-head { display:flex;justify-content:space-between;align-items:end;margin:.85rem 0 .55rem; }
.vs-section-title { font-weight:900;font-size:1.35rem;letter-spacing:-.025em;color:#0b1325; }
.vs-section-sub { color:#64748b;font-size:.82rem;margin-top:.15rem; }
.vs-panel { background:rgba(255,255,255,.96); border:1px solid var(--border); border-radius:18px; box-shadow:0 8px 26px rgba(15,23,42,.055); padding:.85rem 1rem; }
.vs-callout { background:linear-gradient(90deg,#eff6ff,#eef2ff); border:1px solid #cfe0ff; border-left:4px solid #3b82f6; border-radius:13px; padding:.75rem .9rem; color:#1e3a8a; margin:.45rem 0 1rem; }
.vs-reason { background:linear-gradient(90deg,#f8fbff,#fff); border:1px solid #d9e8fb; border-left:4px solid #3b82f6; border-radius:13px; padding:.75rem .9rem; margin:.45rem 0; color:#1e293b; box-shadow:0 5px 16px rgba(15,23,42,.035); }
.vs-signal { display:inline-block; padding:.3rem .58rem; border-radius:999px; font-size:.75rem; font-weight:750; margin:.18rem .2rem .18rem 0; background:#fff7ed; color:#9a3412; border:1px solid #fed7aa; }
.vs-risk-high { color:#dc2626; } .vs-risk-medium { color:#d97706; } .vs-risk-low { color:#16a34a; }
.vs-footer { text-align:center;color:#7890ad;font-size:.76rem;padding:1.35rem 0 .25rem; }


/* Authentication page */
.vs-auth-spacer { height:1.15rem; }
.vs-auth-intro {
  position:relative; overflow:hidden; min-height:650px; padding:2.15rem 2.2rem 1.8rem;
  border-radius:28px; color:white;
  background:
    radial-gradient(circle at 92% 5%, rgba(34,211,238,.28), transparent 18rem),
    radial-gradient(circle at 8% 94%, rgba(139,92,246,.20), transparent 17rem),
    linear-gradient(145deg,#071225 0%,#10244a 55%,#164f78 100%);
  border:1px solid rgba(148,163,184,.22);
  box-shadow:0 24px 65px rgba(15,23,42,.22);
}
.vs-auth-intro:after {
  content:""; position:absolute; width:330px; height:330px; border-radius:50%;
  right:-190px; bottom:-210px; border:1px solid rgba(255,255,255,.13);
  box-shadow:0 0 0 44px rgba(255,255,255,.025),0 0 0 90px rgba(255,255,255,.018);
}
.vs-auth-brand-row { display:flex; align-items:center; gap:.8rem; margin-bottom:2.1rem; position:relative; z-index:1; }
.vs-auth-logo { width:50px; height:50px; border-radius:15px; display:grid; place-items:center; font-size:.9rem; font-weight:950; letter-spacing:.04em; color:white; background:linear-gradient(135deg,#2563eb,#06b6d4 62%,#8b5cf6); box-shadow:0 13px 30px rgba(34,211,238,.23), inset 0 0 0 1px rgba(255,255,255,.2); }
.vs-auth-brand { color:#fff; font-weight:950; letter-spacing:.13em; font-size:.93rem; }
.vs-auth-brand-sub { color:#91a9c9; font-size:.62rem; font-weight:750; letter-spacing:.15em; margin-top:.13rem; }
.vs-auth-kicker { color:#67e8f9; font-size:.68rem; font-weight:900; letter-spacing:.17em; margin-bottom:.65rem; }
.vs-auth-intro h1 { color:#fff; max-width:650px; font-size:2.55rem; line-height:1.03; letter-spacing:-.045em; margin:0 0 .8rem; position:relative; z-index:1; }
.vs-auth-lead { color:#c8d8ec; max-width:690px; font-size:1rem; line-height:1.65; margin:0 0 1.45rem; position:relative; z-index:1; }
.vs-auth-feature-grid { display:grid; gap:.7rem; position:relative; z-index:1; }
.vs-auth-feature { display:grid; grid-template-columns:42px 1fr; gap:.8rem; align-items:start; padding:.8rem .85rem; border:1px solid rgba(191,219,254,.14); background:rgba(255,255,255,.055); border-radius:15px; backdrop-filter:blur(9px); }
.vs-auth-feature-icon { width:38px; height:38px; border-radius:12px; display:grid; place-items:center; color:#a5f3fc; border:1px solid rgba(103,232,249,.25); background:rgba(34,211,238,.09); font-size:.7rem; font-weight:900; letter-spacing:.04em; }
.vs-auth-feature strong { display:block; color:#fff; font-size:.91rem; margin-bottom:.15rem; }
.vs-auth-feature span { display:block; color:#abc0dc; font-size:.78rem; line-height:1.4; }
.vs-auth-flow-label { color:#8fa8c7; font-size:.61rem; font-weight:900; letter-spacing:.17em; margin:1.25rem 0 .5rem; position:relative; z-index:1; }
.vs-auth-flow { display:flex; flex-wrap:wrap; gap:.38rem; align-items:center; position:relative; z-index:1; }
.vs-auth-flow span { padding:.36rem .55rem; border-radius:999px; font-size:.68rem; font-weight:750; color:#dbeafe; background:rgba(255,255,255,.075); border:1px solid rgba(255,255,255,.12); }
.vs-auth-flow b { color:#67e8f9; font-size:.78rem; }
.vs-auth-responsible { position:relative; z-index:1; margin-top:1.15rem; padding:.7rem .8rem; color:#afc3dc; font-size:.72rem; line-height:1.45; border-left:3px solid #22d3ee; background:rgba(2,6,23,.18); border-radius:0 11px 11px 0; }

.st-key-auth_form_card,
.st-key-auth_form_card > div,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.vs-auth-form-head) {
  border-radius:26px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.vs-auth-form-head) {
  min-height:650px; padding:1.65rem 1.7rem 1.45rem;
  background:rgba(255,255,255,.94); border:1px solid #d6e2f0 !important;
  box-shadow:0 22px 58px rgba(15,23,42,.13); backdrop-filter:blur(14px);
}
.vs-auth-form-head { margin:.15rem 0 .4rem; }
.vs-auth-kicker-blue { color:#2563eb; }
.vs-auth-form-head h2 { color:#0b1325; font-size:2rem; letter-spacing:-.035em; margin:.05rem 0 .2rem; }
.vs-auth-form-head p { color:#64748b; margin:0 0 .3rem; font-size:.9rem; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.vs-auth-form-head) [data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid #e2e8f0; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.vs-auth-form-head) [data-baseweb="tab"] { padding:.65rem .85rem; font-weight:800; }
.vs-demo-box { display:flex; justify-content:space-between; align-items:center; gap:.9rem; margin:.75rem 0 .55rem; padding:.75rem .8rem; border-radius:14px; background:linear-gradient(90deg,#eff6ff,#f5f3ff); border:1px solid #cfe0ff; }
.vs-demo-box strong { display:block; color:#1e3a8a; font-size:.82rem; }
.vs-demo-box span { display:block; color:#64748b; font-size:.7rem; margin-top:.1rem; }
.vs-demo-box code { white-space:nowrap; color:#1d4ed8; background:white; border:1px solid #dbeafe; border-radius:8px; padding:.38rem .5rem; font-size:.69rem; }
.st-key-fill_demo_credentials button { min-height:2.25rem; background:#fff !important; color:#1d4ed8 !important; border:1px solid #bfdbfe !important; box-shadow:none !important; }
.st-key-fill_demo_credentials button:hover { border-color:#60a5fa !important; background:#eff6ff !important; }
.vs-auth-trust { display:grid; grid-template-columns:repeat(3,1fr); gap:.5rem; border-top:1px solid #e2e8f0; margin-top:.65rem; padding-top:.75rem; }
.vs-auth-trust div { padding:.55rem .45rem; text-align:center; background:#f8fafc; border:1px solid #e2e8f0; border-radius:11px; }
.vs-auth-trust strong { display:block; color:#1e293b; font-size:.68rem; }
.vs-auth-trust span { display:block; color:#7890ad; font-size:.6rem; margin-top:.1rem; }
.vs-auth-footer { display:flex; justify-content:space-between; gap:1rem; color:#7890ad; font-size:.69rem; margin:.85rem .3rem 0; padding:.7rem .25rem 0; border-top:1px solid rgba(148,163,184,.35); }
.vs-auth-footer strong { color:#334155; }

.stButton > button, .stFormSubmitButton > button { border-radius:11px; font-weight:750; min-height:2.65rem; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { border:0; background:linear-gradient(100deg,#2563eb,#0ea5e9 60%,#7c3aed); box-shadow:0 8px 20px rgba(37,99,235,.22); }
/* Sidebar logout: explicit red treatment so it remains visible on the dark sidebar. */
[data-testid="stSidebar"] .st-key-logout_button button {
  background:#dc2626 !important;
  color:#ffffff !important;
  border:1px solid #ef4444 !important;
  box-shadow:0 8px 20px rgba(220,38,38,.24) !important;
}
[data-testid="stSidebar"] .st-key-logout_button button:hover {
  background:#b91c1c !important;
  border-color:#f87171 !important;
  color:#ffffff !important;
}
[data-testid="stSidebar"] .st-key-logout_button button p { color:#ffffff !important; }
.stTextInput input, .stNumberInput input, .stTextArea textarea, [data-baseweb="select"] > div { border-radius:10px !important; }
div[data-testid="stMetric"] { background:white;border:1px solid var(--border);padding:.75rem;border-radius:14px;box-shadow:0 5px 18px rgba(15,23,42,.04); }
[data-testid="stDataFrame"] { border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:0 7px 20px rgba(15,23,42,.04); }
hr { border-color:#dbe5f3 !important; }
@media (max-width:900px){
 .vs-hero-title{font-size:1.55rem}.block-container{padding:.75rem}.vs-kpi{min-height:108px}
 .vs-auth-spacer{height:.2rem}.vs-auth-intro{min-height:auto;padding:1.5rem 1.25rem}.vs-auth-intro h1{font-size:2rem}
 div[data-testid="stVerticalBlockBorderWrapper"]:has(.vs-auth-form-head){min-height:auto;padding:1.2rem 1rem}
 .vs-auth-trust{grid-template-columns:1fr}.vs-auth-footer{flex-direction:column;text-align:center}.vs-demo-box{align-items:flex-start;flex-direction:column}
}
</style>
"""
