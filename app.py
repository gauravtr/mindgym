"""MindGym — mental maths & memory trainer (Streamlit)."""
import html
import math
import os
import random
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import analytics as A
import growth as G
import logic as L
import puzzles as PZ
from db import Store

st.set_page_config(page_title="MindGym · Train your mind", page_icon="🧠", layout="centered",
                   initial_sidebar_state="collapsed")


@st.cache_resource
def get_store():
    url = None
    try:
        url = st.secrets.get("DATABASE_URL")
    except Exception:
        pass
    return Store(url or os.environ.get("DATABASE_URL"))


store = get_store()

# ================================================================ design system
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
:root{
  --ink:#0f172a; --ink-2:#475569; --ink-3:#94a3b8; --line:#e6e8f1; --surface:#ffffff; --bg:#f7f8fc;
  --brand:#4f46e5; --brand-2:#7c3aed; --brand-soft:#eef2ff;
  --ok:#059669; --ok-soft:#ecfdf5; --bad:#e11d48; --bad-soft:#fff1f2; --warn:#d97706; --warn-soft:#fffbeb;
  --shadow:0 1px 2px rgba(15,23,42,.04), 0 12px 32px -20px rgba(15,23,42,.22);
}
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp td, .stApp th {
  font-family:'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp{background:radial-gradient(1100px 380px at 50% -180px,#e9ecff 0%,rgba(233,236,255,0) 70%),var(--bg);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:880px;padding-top:1.4rem;padding-bottom:5rem;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5{letter-spacing:-.02em;color:var(--ink);}

/* ---------- top bar & navigation */
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:1.22rem;letter-spacing:-.02em;color:var(--ink);}
.brand .logo{width:36px;height:36px;border-radius:11px;background:linear-gradient(135deg,var(--brand),var(--brand-2));
  display:grid;place-items:center;color:#fff;font-size:19px;box-shadow:0 8px 18px -8px rgba(79,70,229,.75);}
.brand small{display:block;font-size:.72rem;font-weight:500;color:var(--ink-3);letter-spacing:0;margin-top:-2px;}
.st-key-nav{margin:6px 0 4px;width:100%!important;}
.st-key-nav [data-testid="stButtonGroup"]{width:100%;}
.st-key-nav [role="radiogroup"]{width:100%;max-width:none!important;}
.st-key-nav button{flex:1 1 0;min-height:2.6rem;font-weight:600;min-width:0;}
/* keep these rows side by side on phones */
.st-key-topbar [data-testid="stHorizontalBlock"], .st-key-ansbox [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:10px;}
.st-key-topbar [data-testid="stColumn"], .st-key-ansbox [data-testid="stColumn"]{min-width:0!important;width:auto!important;flex:1 1 0!important;}
.st-key-topbar [data-testid="stColumn"]:last-child{flex:0 0 auto!important;}
.st-key-ansbox [data-testid="stColumn"]:first-child{flex:3 1 0!important;}
@media (max-width:640px){ .st-key-nav button p{font-size:.82rem;} .brand small{display:none;} }

/* ---------- headings */
.page-head{margin:14px 0 14px;}
.page-head .eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--brand);}
.page-head h2{margin:2px 0 0;padding:0;font-size:1.7rem;font-weight:800;letter-spacing:-.025em;color:var(--ink);}
.page-head p{margin:.3rem 0 0;color:var(--ink-2);font-size:.98rem;}
.sec{font-weight:700;font-size:1.02rem;color:var(--ink);margin:22px 0 10px;}
.sec small{color:var(--ink-3);font-weight:500;margin-left:6px;font-size:.85rem;}
.muted{color:var(--ink-2);font-size:.9rem;}

/* ---------- cards (keyed containers whose key starts with card_) */
[class*="st-key-card_"]{background:var(--surface);border:1px solid var(--line);border-radius:20px;
  padding:20px 22px 18px;box-shadow:var(--shadow);}
[class*="st-key-card_qs"]{padding:18px 18px 16px;}
[data-testid="stMetric"]{background:var(--surface);border:1px solid var(--line);border-radius:16px;
  padding:14px 16px;box-shadow:var(--shadow);}
[data-testid="stMetricLabel"] p{color:var(--ink-2);font-weight:600;font-size:.8rem;}
[data-testid="stMetricValue"]{font-weight:750;font-variant-numeric:tabular-nums;letter-spacing:-.02em;}

/* ---------- controls */
.stButton button, .stFormSubmitButton button, .stDownloadButton button, [data-testid="stPopover"] button{
  border-radius:12px;font-weight:600;min-height:2.7rem;transition:transform .12s ease, box-shadow .12s ease;}
button[kind="primary"], button[kind="primaryFormSubmit"],
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(135deg,var(--brand),#6d5bf0)!important;border:0!important;color:#fff!important;
  box-shadow:0 10px 22px -12px rgba(79,70,229,.85);}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover{transform:translateY(-1px);
  box-shadow:0 14px 26px -12px rgba(79,70,229,.9);}
