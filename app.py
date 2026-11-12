"""MindGym — mental maths & memory trainer (Streamlit)."""
import os
import random
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import analytics as A
import growth as G
import logic as L
from db import Store

st.set_page_config(page_title="MindGym", page_icon="🧠", layout="centered")


@st.cache_resource
def get_store():
    url = None
    try:
        url = st.secrets.get("DATABASE_URL")
    except Exception:
        pass
    return Store(url or os.environ.get("DATABASE_URL"))


store = get_store()

# ---------------------------------------------------------------- style
st.markdown(
    """
<style>
.block-container {padding-top: 2rem; max-width: 760px;}
.q-card {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  color: #f8fafc; border-radius: 18px; padding: 34px 20px; text-align: center;
  font-size: 2.6rem; font-weight: 700; letter-spacing: .5px; margin: 8px 0 14px;
  font-variant-numeric: tabular-nums;
}
.q-sub {font-size: .9rem; font-weight: 500; opacity: .65; margin-top: 6px; letter-spacing: 0;}
.mem-card {
  background: #fef3c7; color: #78350f; border-radius: 18px; padding: 40px 16px;
  text-align: center; font-size: 2.8rem; font-weight: 800; letter-spacing: 6px;
  font-family: ui-monospace, Menlo, monospace; word-break: break-all;
}
.fb-ok  {background:#dcfce7; color:#14532d; padding:10px 14px; border-radius:10px;}
.fb-bad {background:#fee2e2; color:#7f1d1d; padding:10px 14px; border-radius:10px;}
.digit {display:inline-block; width:1.6em; text-align:center; font-family:ui-monospace,Menlo,monospace;
        font-size:1.6rem; font-weight:700; border-radius:6px; margin:2px; padding:4px 0;}
.d-ok {background:#dcfce7; color:#14532d;} .d-bad {background:#fee2e2; color:#7f1d1d;}
.tip {background:#eff6ff; color:#1e3a8a; padding:10px 14px; border-radius:10px; font-size:.92rem;}
</style>
""",
    unsafe_allow_html=True,
)


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


# ---------------------------------------------------------------- state
ss = st.session_state
defaults = dict(
    history=[],          # math attempts
    mem_history=[],      # memory attempts
    drill=None,          # active drill config
    q=None, q_start=0.0, feedback=None, streak=0, best_streak=0,
    mem_phase="idle", mem_seq="", mem_len=5, mem_result=None,
    user=None,
)
for k, v in defaults.items():
    ss.setdefault(k, v)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🧠 MindGym")
    page = st.radio("Go to", ["🔢 Math Drills", "🧩 Memory", "📈 Progress"], label_visibility="collapsed")
    st.divider()

    if ss.user:
        st.markdown(f"👤 **{ss.user['username']}**")
        if st.button("Log out", use_container_width=True):
            for k in ("user", "history", "mem_history", "drill", "q", "feedback", "mem_result"):
                ss[k] = defaults[k]
            ss.streak = ss.best_streak = 0
            st.rerun()
    else:
        st.markdown("**Save your progress**")
        st.caption("Make a free account to track your growth over weeks and months.")
        t_login, t_signup = st.tabs(["Log in", "Sign up"])
        with t_login:
            with st.form("login"):
                u = st.text_input("Username", key="li_u")
                p = st.text_input("Password", type="password", key="li_p")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    user = store.login(u, p)
                    if user:
                        ss.user = user
                        st.rerun()
                    else:
                        st.error("Wrong username or password.")
        with t_signup:
            with st.form("signup"):
                u = st.text_input("Choose a username", key="su_u")
                p = st.text_input("Password (6+ characters)", type="password", key="su_p")
                p2 = st.text_input("Repeat password", type="password", key="su_p2")
                if st.form_submit_button("Create account", type="primary", use_container_width=True):
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
                                                 m.get("attempt"))
                            st.rerun()
        st.caption("Playing as guest — progress is lost when you close the tab.")

    st.divider()
    total = len(ss.history)
    acc = (sum(h["correct"] for h in ss.history) / total * 100) if total else 0
    st.caption("THIS SESSION")
    c1, c2 = st.columns(2)
    c1.metric("Questions", total)
    c2.metric("Accuracy", f"{acc:.0f}%")
    best_span = max([m["length"] for m in ss.mem_history if m["correct"]], default=0)
    c1.metric("Best streak", ss.best_streak)
    c2.metric("Digit span", best_span)
    if not store.permanent:
        st.caption("⚠️ Storage: temporary database (resets when the app restarts).")


# ================================================================ MATH
def new_question():
    d = ss.drill
    cat = random.choice(d["cats"])
    ss.q = L.make_question(cat, d["level"])
    ss.q_start = time.time()


def finish_drill():
    ss.drill["done"] = True


def math_page():
    st.header("🔢 Math Drills")

    # ---------- setup screen
    if ss.drill is None or ss.drill.get("done"):
        if ss.drill and ss.drill.get("done"):
            show_summary()
            st.divider()

        st.subheader("Set up a round")
        cats = st.multiselect(
            "What do you want to practise? (pick one or mix several)",
            list(L.CATEGORIES),
            default=["Multiplication"],
            format_func=lambda c: f"{L.CATEGORIES[c]}  {c}",
        )
        level = st.radio("Difficulty", L.LEVELS, index=1, horizontal=True)
        if cats:
            for c in cats:
                st.caption(f"**{c}** · {level}: {L.LEVEL_INFO[c][L.LEVELS.index(level)]}")

        c1, c2 = st.columns(2)
        mode = c1.radio("Mode", ["Sprint", "Timed", "Zen"], horizontal=True,
                        help="Sprint: fixed number of questions · Timed: beat the clock · Zen: endless")
        if mode == "Sprint":
            amount = c2.select_slider("Questions", [5, 10, 15, 20, 30, 50], value=10)
        elif mode == "Timed":
            amount = c2.select_slider("Seconds", [30, 60, 90, 120, 180, 300], value=60)
        else:
            amount = None
            c2.write(""); c2.caption("Practise as long as you like, end any time.")

        if st.button("▶  Start", type="primary", use_container_width=True, disabled=not cats):
            ss.drill = dict(cats=cats, level=level, mode=mode, amount=amount,
                            start=time.time(), n=0, right=0, times=[], done=False, wrong=[])
            ss.streak, ss.feedback = 0, None
            new_question()
            st.rerun()
        return

    # ---------- playing
    d, q = ss.drill, ss.q

    # time check for timed mode
    if d["mode"] == "Timed":
        left = d["amount"] - (time.time() - d["start"])
        if left <= 0:
            finish_drill(); st.rerun()

    # header row
    c1, c2, c3, c4 = st.columns(4)
    if d["mode"] == "Sprint":
        c1.metric("Question", f"{d['n'] + 1}/{d['amount']}")
    else:
        c1.metric("Answered", d["n"])
    c2.metric("Correct", d["right"])
    c3.metric("Streak", f"🔥 {ss.streak}" if ss.streak >= 3 else ss.streak)
    if d["mode"] == "Timed":
        with c4:
            # client-side live countdown (display only; server enforces the limit)
            components.html(
                f"""<div style="font-family:sans-serif;color:#64748b;font-size:14px">Time left</div>
                <div id=t style="font-family:sans-serif;font-size:34px;font-weight:600;color:#0f172a"></div>
                <script>let s={left:.1f};const e=document.getElementById('t');
                const f=()=>{{e.textContent=Math.max(0,Math.ceil(s))+'s';e.style.color=s<10?'#dc2626':'#0f172a';s-=.25}};
                f();setInterval(f,250);</script>""",
                height=80,
            )
    else:
        avg = sum(d["times"]) / len(d["times"]) if d["times"] else 0
        c4.metric("Avg time", f"{avg:.1f}s")

    if d["mode"] == "Sprint":
        st.progress(d["n"] / d["amount"])

    # feedback from previous answer
    if ss.feedback:
        ok, text = ss.feedback
        st.markdown(f'<div class="{"fb-ok" if ok else "fb-bad"}">{text}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="q-card">{q["prompt"]} = ?'
        f'<div class="q-sub">{L.CATEGORIES[q["category"]]} {q["category"]} · {q["level"]}</div></div>',
        unsafe_allow_html=True,
    )

    with st.form("answer", clear_on_submit=True):
        ans = st.text_input("Your answer", placeholder="Type and press Enter", label_visibility="collapsed")
        b1, b2 = st.columns([3, 1])
        submitted = b1.form_submit_button("Submit ↵", type="primary", use_container_width=True)
        skipped = b2.form_submit_button("Skip", use_container_width=True)

    focus_input()

    with st.expander("💡 Trick for this type"):
        st.markdown(f'<div class="tip">{L.TIPS[q["category"]]}</div>', unsafe_allow_html=True)

    if st.button("⏹ End round"):
        finish_drill(); st.rerun()

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
        ss.history.append(dict(time=pd.Timestamp.now(), category=q["category"], level=q["level"],
                               question=q["prompt"], answer=L.show_answer(q),
                               given=ans if not skipped else "(skipped)",
                               correct=ok, seconds=round(elapsed, 2)))
        if ss.user:
            h = ss.history[-1]
            store.add_math(ss.user["id"], h["category"], h["level"], h["question"], h["answer"],
                           h["given"], ok, h["seconds"])
        if ok:
            ss.feedback = (True, f"✅ {q['prompt']} = <b>{L.show_answer(q)}</b> · {elapsed:.1f}s")
        else:
            given = "skipped" if skipped else f"you said {ans}"
            ss.feedback = (False, f"❌ {q['prompt']} = <b>{L.show_answer(q)}</b> ({given})")
            d["wrong"].append((q["prompt"], L.show_answer(q), "—" if skipped else ans))

        if d["mode"] == "Sprint" and d["n"] >= d["amount"]:
            finish_drill()
        else:
            new_question()
        st.rerun()