.stTextInput [data-baseweb="input"]{border-radius:12px;}
[data-testid="stForm"]{border:0;padding:0;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#eceef6;padding:4px;border-radius:12px;}
.stTabs [data-baseweb="tab"]{border-radius:9px;padding:6px 12px;height:auto;}
.stTabs [aria-selected="true"]{background:#fff;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{display:none;}
[data-testid="stExpander"] details{border-radius:14px;border-color:var(--line);background:var(--surface);}

/* ---------- drill */
.hud{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin:6px 0 10px;}
.hud .where{font-weight:700;color:var(--ink);font-size:1rem;}
.hud .where span{color:var(--ink-3);font-weight:600;}
.pills{display:flex;gap:6px;flex-wrap:wrap;}
.pill{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:999px;background:#fff;
  border:1px solid var(--line);font-weight:600;font-size:.82rem;color:var(--ink-2);font-variant-numeric:tabular-nums;}
.pill.ok{color:var(--ok);} .pill.fire{color:var(--warn);background:var(--warn-soft);border-color:#fde68a;}
.pill.brand{color:var(--brand);background:var(--brand-soft);border-color:#c7d2fe;}
.track{height:7px;background:#e7e9f4;border-radius:999px;overflow:hidden;margin:0 0 14px;}
.track > div{height:100%;background:linear-gradient(90deg,var(--brand),var(--brand-2));border-radius:999px;}
.q-card{background:var(--surface);border:1px solid var(--line);border-radius:26px;padding:34px 20px 34px;
  text-align:center;box-shadow:var(--shadow);margin:4px 0 14px;}
.chip{display:inline-flex;gap:6px;align-items:center;font-size:.74rem;font-weight:650;color:var(--brand);
  background:var(--brand-soft);padding:4px 11px;border-radius:999px;}
.q-text{font-size:clamp(2.3rem,8vw,3.6rem);font-weight:800;letter-spacing:-.02em;color:var(--ink);
  margin-top:14px;font-variant-numeric:tabular-nums;line-height:1.1;}
.q-text .eq{color:#c3c8d8;font-weight:700;}
.st-key-ansbox input{font-size:1.9rem;text-align:center;font-weight:700;height:3.7rem;
  font-variant-numeric:tabular-nums;}
.st-key-recallbox input{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:1.7rem;text-align:center;
  font-weight:700;height:3.7rem;letter-spacing:.25em;}
.st-key-ansbox input::placeholder, .st-key-recallbox input::placeholder{font-family:'Inter',sans-serif;font-size:1rem;
  font-weight:500;letter-spacing:0;color:#a3acc0;}
.st-key-ansbox [data-testid="InputInstructions"], .st-key-recallbox [data-testid="InputInstructions"]{display:none;}
.fb{display:flex;gap:10px;align-items:flex-start;padding:11px 14px;border-radius:14px;font-size:.94rem;
  margin:2px 0 10px;line-height:1.45;}
.fb.ok{background:var(--ok-soft);color:#065f46;border:1px solid #a7f3d0;}
.fb.bad{background:var(--bad-soft);color:#9f1239;border:1px solid #fecdd3;}
.fb .ic{font-weight:800;flex:none;}
.tip{color:var(--ink-2);font-size:.92rem;line-height:1.55;}
.lvl{display:flex;flex-direction:column;gap:4px;margin:2px 0 6px;}
.lvl div{font-size:.86rem;color:var(--ink-2);} .lvl b{color:var(--ink);font-weight:600;}

/* ---------- results */
.result{background:linear-gradient(135deg,var(--brand),var(--brand-2));color:#fff;border-radius:24px;
  padding:24px 26px;box-shadow:0 22px 40px -24px rgba(79,70,229,.9);margin:6px 0 16px;}
.result.bad{background:linear-gradient(135deg,#334155,#1e293b);box-shadow:0 22px 40px -26px rgba(15,23,42,.9);}
.result .grade{font-size:.74rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;opacity:.85;}
.result .big{font-size:2.9rem;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin-top:4px;}
.result .line{opacity:.9;margin-top:2px;}
.result .stats{display:flex;gap:28px;flex-wrap:wrap;margin-top:14px;}
.result .stats div{font-size:.78rem;opacity:.85;}
.result .stats b{display:block;font-size:1.2rem;opacity:1;font-weight:700;}

/* ---------- memory */
.mem-card{background:linear-gradient(160deg,#111827,#1e1b4b);color:#f8fafc;border-radius:26px;padding:46px 16px;
  text-align:center;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:clamp(1.9rem,7vw,3rem);
  font-weight:700;letter-spacing:.26em;word-break:break-all;box-shadow:0 22px 44px -26px rgba(30,27,75,.85);}
.mem-card .q-sub{font-family:'Inter',sans-serif;font-size:.85rem;opacity:.6;letter-spacing:0;margin-top:8px;font-weight:500;}
.mem-card.count{opacity:.5;}
.vault{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;padding:13px 14px;
  border-radius:16px;background:#fff;border:1.5px dashed #c7d2fe;color:var(--ink-2);font-weight:600;font-size:.92rem;
  margin:4px 0 12px;}
.vault .dots{font-family:'JetBrains Mono',monospace;letter-spacing:.22em;color:var(--brand);font-weight:700;}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin:2px 0 4px;}
.step{display:flex;align-items:center;gap:8px;font-size:.85rem;color:var(--ink-2);font-weight:500;}
.step b{width:22px;height:22px;border-radius:999px;display:grid;place-items:center;background:var(--brand-soft);
  color:var(--brand);font-size:.75rem;}
.step i{color:#cbd5e1;font-style:normal;}
.pz-q{font-size:1.18rem;font-weight:650;color:var(--ink);line-height:1.45;margin:10px 0 6px;}
.st-key-card_pz [data-testid="stElementContainer"]:has([data-testid="stRadio"]),
.st-key-card_pz [data-testid="stRadio"]{width:100%!important;}
.st-key-card_pz [data-testid="stRadioGroup"]{width:100%;align-items:stretch;}
.st-key-card_pz [data-testid="stRadioGroup"] > div{width:100%;flex-direction:column;gap:0;}
.st-key-card_pz label[data-testid="stRadioOption"]{border:1px solid var(--line);border-radius:12px;padding:11px 14px;
  margin:0 0 8px;width:100%;background:#fff;transition:all .12s;cursor:pointer;}
.st-key-card_pz label[data-testid="stRadioOption"]:hover{border-color:#c7d2fe;background:#fafaff;}
.st-key-card_pz label[data-testid="stRadioOption"][data-selected="true"]{border-color:var(--brand);background:var(--brand-soft);}
.digit{display:inline-grid;place-items:center;width:2.05em;height:2.4em;font-family:'JetBrains Mono',monospace;
  font-size:1.3rem;font-weight:700;border-radius:10px;margin:3px;}
.d-ok{background:var(--ok-soft);color:#047857;border:1px solid #a7f3d0;}
.d-bad{background:var(--bad-soft);color:#be123c;border:1px solid #fecdd3;}

/* ---------- home */
.hero{display:flex;align-items:center;gap:22px;background:var(--surface);border:1px solid var(--line);border-radius:24px;
  padding:22px 24px;box-shadow:var(--shadow);margin:12px 0 12px;}
.hero h2{margin:0;padding:0;font-size:1.65rem;font-weight:800;letter-spacing:-.025em;color:var(--ink);}
.hero p{margin:5px 0 0;color:var(--ink-2);}
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 6px;}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:13px 15px;box-shadow:var(--shadow);}
.tile .k{font-size:.74rem;color:var(--ink-2);font-weight:600;}
.tile .v{font-size:1.45rem;font-weight:800;margin-top:2px;font-variant-numeric:tabular-nums;letter-spacing:-.02em;color:var(--ink);}
.tile .s{font-size:.74rem;color:var(--ink-3);}
.qs-ic{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;font-size:20px;background:var(--brand-soft);}
.qs-t{font-weight:700;margin-top:10px;color:var(--ink);font-size:1rem;}
.qs-d{color:var(--ink-2);font-size:.85rem;min-height:2.7em;margin:2px 0 6px;line-height:1.4;}
.reco{display:flex;gap:14px;align-items:center;}
.reco .qs-ic{background:var(--warn-soft);flex:none;}
@media (max-width:640px){
  .hero{flex-direction:row;padding:18px;gap:14px;} .hero h2{font-size:1.3rem;}
  .tiles{grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;} .tile{padding:10px 11px;} .tile .v{font-size:1.15rem;}
  .q-card{padding:26px 14px;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def H(markup):
    """Render a trusted HTML snippet (kept on one line so Markdown never treats it as code)."""
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def page_head(eyebrow, title, sub=""):
    H(f'<div class="page-head"><div class="eyebrow">{eyebrow}</div><h2>{title}</h2>'
      + (f"<p>{sub}</p>" if sub else "") + "</div>")


def feedback(ok, msg):
    H(f'<div class="fb {"ok" if ok else "bad"}"><span class="ic">{"✓" if ok else "✕"}</span><span>{msg}</span></div>')


def focus_input():
    """Put the cursor back in the answer box so you can keep typing + Enter."""
    components.html(
        """<script>
        const t = () => {const i = window.parent.document.querySelectorAll('input[type=text]');
                         if (i.length) i[i.length-1].focus();};
        setTimeout(t, 60); setTimeout(t, 300);
        </script>""",
        height=0,
    )


def ring(frac, big, small):
    r = 34
    c = 2 * math.pi * r
    off = c * (1 - max(0.0, min(frac, 1.0)))
    return (f'<svg width="96" height="96" viewBox="0 0 92 92" style="flex:none">'
            f'<defs><linearGradient id="rg" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#4f46e5"/>'
            f'<stop offset="1" stop-color="#7c3aed"/></linearGradient></defs>'
            f'<circle cx="46" cy="46" r="{r}" stroke="#eceef7" stroke-width="9" fill="none"/>'
            f'<circle cx="46" cy="46" r="{r}" stroke="url(#rg)" stroke-width="9" fill="none" stroke-linecap="round" '
            f'stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" transform="rotate(-90 46 46)"/>'
            f'<text x="46" y="47" text-anchor="middle" font-size="18" font-weight="800" fill="#0f172a" '
            f'font-family="Inter,sans-serif">{big}</text>'
            f'<text x="46" y="62" text-anchor="middle" font-size="9.5" font-weight="600" fill="#94a3b8" '
            f'font-family="Inter,sans-serif">{small}</text></svg>')


# ================================================================ state
ss = st.session_state
defaults = dict(
    history=[],          # math attempts
    mem_history=[],      # memory attempts
    drill=None,          # active drill config
    q=None, q_start=0.0, feedback=None, streak=0, best_streak=0,
    mem_phase="idle", mem_seq="", mem_len=5, mem_result=None,
    user=None, nav="Home", last_page="Home",
)
for k, v in defaults.items():
    ss.setdefault(k, v)

NAV = {"Home": ":material/home: Home", "Math": ":material/calculate: Math",
       "Memory": ":material/psychology: Memory", "Progress": ":material/insights: Progress"}


# ================================================================ actions (used as button callbacks)
def new_question():
    d = ss.drill
    cat = random.choice(d["cats"])
    ss.q = L.make_question(cat, d["level"])
    ss.q_start = time.time()


def start_drill(cats, level, mode, amount):
    ss.drill = dict(cats=list(cats), level=level, mode=mode, amount=amount,
                    start=time.time(), n=0, right=0, times=[], done=False, wrong=[])
    ss.streak, ss.feedback = 0, None
    new_question()
    ss.nav = "Math"


def replay_drill():
    d = ss.drill
    start_drill(d["cats"], d["level"], d["mode"], d["amount"])


def reset_drill():
    ss.drill = None
    ss.nav = "Math"


def start_memory(cfg):
    ss.mem_cfg = cfg
    ss.mem_seq = L.make_sequence(ss.mem_len)
    ss.mem_result = None
    ss.mem_phase = "show"
    ss.nav = "Memory"


def go(page):
    ss.nav = page


def logout():
    for k in ("user", "history", "mem_history", "drill", "q", "feedback", "mem_result"):
        ss[k] = defaults[k]
    ss.streak = ss.best_streak = 0
    ss.mem_phase = "idle"
    ss.nav = "Home"


def auth_forms(prefix):
    t_login, t_signup = st.tabs(["Log in", "Create account"])
    with t_login:
        with st.form(f"{prefix}_login", border=False):
            u = st.text_input("Username", key=f"{prefix}_li_u")
            p = st.text_input("Password", type="password", key=f"{prefix}_li_p")
            if st.form_submit_button("Log in", type="primary", use_container_width=True):
                user = store.login(u, p)
                if user:
                    ss.user = user
                    st.rerun()
                else:
                    st.error("Wrong username or password.")
    with t_signup:
        with st.form(f"{prefix}_signup", border=False):
            u = st.text_input("Choose a username", key=f"{prefix}_su_u")
            p = st.text_input("Password (6+ characters)", type="password", key=f"{prefix}_su_p")
            p2 = st.text_input("Repeat password", type="password", key=f"{prefix}_su_p2")
            if st.form_submit_button("Create free account", type="primary", use_container_width=True):
                if p != p2:
                    st.error("Passwords don't match.")
                else:
                    user, err = store.create_user(u, p)
                    if err:
                        st.error(err)
                    else:
                        ss.user = user
                        # keep anything practised as a guest this session
                        for h in ss.history:
                            store.add_math(user["id"], h["category"], h["level"], h["question"], h["answer"],
                                           h["given"], h["correct"], h["seconds"])
                        for m in ss.mem_history:
                            store.add_memory(user["id"], m["length"], m["direction"], m["style"],
                                             m["correct"], m["digits_right"], m.get("target"),
                                             m.get("attempt"), m.get("distract", 0),
                                             m.get("puzzles_right", 0), m.get("hold_seconds"))
                        st.rerun()


# ================================================================ top bar
topbar = st.container(key="topbar")
bar_l, bar_r = topbar.columns([3, 1.25], vertical_alignment="center")
with bar_l:
    H('<div class="brand"><div class="logo">🧠</div><div>MindGym<small>Mental maths &amp; memory trainer</small></div></div>')
with bar_r:
    label = f":material/account_circle: {ss.user['username']}" if ss.user else ":material/login: Sign in"
    with st.popover(label, use_container_width=True):
        if ss.user:
            st.markdown(f"Signed in as **{html.escape(ss.user['username'])}**")
            st.caption("Every answer is saved to your account and analysed in Progress.")
            st.button("Log out", on_click=logout, use_container_width=True, icon=":material/logout:")
        else:
            st.markdown("**Save your progress**")
            st.caption("Free account · track your growth over weeks and months. "
                       "Anything you've practised this session is kept.")
            auth_forms("pop")
        if not store.permanent:
            st.caption("⚠️ Storage is temporary (resets when the app restarts).")

choice = st.segmented_control("Navigate", list(NAV), format_func=lambda p: NAV[p], key="nav",
                              label_visibility="collapsed")
page = choice or ss.last_page
ss.last_page = page


# ================================================================ HOME
def greeting():
    h = pd.Timestamp.now(tz=G.TZ).hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


PRESETS = [
    dict(icon="⚡", title="Daily warm-up", desc="10 easy mixed questions to switch your brain on.",
         kind="math", args=(["Addition", "Subtraction", "Multiplication", "Division"], "Easy", "Sprint", 10)),
    dict(icon="✖️", title="Multiplication sprint", desc="15 questions · 2-digit × 2-digit.",
         kind="math", args=(["Multiplication"], "Medium", "Sprint", 15)),
    dict(icon="⏱️", title="60-second blitz", desc="Mixed medium questions — how many can you get?",
         kind="math", args=(["Addition", "Multiplication", "Squares", "Percentages"], "Medium", "Timed", 60)),
    dict(icon="🧩", title="Memory under pressure", desc="Memorise digits, solve 5 puzzles, then recall.",
         kind="memory", args=(dict(length_mode="Adaptive", style="All at once", direction="Forward", speed=0.8,
                                   chunked=True, n_distract=5, topic="Mixed"),)),
]


def home_page():
    goal = int((ss.user or {}).get("daily_goal") or 30)
    tbl = pd.DataFrame()
    if ss.user:
        uid = ss.user["id"]
        raw = store.math_df(uid)
        mdf = A.prepare_math(G.with_day(raw)) if len(raw) else raw
        mem = G.with_day(store.memory_df(uid))
        days = (set(mdf["day"]) if len(mdf) else set()) | (set(mem["day"]) if len(mem) else set())
        streak, _ = G.streaks(days)
        today = int((mdf["day"] == G.today()).sum()) if len(mdf) else 0
        last7 = G.in_range(mdf, 7) if len(mdf) else mdf
        acc = last7.correct.mean() * 100 if len(last7) else None
        acc_lbl = "Accuracy · 7 days"
        span = int(mem[mem.correct.astype(bool)]["length"].max()) if len(mem) and mem.correct.astype(bool).any() else 0
        tbl = A.skill_table(G.in_range(mdf, 30)) if len(mdf) else tbl
        title = f"{greeting()}, {html.escape(ss.user['username'])}"
        if today >= goal:
            sub = "Daily goal done — anything more is a bonus. 🎉"
        elif today:
            sub = f"{goal - today} questions to go for today's goal. Keep the streak alive."
        else:
            sub = "A few focused minutes a day builds real number sense. Ready?"
    else:
        streak = 0
        today = len(ss.history)
        acc = (sum(h["correct"] for h in ss.history) / today * 100) if today else None
        acc_lbl = "Accuracy · session"
        span = max([m["length"] for m in ss.mem_history if m["correct"]], default=0)
        title = f"{greeting()} 👋"
        sub = "Sharpen your mental maths and working memory in 5 minutes a day."

    H(f'<div class="hero">{ring(today / goal, f"{min(today, 999)}", f"of {goal} today")}'
      f'<div><h2>{title}</h2><p>{sub}</p></div></div>')
    H(f'<div class="tiles">'
      f'<div class="tile"><div class="k">🔥 Day streak</div><div class="v">{streak}</div>'
      f'<div class="s">{"days in a row" if ss.user else "sign in to track"}</div></div>'
      f'<div class="tile"><div class="k">🎯 {acc_lbl.split(" · ")[0]}</div>'
      f'<div class="v">{f"{acc:.0f}%" if acc is not None else "—"}</div><div class="s">{acc_lbl.split(" · ")[1]}</div></div>'
      f'<div class="tile"><div class="k">🧩 Best digit span</div><div class="v">{span or "—"}</div>'
      f'<div class="s">digits recalled</div></div></div>')

    # personalised next step
    reco = None
    if len(tbl):
        t = tbl[tbl.Attempts >= 5]
        if len(t):
            weak = t.sort_values(["Accuracy", "Median (s)"], ascending=[True, False]).iloc[0]
            if weak["Accuracy"] < 85:
                reco = ("🎯", f"Focus on {weak['category']} · {weak['level']}",
                        f"Your accuracy here is {weak['Accuracy']:.0f}% over the last 30 days — your biggest win.",
                        ([weak["category"]], weak["level"], "Sprint", 10))
            else:
                best = t.sort_values("Accuracy", ascending=False).iloc[0]
                i = L.LEVELS.index(best["level"])
                if i < len(L.LEVELS) - 1:
                    nxt = L.LEVELS[i + 1]
                    reco = ("🚀", f"Level up: {best['category']} · {nxt}",
                            f"You're at {best['Accuracy']:.0f}% on {best['level']}. Time for a harder challenge.",
                            ([best["category"]], nxt, "Sprint", 10))
    if reco:
        H('<div class="sec">Recommended for you</div>')
        with st.container(key="card_reco"):
            c1, c2 = st.columns([3, 1.1], vertical_alignment="center")
            c1.markdown(f'<div class="reco"><div class="qs-ic">{reco[0]}</div><div><div class="qs-t" '
                        f'style="margin:0">{reco[1]}</div><div class="muted">{reco[2]}</div></div></div>',
                        unsafe_allow_html=True)
            c2.button("Start", type="primary", use_container_width=True, key="reco_go",
                      on_click=start_drill, args=reco[3], icon=":material/play_arrow:")

    H('<div class="sec">Quick start <small>one tap, no setup</small></div>')
    for row in (PRESETS[:2], PRESETS[2:]):
        cols = st.columns(2)
        for col, p in zip(cols, row):
            with col:
                with st.container(key=f"card_qs_{p['title'].split()[0].lower()}"):
                    H(f'<div class="qs-ic">{p["icon"]}</div><div class="qs-t">{p["title"]}</div>'
                      f'<div class="qs-d">{p["desc"]}</div>')
                    st.button("Start", key=f"qs_{p['title']}", use_container_width=True,
                              on_click=start_drill if p["kind"] == "math" else start_memory, args=p["args"])

    H('<div class="sec">Build your own</div>')
    c1, c2 = st.columns(2)
    c1.button("Custom maths round", on_click=go, args=("Math",), use_container_width=True,
              icon=":material/tune:")
    c2.button("Memory settings", on_click=go, args=("Memory",), use_container_width=True,
              icon=":material/psychology:")

    if not ss.user:
        H('<div class="sec">Save your progress</div>')
        with st.container(key="card_auth"):
            st.markdown("Create a **free account** to keep your history, streaks and a detailed analytics "
                        "dashboard of your growth over weeks and months.")
            auth_forms("home")


# ================================================================ MATH
def math_page():
    if ss.drill is not None and ss.drill.get("done"):
        show_summary()
        return
    if ss.drill is None:
        math_setup()
        return
    math_play()


def math_setup():
    page_head("Math drills", "Build a round", "Pick the skills, set the difficulty, choose how you want to play.")
    with st.container(key="card_setup"):
        cats = st.pills("What do you want to train?", list(L.CATEGORIES), selection_mode="multi",
                        default=["Multiplication"], format_func=lambda c: f"{L.CATEGORIES[c]}  {c}", key="m_cats")
        cats = cats or []
        level = st.segmented_control("Difficulty", L.LEVELS, default="Medium", key="m_level") or "Medium"
        if cats:
            H('<div class="lvl">' + "".join(
                f'<div><b>{c}</b> · {L.LEVEL_INFO[c][L.LEVELS.index(level)]}</div>' for c in cats) + "</div>")
        else:
            st.caption("Select at least one skill above.")
        c1, c2 = st.columns([1.15, 1])
        with c1:
            mode = st.segmented_control(
                "Mode", ["Sprint", "Timed", "Zen"], default="Sprint", key="m_mode",
                format_func=lambda m: {"Sprint": ":material/flag: Sprint", "Timed": ":material/timer: Timed",
                                       "Zen": ":material/spa: Zen"}[m]) or "Sprint"
            st.caption({"Sprint": "A fixed number of questions.", "Timed": "Answer as many as you can.",
                        "Zen": "No limits — stop whenever you like."}[mode])
        with c2:
            if mode == "Sprint":
                amount = st.select_slider("Questions", [5, 10, 15, 20, 30, 50], value=10)
            elif mode == "Timed":
                amount = st.select_slider("Seconds", [30, 60, 90, 120, 180, 300], value=60)
            else:
                amount = None
        st.button("Start round", type="primary", use_container_width=True, disabled=not cats,
                  on_click=start_drill, args=(cats, level, mode, amount), icon=":material/play_arrow:")


def math_play():
    d, q = ss.drill, ss.q

    if d["mode"] == "Timed":
        left = d["amount"] - (time.time() - d["start"])
        if left <= 0:
            d["done"] = True
            st.rerun()

    # ---- heads-up display
    if d["mode"] == "Sprint":
        where = f'Question {d["n"] + 1} <span>/ {d["amount"]}</span>'
    else:
        where = f'{d["n"]} <span>answered</span>'
    avg = sum(d["times"]) / len(d["times"]) if d["times"] else 0
    fire = ss.streak >= 3
    H(f'<div class="hud"><div class="where">{where}</div><div class="pills">'
      f'<span class="pill ok">✓ {d["right"]}</span>'
      f'<span class="pill {"fire" if fire else ""}">{"🔥" if fire else "↗"} {ss.streak} streak</span>'
      f'<span class="pill">⌀ {avg:.1f}s</span></div></div>')
    if d["mode"] == "Sprint":
        H(f'<div class="track"><div style="width:{d["n"] / d["amount"] * 100:.1f}%"></div></div>')
    elif d["mode"] == "Timed":
        components.html(
            f"""<div style="font-family:Inter,system-ui,sans-serif;display:flex;align-items:center;gap:12px">
            <div style="flex:1;height:7px;background:#e7e9f4;border-radius:99px;overflow:hidden">
            <div id=b style="height:100%;border-radius:99px;background:linear-gradient(90deg,#4f46e5,#7c3aed)"></div></div>
            <div id=t style="font-weight:700;font-size:15px;min-width:52px;text-align:right;color:#0f172a"></div></div>
            <script>let s={left:.2f};const T={d["amount"]};const e=document.getElementById('t'),b=document.getElementById('b');
            const f=()=>{{const v=Math.max(0,s);e.textContent='⏱ '+Math.ceil(v)+'s';b.style.width=(v/T*100)+'%';
            const c=v<10?'#e11d48':'#0f172a';e.style.color=c;if(v<10)b.style.background='#e11d48';s-=.25}};
            f();setInterval(f,250);</script>""",
            height=30,
        )

    if ss.feedback:
        feedback(*ss.feedback)

    H(f'<div class="q-card"><span class="chip">{L.CATEGORIES[q["category"]]} {q["category"]} · {q["level"]}</span>'
      f'<div class="q-text">{q["prompt"]} <span class="eq">=</span> ?</div></div>')

    with st.container(key="ansbox"):
        with st.form("answer", clear_on_submit=True, border=False):
            ans = st.text_input("Your answer", placeholder="Type your answer · Enter", label_visibility="collapsed")
            b1, b2 = st.columns([3, 1])
            submitted = b1.form_submit_button("Submit", type="primary", use_container_width=True)
            skipped = b2.form_submit_button("Skip", use_container_width=True)
    focus_input()

    c1, c2 = st.columns([3, 1], vertical_alignment="top")
    with c1:
        with st.expander("Show a trick for this type", icon=":material/lightbulb:"):
            H(f'<div class="tip">{L.TIPS[q["category"]]}</div>')
    if c2.button("End round", type="tertiary", icon=":material/stop_circle:", use_container_width=True):
        d["done"] = True
        st.rerun()

    if submitted or skipped:
        if submitted and L.parse_answer(ans) is None:
            ss.feedback = (False, "That wasn't a number — try again.")
            st.rerun()
        elapsed = time.time() - ss.q_start
        val = None if skipped else L.parse_answer(ans)
        ok = L.is_correct(q, val)
        d["n"] += 1
        d["right"] += ok
        d["times"].append(elapsed)
        ss.streak = ss.streak + 1 if ok else 0
        ss.best_streak = max(ss.best_streak, ss.streak)
        d["best"] = max(d.get("best", 0), ss.streak)
        ss.history.append(dict(time=pd.Timestamp.now(), category=q["category"], level=q["level"],
                               question=q["prompt"], answer=L.show_answer(q),
                               given=ans if not skipped else "(skipped)",
                               correct=ok, seconds=round(elapsed, 2)))
        if ss.user:
            h = ss.history[-1]
            store.add_math(ss.user["id"], h["category"], h["level"], h["question"], h["answer"],
                           h["given"], ok, h["seconds"])
        if ok:
            ss.feedback = (True, f"{q['prompt']} = <b>{L.show_answer(q)}</b> · {elapsed:.1f}s")
        else:
            given = "skipped" if skipped else f"you said {html.escape(ans)}"
            ss.feedback = (False, f"{q['prompt']} = <b>{L.show_answer(q)}</b> ({given})")
            d["wrong"].append((q["prompt"], L.show_answer(q), "—" if skipped else ans))

        if d["mode"] == "Sprint" and d["n"] >= d["amount"]:
            d["done"] = True
        else:
            new_question()
        st.rerun()


def grade(acc):
    if acc >= 90:
        return "Outstanding", "Fast, accurate, in control."
    if acc >= 75:
        return "Sharp", "Strong round — a few slips to tidy up."
    if acc >= 50:
        return "Solid effort", "You're building it. Review the misses below."
    return "Keep going", "Try an easier level to lock in the method first."


def show_summary():
    d = ss.drill
    n = d["n"]
    acc = (d["right"] / n * 100) if n else 0
    g, line = grade(acc) if n else ("Round ended", "No questions answered this time.")
    avg = (sum(d["times"]) / n) if n else 0
    best = min(d["times"]) if d["times"] else 0
    page_head("Math drills", "Round complete")
    H(f'<div class="result {"" if acc >= 50 else "bad"}"><div class="grade">{g}</div>'
      f'<div class="big">{d["right"]} / {n}</div><div class="line">{line}</div>'
      f'<div class="stats"><div><b>{acc:.0f}%</b>accuracy</div><div><b>{avg:.1f}s</b>avg / question</div>'
      f'<div><b>{best:.1f}s</b>fastest</div><div><b>{d.get("best", 0)}</b>best streak</div></div></div>')
    c1, c2 = st.columns(2)
    c1.button("Play again", type="primary", on_click=replay_drill, use_container_width=True,
              icon=":material/replay:")
    c2.button("Change settings", on_click=reset_drill, use_container_width=True, icon=":material/tune:")
    if d["wrong"]:
        H('<div class="sec">Review your misses</div>')
        st.dataframe(pd.DataFrame(d["wrong"], columns=["Question", "Correct answer", "Your answer"]),
                     hide_index=True, use_container_width=True)
    if not ss.user and n:
        st.caption("Sign in (top right) to save rounds like this and see your growth over time.")


# ================================================================ MEMORY
DISTRACT = [0, 3, 5, 10]


def memory_page():
    if ss.mem_phase == "idle":
        memory_setup()
        return
    cfg = ss.mem_cfg
    seq = ss.mem_seq
    if ss.mem_phase == "show":
        memory_show(cfg, seq)
    elif ss.mem_phase == "distract":
        memory_distract(seq)
    elif ss.mem_phase == "recall":
        memory_recall(cfg, seq)


def memory_setup():
    page_head("Memory · digit span", "How much can you hold?",
              "Memorise a string of digits, survive the distraction, then type it back.")
    if ss.mem_result:
        show_mem_result()

    with st.container(key="card_memsetup"):
        H('<div class="steps"><span class="step"><b>1</b>Memorise</span><span class="step"><i>→</i></span>'
          '<span class="step"><b>2</b>Solve puzzles</span><span class="step"><i>→</i></span>'
          '<span class="step"><b>3</b>Recall the digits</span></div>')
        c1, c2 = st.columns(2)
        with c1:
            length_mode = st.segmented_control("Length", ["Adaptive", "Fixed"], default="Adaptive",
                                               key="mem_lenmode") or "Adaptive"
            if length_mode == "Fixed":
                ss.mem_len = st.slider("Digits", 3, 40, 7, key="fixed_len")
            else:
                st.caption(f"Next string: **{ss.mem_len} digits** · +1 when right, −1 when you miss.")
        with c2:
            n_distract = st.segmented_control("Distraction before recall", DISTRACT, default=5, key="mem_nd",
                                              format_func=lambda n: "Off" if n == 0 else f"{n} puzzles")
            n_distract = 5 if n_distract is None else n_distract
            if n_distract:
                topic = st.pills("Puzzle type", PZ.TOPICS, default="Mixed", key="mem_topic") or "Mixed"
            else:
                topic = "Mixed"
                st.caption("Recall straight after the digits disappear.")
        with st.expander("Display options", icon=":material/tune:"):
            a, b = st.columns(2)
            style = a.segmented_control("Display", ["All at once", "One by one"], default="All at once",
                                        key="mem_style") or "All at once"
            direction = b.segmented_control("Recall order", ["Forward", "Backward"], default="Forward",
                                            key="mem_dir", help="Backward = type the digits in reverse (harder)") \
                or "Forward"
            if style == "All at once":
                speed = st.slider("Seconds per digit", 0.3, 2.0, 0.8, 0.1, help="Total viewing time = digits × this")
            else:
                speed = st.slider("Seconds each digit is shown", 0.4, 2.0, 1.0, 0.1)
            chunked = st.toggle("Group digits in 3s (chunking)", value=True, disabled=style == "One by one")
        cfg = dict(length_mode=length_mode, style=style, direction=direction, speed=speed,
                   chunked=chunked, n_distract=n_distract, topic=topic)
        st.button("Show me the digits", type="primary", use_container_width=True, on_click=start_memory,
                  args=(cfg,), icon=":material/visibility:")


def memory_show(cfg, seq):
    page_head("Memory", "Memorise", f"{len(seq)} digits · stay focused")
    box = st.empty()
    bar = st.progress(0.0)
    for i in (3, 2, 1):
        box.markdown(f'<div class="mem-card count">{i}</div>', unsafe_allow_html=True)
        time.sleep(0.6)
    if cfg["style"] == "All at once":
        text = L.chunk(seq) if cfg["chunked"] else seq
        box.markdown(f'<div class="mem-card">{text}</div>', unsafe_allow_html=True)
        total = len(seq) * cfg["speed"]
        steps = max(1, int(total / 0.1))
        for s in range(steps):
            bar.progress((s + 1) / steps)
            time.sleep(total / steps)
    else:
        for i, ch in enumerate(seq):
            box.markdown(f'<div class="mem-card">{ch}<div class="q-sub">{i + 1} / {len(seq)}</div></div>',
                         unsafe_allow_html=True)
            bar.progress((i + 1) / len(seq))
            time.sleep(cfg["speed"])
            box.markdown('<div class="mem-card">&nbsp;<div class="q-sub">&nbsp;</div></div>',
                         unsafe_allow_html=True)
            time.sleep(0.12)
    ss.mem_shown_at = time.time()
    if cfg.get("n_distract"):
        ss.pz = PZ.pick(cfg["n_distract"], cfg.get("topic", "Mixed"))
        ss.pz_i, ss.pz_right, ss.pz_fb = 0, 0, None
        ss.mem_phase = "distract"
    else:
        ss.pz, ss.pz_right = [], 0
        ss.mem_phase = "recall"
    st.rerun()


def memory_distract(seq):
    n = len(ss.pz)
    page_head("Distraction round", f"Puzzle {ss.pz_i + 1} of {n}", "Answer these — but don't let go of the digits.")
    H(f'<div class="vault">🔒 Holding <span class="dots">{"•" * len(seq)}</span> {len(seq)} digits</div>')
    H(f'<div class="track"><div style="width:{ss.pz_i / n * 100:.1f}%"></div></div>')
    if ss.pz_fb:
        feedback(*ss.pz_fb)
    p = ss.pz[ss.pz_i]
    with st.container(key="card_pz"):
        with st.form(f"pz_{ss.pz_i}", border=False):
            H(f'<span class="chip">{html.escape(p["topic"])}</span><div class="pz-q">{html.escape(p["q"])}</div>')
            choice = st.radio("Answer", p["options"], index=None, label_visibility="collapsed")
            sub = st.form_submit_button("Submit answer", type="primary", use_container_width=True)
    st.caption(f"{ss.pz_right} correct so far")
    if sub:
        if choice is None:
            ss.pz_fb = (False, "Pick an option first.")
            st.rerun()
        ok = choice == p["answer"]
        ss.pz_right += ok
        ss.pz_fb = (ok, ("Correct. " if ok else f"Answer: <b>{html.escape(p['answer'])}</b>. ")
                    + html.escape(p["why"]))
        ss.pz_i += 1
        if ss.pz_i >= n:
            ss.mem_phase = "recall"
        st.rerun()


def memory_recall(cfg, seq):
    rev = cfg["direction"] == "Backward"
    page_head("Recall", "Now — what was the string?",
              f"Type all {len(seq)} digits" + (" <b>in reverse order</b>." if rev else " in order."))
    if cfg.get("n_distract"):
        if ss.get("pz_fb"):
            feedback(*ss.pz_fb)
        H(f'<div class="pills" style="margin-bottom:10px"><span class="pill brand">🧠 Puzzles: '
          f'{ss.pz_right}/{len(ss.pz)} correct</span>'
          f'<span class="pill">⏱ {time.time() - ss.get("mem_shown_at", time.time()):.0f}s since the digits vanished</span></div>')
    H(f'<div class="vault">🔒 <span class="dots">{"•" * len(seq)}</span></div>')
    with st.container(key="recallbox"):
        with st.form("recall", clear_on_submit=True, border=False):
            attempt = st.text_input("Digits", placeholder="Type the digits", label_visibility="collapsed")
            sub = st.form_submit_button("Check my answer", type="primary", use_container_width=True)
    focus_input()
    if sub:
        target = seq[::-1] if rev else seq
        n_ok, marks, clean = L.compare_sequence(target, attempt)
        correct = clean == target
        hold = round(time.time() - ss.get("mem_shown_at", time.time()), 1)
        nd = len(ss.get("pz") or []) if cfg.get("n_distract") else 0
        pr = ss.get("pz_right", 0) if nd else 0
        ss.mem_history.append(dict(time=pd.Timestamp.now(), length=len(seq), direction=cfg["direction"],
                                   style=cfg["style"], correct=correct,
                                   digits_right=n_ok, sequence=seq, target=target, attempt=clean,
                                   distract=nd, puzzles_right=pr, hold_seconds=hold))
        if ss.user:
            store.add_memory(ss.user["id"], len(seq), cfg["direction"], cfg["style"], correct, n_ok,
                             target, clean, nd, pr, hold)
        ss.mem_result = dict(correct=correct, marks=marks, target=target, attempt=clean,
                             n_ok=n_ok, length=len(seq), distract=nd, puzzles_right=pr, hold=hold)
        ss.pz_fb = None
        if cfg["length_mode"] == "Adaptive":
            ss.mem_len = L.next_adaptive_length(ss.mem_len, correct)
        ss.mem_phase = "idle"
        st.rerun()


def show_mem_result():
    r = ss.mem_result
    extra = (f'<div><b>{r["puzzles_right"]}/{r["distract"]}</b>puzzles right</div>'
             f'<div><b>{r["hold"]:.0f}s</b>held in memory</div>') if r.get("distract") else ""
    if r["correct"]:
        head, big, line = "Perfect recall", f'{r["length"]} / {r["length"]}', "Every digit in the right place."
    else:
        head, big = "Not quite", f'{r["n_ok"]} / {r["length"]}'
        line = f'digits in the right place · you typed <b>{html.escape(r["attempt"] or "—")}</b>'
    H(f'<div class="result {"" if r["correct"] else "bad"}"><div class="grade">{head}</div>'
      f'<div class="big">{big}</div><div class="line">{line}</div>'
      f'<div class="stats"><div><b>{ss.mem_len}</b>next length</div>{extra}</div></div>')
    chips = "".join(f'<span class="digit {"d-ok" if ok else "d-bad"}">{ch}</span>' for ch, ok in r["marks"])
    H('<div class="muted" style="margin:-4px 0 4px">Expected answer · '
      '<span style="color:#047857;font-weight:600">green</span> = you got that position right</div>'
      f'<div style="margin:0 0 16px">{chips}</div>')


# ================================================================ PROGRESS
def progress_page():
    page_head("Progress", "Your performance",
              "Every answer, measured — accuracy, speed, consistency and memory over time.")
    if ss.user:
        growth_page()
        return
    st.info("You're playing as a guest, so only this session is shown. **Sign in (top right)** — it's free — "
            "to track your growth over weeks and months. Anything you've done this session is kept.")
    session_progress()


RANGES = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": None}


def growth_page():
    uid = ss.user["id"]
    raw = store.math_df(uid)
    mdf_all = A.prepare_math(G.with_day(raw)) if len(raw) else raw
    memdf_all = G.with_day(store.memory_df(uid))
    if not len(mdf_all) and not len(memdf_all):
        st.info("No practice saved yet. Play a round of Math Drills or Memory — every answer is saved "
                "to your account and analysed here.")
        return

    # ---------------- controls
    c1, c2 = st.columns([2, 3])
    rng = c1.selectbox("Period", list(RANGES), index=1)
    days = RANGES[rng]
    skills_all = sorted(mdf_all["category"].unique()) if len(mdf_all) else []
    pick = c2.multiselect("Skills", skills_all, placeholder="All skills")
    mdf = mdf_all[mdf_all.category.isin(pick)] if pick and len(mdf_all) else mdf_all
    m_cur, m_prev = A.periods(mdf, days) if len(mdf) else (mdf, None)
    mem = G.in_range(memdf_all, days) if len(memdf_all) else memdf_all

    k = A.kpis(m_cur) if len(mdf) else A.kpis(None)
    kp = A.kpis(m_prev) if m_prev is not None and len(m_prev) else None
    all_days = (set(mdf_all["day"]) if len(mdf_all) else set()) | (set(memdf_all["day"]) if len(memdf_all) else set())
    cur_streak, best_streak = G.streaks(all_days)

    # ---------------- headline KPIs (vs previous period of equal length)
    st.caption(f"{rng}" + (" · compared with the previous period of the same length" if kp else ""))
    r = st.columns(6)
    r[0].metric("Questions", k["questions"], A.delta(k, kp, "questions", "{:+.0f}"))
    r[1].metric("Accuracy", f"{k['accuracy']:.1f}%" if k["accuracy"] is not None else "–",
                (A.delta(k, kp, "accuracy", "{:+.1f} pts")))
    r[2].metric("Median time", f"{k['median_s']:.2f}s" if k["median_s"] else "–",
                A.delta(k, kp, "median_s", "{:+.2f}s"), delta_color="inverse",
                help="Median seconds per correct answer")
    r[3].metric("Correct / min", f"{k['fluency']:.2f}" if k["fluency"] else "–",
                A.delta(k, kp, "fluency", "{:+.2f}"), help="Fluency: correct answers per minute of thinking time")
    r[4].metric("Active days", k["days"], A.delta(k, kp, "days", "{:+.0f}"))
    r[5].metric("🔥 Streak", f"{cur_streak}d", help=f"Longest ever: {best_streak} days")

    # ---------------- daily goal
    goal = int(ss.user.get("daily_goal") or 30)
    done_today = int((mdf_all["day"] == G.today()).sum()) if len(mdf_all) else 0
    g1, g2 = st.columns([4, 1])
    g1.progress(min(1.0, done_today / goal), text=f"Today's goal: {done_today} / {goal} questions")
    new_goal = g2.number_input("Daily goal", 5, 500, goal, 5, label_visibility="collapsed", help="Questions per day")
    if new_goal != goal:
        store.set_goal(uid, new_goal)
        ss.user["daily_goal"] = new_goal
        st.rerun()

    tbl = A.skill_table(m_cur) if len(m_cur) else pd.DataFrame()
    notes = A.insights(m_cur if len(m_cur) else None, mem, tbl)
    if notes:
        with st.container(key="card_insights"):
            st.markdown("**🔎 Key insights**")
            for n in notes:
                st.markdown(f"- {n}")

    tabs = st.tabs(["📊 Overview", "🧠 Skills", "⚡ Speed", "🎯 Accuracy & errors", "🕒 Habits", "🧩 Memory", "🗂 Data"])

    # ================= OVERVIEW
    with tabs[0]:
        st.markdown("##### Practice calendar · last 13 weeks")
        counts = mdf_all.groupby("day").size().to_dict() if len(mdf_all) else {}
        st.markdown(G.heatmap_html(counts, days=91, goal=goal), unsafe_allow_html=True)
        ds = A.daily_series(m_cur) if len(m_cur) else pd.DataFrame()
        if len(ds):
            st.markdown("##### Daily trend")
            st.caption("Thin line = that day · thick line = 7-day rolling average.")
            a, b = st.columns(2)
            with a:
                st.markdown("**Accuracy %**")
                st.line_chart(ds[["Accuracy %", "Accuracy % · 7d avg"]], height=220)
            with b:
                st.markdown("**Median time per correct answer (s)** — lower is better")
                st.line_chart(ds[["Median time (s)", "Median time (s) · 7d avg"]], height=220)
            a, b = st.columns(2)
            with a:
                st.markdown("**Fluency (correct / min)**")
                st.line_chart(ds[["Correct / min", "Correct / min · 7d avg"]], height=200)
            with b:
                st.markdown("**Questions per day**")
                st.bar_chart(ds["Questions"], height=200)
            st.markdown("##### Week by week")
            st.dataframe(A.weekly_summary(m_cur), hide_index=True, use_container_width=True)
        else:
            st.caption("No math practice in this period.")

    # ================= SKILLS
    with tabs[1]:
        if len(tbl):
            st.markdown("##### Skill report card")
            st.caption("**Consistency** = how steady your times are (100 = identical every time). "
                       "**Speed trend** = change in daily median time per week (negative = getting faster). "
                       "**Mastered** = ≥90% accuracy, consistency ≥50 and 20+ attempts.")
            st.dataframe(
                tbl.drop(columns=["category", "level"]), hide_index=True, use_container_width=True,
                column_config={
                    "Accuracy": st.column_config.ProgressColumn("Accuracy", format="%.0f%%", min_value=0, max_value=100),
                    "Consistency": st.column_config.ProgressColumn("Consistency", format="%d", min_value=0, max_value=100),
                    "Speed trend %/wk": st.column_config.NumberColumn("Speed trend", format="%+.1f%%/wk"),
                    "Per min": st.column_config.NumberColumn("Correct/min", format="%.1f"),
                })
            strong, weak = A.strengths_weaknesses(tbl)
            if strong:
                a, b = st.columns(2)
                a.success("**Strongest**\n\n" + "\n".join(f"- {s}" for s in strong))
                b.error("**Focus next**\n\n" + "\n".join(f"- {s}" for s in weak))

            st.markdown("##### Deep dive into one skill")
            sk = st.selectbox("Skill", tbl["Skill"].tolist())
            g = m_cur[m_cur.skill == sk]
            row = tbl[tbl.Skill == sk].iloc[0]
            q = st.columns(5)
            q[0].metric("Attempts", int(row["Attempts"]))
            q[1].metric("Accuracy", f"{row['Accuracy']:.1f}%")
            q[2].metric("Median", f"{row['Median (s)']}s" if pd.notna(row["Median (s)"]) else "–")
            q[3].metric("Personal best", f"{row['Best (s)']}s" if pd.notna(row["Best (s)"]) else "–")
            q[4].metric("Status", row["Status"].split(" ", 1)[1])
            dsk = A.daily_series(g)
            if len(dsk.dropna(subset=["Median time (s)"])) >= 2:
                st.line_chart(dsk[["Median time (s)", "Median time (s) · 7d avg"]], height=200)
            tvn = G.then_vs_now(g, min_attempts=10)
            if len(tvn):
                t = tvn.iloc[0]
                st.info(f"First 30% of attempts → latest 30%: accuracy **{t['acc_then']}% → {t['acc_now']}%**, "
                        f"time **{t['sec_then']}s → {t['sec_now']}s**.")
            st.caption("Slowest correct answers in this skill — the patterns worth drilling:")
            slow = g[g.correct].sort_values("seconds", ascending=False).head(5)
            st.dataframe(slow[["question", "answer", "seconds"]].rename(
                columns={"question": "Question", "answer": "Answer", "seconds": "Seconds"}),
                hide_index=True, use_container_width=True)
        else:
            st.caption("No math practice in this period.")

    # ================= SPEED
    with tabs[2]:
        if len(m_cur) and m_cur.correct.any():
            a, b = st.columns(2)
            with a:
                st.markdown("##### How long your correct answers take")
                st.bar_chart(A.speed_distribution(m_cur), height=240)
            with b:
                st.markdown("##### Speed vs accuracy")
                st.caption("Your answers split into four groups by how fast you were.")
                pace = A.speed_accuracy_by_pace(m_cur)
                if len(pace):
                    st.dataframe(pace, hide_index=True, use_container_width=True)
                    st.bar_chart(pace.set_index("Pace")["Accuracy %"], height=150)
                else:
                    st.caption("Needs 20+ answers.")
            st.markdown("##### Weekly median time by skill")
            cs = A.category_speed_by_period(m_cur)
            if len(cs) >= 2:
                st.line_chart(cs, height=260)
            elif len(cs):
                st.dataframe(cs, use_container_width=True)
            p = st.columns(3)
            c = m_cur[m_cur.correct]
            p[0].metric("Fastest answer", f"{c['seconds'].min():.2f}s")
            p[1].metric("Median", f"{c['seconds'].median():.2f}s")
            p[2].metric("90th percentile", f"{c['seconds'].quantile(.9):.2f}s",
                        help="90% of your correct answers are faster than this")
        else:
            st.caption("No correct answers in this period yet.")

    # ================= ACCURACY & ERRORS
    with tabs[3]:
        if len(m_cur):
            eb = A.error_breakdown(m_cur)
            e = st.columns(4)
            wrong = int((~m_cur.correct).sum())
            e[0].metric("Mistakes", wrong)
            e[1].metric("Skip rate", f"{k['skip_rate']:.1f}%" if k["skip_rate"] is not None else "–")
            e[2].metric("Near misses", int(eb.loc["Near miss (≤2%)", "Count"]) if "Near miss (≤2%)" in eb.index else 0,
                        help="Wrong but within 2% of the answer — method right, arithmetic slip")
            e[3].metric("Longest correct run", k["best_streak"])
            if len(eb):
                a, b = st.columns([3, 2])
                with a:
                    st.markdown("##### Types of mistakes")
                    st.bar_chart(eb["Count"], height=240, horizontal=True)
                with b:
                    st.markdown("##### ")
                    st.dataframe(eb, use_container_width=True)
                st.caption("**Single-digit slip**: one digit wrong · **Transposed**: two digits swapped · "
                           "**Place-value**: off by ×10/×100 · **Near miss**: within 2% · "
                           "**Calculation error**: everything else.")
                st.markdown("##### Mistakes by skill")
                st.dataframe(A.error_by_skill(m_cur), use_container_width=True)
                st.markdown("##### Questions you miss most")
                st.dataframe(A.most_missed(m_cur), hide_index=True, use_container_width=True)
            else:
                st.success("No mistakes in this period. 👏")
        else:
            st.caption("No math practice in this period.")

    # ================= HABITS
    with tabs[4]:
        if len(m_cur):
            a, b = st.columns(2)
            with a:
                st.markdown("##### Time of day")
                tod = A.time_of_day(m_cur)
                st.dataframe(tod, hide_index=True, use_container_width=True)
                if len(tod):
                    st.bar_chart(tod.set_index("When")["Accuracy %"], height=180)
            with b:
                st.markdown("##### Day of week")
                wd = A.weekday_profile(m_cur)
                st.dataframe(wd, hide_index=True, use_container_width=True)
                if len(wd):
                    st.bar_chart(wd.set_index("When")["Questions"], height=180)
            st.markdown("##### Stamina within a session")
            st.caption("Accuracy and speed as a session goes on — a drop means fatigue.")
            fat = A.fatigue_curve(m_cur)
            if len(fat):
                st.dataframe(fat, hide_index=True, use_container_width=True)
            st.markdown("##### Sessions")
            st.caption(f"A new session starts after a {A.SESSION_GAP_MIN}-minute break.")
            st.dataframe(A.session_stats(m_cur), hide_index=True, use_container_width=True)
        else:
            st.caption("No math practice in this period.")

    # ================= MEMORY
    with tabs[5]:
        if len(mem):
            mk = A.memory_kpis(mem)
            q = st.columns(5)
            q[0].metric("Attempts", mk["attempts"])
            q[1].metric("Perfect recall", f"{mk['success']:.0f}%")
            q[2].metric("Best span", mk["best_span"])
            q[3].metric("Reliable span", mk["reliable_span"], help="Longest length you get right ≥75% of the time")
            q[4].metric("Digit accuracy", f"{mk['digit_accuracy']:.0f}%" if mk["digit_accuracy"] else "–")
            md = A.memory_daily(mem)
            if len(md):
                st.markdown("##### Span over time")
                st.line_chart(md[["Best span", "Avg length tried"]], height=220)
            a, b = st.columns(2)
            with a:
                st.markdown("##### Success by length")
                bl = A.memory_by_length(mem)
                st.bar_chart(bl["Success %"], height=200)
                st.dataframe(bl, use_container_width=True)
            with b:
                st.markdown("##### Where you lose digits")
                pc = A.memory_position_curve(mem)
                if len(pc):
                    st.caption("Accuracy at each part of the sequence (start → end).")
                    st.bar_chart(pc, height=200)
                else:
                    st.caption("Shows up after a few more memory rounds.")
            de = A.distraction_effect(mem)
            if len(de):
                st.markdown("##### Effect of distraction")
                st.caption("How well the digits survive when you solve puzzles before recalling them. "
                           "**Avg hold** = seconds between the digits disappearing and you typing them back.")
                st.dataframe(de, hide_index=True, use_container_width=True)
                if len(de) >= 2:
                    st.bar_chart(de.set_index("Condition")["Digit accuracy %"], height=180)
            st.markdown("##### By display mode")
            st.dataframe(A.memory_by_mode(mem), hide_index=True, use_container_width=True)
        else:
            st.caption("No memory practice in this period.")

    # ================= DATA
    with tabs[6]:
        if len(mdf_all):
            show = mdf_all.copy()
            show["time"] = show["ts"].dt.tz_convert(G.TZ).dt.strftime("%Y-%m-%d %H:%M:%S")
            cols = ["time", "category", "level", "question", "answer", "given", "correct", "seconds", "error_type", "session"]
            st.dataframe(show[cols].iloc[::-1].head(1000), hide_index=True, use_container_width=True)
            st.download_button("⬇ Math history (CSV)", show[cols].to_csv(index=False), "mindgym_math.csv", "text/csv")
        if len(memdf_all):
            st.download_button("⬇ Memory history (CSV)", memdf_all.drop(columns=["user_id"]).to_csv(index=False),
                               "mindgym_memory.csv", "text/csv")


def session_progress():
    if not ss.history and not ss.mem_history:
        st.info("Play a round of Math Drills or Memory and your stats will show up here.")
        return

    if ss.history:
        df = pd.DataFrame(ss.history)
        st.subheader("Math")
        summ = (df.groupby(["category", "level"])
                  .agg(attempts=("correct", "size"), accuracy=("correct", "mean"), avg_seconds=("seconds", "mean"))
                  .reset_index())
        summ["accuracy"] = (summ["accuracy"] * 100).round(0).astype(int).astype(str) + "%"
        summ["avg_seconds"] = summ["avg_seconds"].round(1)
        st.dataframe(summ, hide_index=True, use_container_width=True)

        st.caption("Seconds per question (lower = faster)")
        st.line_chart(df.reset_index()[["index", "seconds"]].set_index("index"), height=220)

        slow = df[df.correct].sort_values("seconds", ascending=False).head(5)
        if len(slow):
            st.caption("Your slowest correct answers — good ones to drill again")
            st.dataframe(slow[["question", "answer", "seconds"]], hide_index=True, use_container_width=True)

        st.download_button("⬇ Download math history (CSV)", df.to_csv(index=False), "mindgym_math.csv",
                           "text/csv")

    if ss.mem_history:
        mdf = pd.DataFrame(ss.mem_history)
        st.subheader("Memory")
        c1, c2, c3 = st.columns(3)
        c1.metric("Attempts", len(mdf))
        c2.metric("Perfect recalls", int(mdf.correct.sum()))
        c3.metric("Best span", int(mdf[mdf.correct].length.max()) if mdf.correct.any() else 0)
        st.caption("Length of each attempt")
        st.bar_chart(mdf.reset_index()[["index", "length"]].set_index("index"), height=200)
        st.download_button("⬇ Download memory history (CSV)", mdf.to_csv(index=False), "mindgym_memory.csv",
                           "text/csv")


# ================================================================ router
{"Home": home_page, "Math": math_page, "Memory": memory_page, "Progress": progress_page}[page]()