def show_summary():
    d = ss.drill
    n = d["n"]
    st.success("Round complete! 🎉")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{d['right']}/{n}")
    c2.metric("Accuracy", f"{(d['right'] / n * 100) if n else 0:.0f}%")
    c3.metric("Avg time / question", f"{(sum(d['times']) / n) if n else 0:.1f}s")
    if d["wrong"]:
        st.markdown("**Review your misses**")
        st.dataframe(pd.DataFrame(d["wrong"], columns=["Question", "Correct answer", "Your answer"]),
                     hide_index=True, use_container_width=True)


# ================================================================ MEMORY
def memory_page():
    st.header("🧩 Memory — Digit Span")
    st.caption("A string of digits appears for a few seconds. Memorise it, then type it back.")

    if ss.mem_phase == "idle":
        c1, c2 = st.columns(2)
        length_mode = c1.radio("Length", ["Adaptive", "Fixed"], horizontal=True,
                               help="Adaptive: +1 digit when you get it right, −1 when you miss")
        if length_mode == "Fixed":
            ss.mem_len = c2.slider("Number of digits", 3, 40, 7, key="fixed_len")
        else:
            c2.metric("Next length", ss.mem_len)
        c3, c4 = st.columns(2)
        style = c3.radio("Display", ["All at once", "One by one"], horizontal=True)
        direction = c4.radio("Recall", ["Forward", "Backward"], horizontal=True,
                             help="Backward = type the digits in reverse order (harder)")
        if style == "All at once":
            speed = st.slider("Seconds per digit", 0.3, 2.0, 0.8, 0.1,
                              help="Total viewing time = digits × this")
        else:
            speed = st.slider("Seconds each digit is shown", 0.4, 2.0, 1.0, 0.1)
        chunked = st.checkbox("Group digits in 3s (chunking)", value=True, disabled=style == "One by one")

        if ss.mem_result:
            show_mem_result()

        if st.button("▶  Show me the digits", type="primary", use_container_width=True):
            ss.mem_cfg = dict(length_mode=length_mode, style=style, direction=direction,
                              speed=speed, chunked=chunked)
            ss.mem_seq = L.make_sequence(ss.mem_len)
            ss.mem_result = None
            ss.mem_phase = "show"
            st.rerun()
        return

    cfg = ss.mem_cfg
    seq = ss.mem_seq

    if ss.mem_phase == "show":
        box = st.empty()
        bar = st.progress(0.0)
        for i in (3, 2, 1):
            box.markdown(f'<div class="mem-card" style="opacity:.5">{i}</div>', unsafe_allow_html=True)
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
                box.markdown(f'<div class="mem-card">{ch}<div class="q-sub" style="letter-spacing:0">'
                             f'{i + 1} / {len(seq)}</div></div>', unsafe_allow_html=True)
                bar.progress((i + 1) / len(seq))
                time.sleep(cfg["speed"])
                box.markdown('<div class="mem-card">&nbsp;<div class="q-sub">&nbsp;</div></div>',
                             unsafe_allow_html=True)
                time.sleep(0.12)
        ss.mem_phase = "recall"
        ss.mem_shown_at = time.time()
        st.rerun()

    if ss.mem_phase == "recall":
        st.markdown(f'<div class="mem-card" style="background:#f1f5f9;color:#94a3b8">'
                    f'{"•" * len(seq)}</div>', unsafe_allow_html=True)
        label = f"Type the {len(seq)} digits" + (" **in reverse order**" if cfg["direction"] == "Backward" else "")
        st.markdown(label)
        with st.form("recall", clear_on_submit=True):
            attempt = st.text_input("Digits", placeholder="e.g. 4829...", label_visibility="collapsed")
            sub = st.form_submit_button("Check ↵", type="primary", use_container_width=True)
        focus_input()
        if sub:
            target = seq[::-1] if cfg["direction"] == "Backward" else seq
            n_ok, marks, clean = L.compare_sequence(target, attempt)
            correct = clean == target
            ss.mem_history.append(dict(time=pd.Timestamp.now(), length=len(seq), direction=cfg["direction"],
                                       style=cfg["style"], correct=correct,
                                       digits_right=n_ok, sequence=seq, target=target, attempt=clean))
            if ss.user:
                store.add_memory(ss.user["id"], len(seq), cfg["direction"], cfg["style"], correct, n_ok,
                                 target, clean)
            ss.mem_result = dict(correct=correct, marks=marks, target=target, attempt=clean,
                                 n_ok=n_ok, length=len(seq))
            if cfg["length_mode"] == "Adaptive":
                ss.mem_len = L.next_adaptive_length(ss.mem_len, correct)
            ss.mem_phase = "idle"
            st.rerun()


def show_mem_result():
    r = ss.mem_result
    if r["correct"]:
        st.markdown(f'<div class="fb-ok">✅ Perfect — all {r["length"]} digits!</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fb-bad">❌ {r["n_ok"]}/{r["length"]} digits in the right place. '
                    f'You typed: <code>{r["attempt"] or "—"}</code></div>', unsafe_allow_html=True)
    html = "".join(f'<span class="digit {"d-ok" if ok else "d-bad"}">{ch}</span>' for ch, ok in r["marks"])
    st.markdown(f"<div style='margin:10px 0 16px'>{html}</div>", unsafe_allow_html=True)


# ================================================================ PROGRESS
def progress_page():
    st.header("📈 Progress")
    if ss.user:
        growth_page()
        return
    st.info("You're playing as a guest, so only this session is shown. **Sign up in the sidebar** "
            "(it's free) to track your growth over weeks and months — anything you've done this session is kept.")
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
        with st.container(border=True):
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


# ---------------------------------------------------------------- router
if page.startswith("🔢"):
    math_page()
elif page.startswith("🧩"):
    memory_page()
else:
    progress_page()
