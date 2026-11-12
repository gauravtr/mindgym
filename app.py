"""MindGym — mental maths & memory trainer (Streamlit)."""
import os
import random
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
                                                 m["correct"], m["digits_right"])
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
                                       digits_right=n_ok, sequence=seq, attempt=clean))
            if ss.user:
                store.add_memory(ss.user["id"], len(seq), cfg["direction"], cfg["style"], correct, n_ok)
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
    mdf = G.with_day(store.math_df(uid))
    memdf = G.with_day(store.memory_df(uid))
    if not len(mdf) and not len(memdf):
        st.info("No practice saved yet. Play a round of Math Drills or Memory — every answer is saved to your account.")
        return

    goal = int(ss.user.get("daily_goal") or 30)
    all_days = (set(mdf["day"]) if len(mdf) else set()) | (set(memdf["day"]) if len(memdf) else set())
    cur_streak, best_streak = G.streaks(all_days)
    today = G.today()
    done_today = int((mdf["day"] == today).sum()) if len(mdf) else 0

    # ---- top line
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 Day streak", cur_streak, help=f"Longest ever: {best_streak} days")
    c2.metric("Days practised", len(all_days))
    c3.metric("Total questions", len(mdf))
    c4.metric("Best digit span", int(memdf[memdf.correct]["length"].max()) if len(memdf) and memdf.correct.any() else 0)

    # ---- daily goal
    gc1, gc2 = st.columns([3, 1])
    gc1.markdown(f"**Today's goal:** {done_today} / {goal} questions")
    gc1.progress(min(1.0, done_today / goal))
    new_goal = gc2.number_input("Daily goal", 5, 500, goal, 5, label_visibility="collapsed",
                                help="Questions per day")
    if new_goal != goal:
        store.set_goal(uid, new_goal)
        ss.user["daily_goal"] = new_goal
        st.rerun()

    # ---- calendar
    st.subheader("Practice calendar")
    counts = mdf.groupby("day").size().to_dict() if len(mdf) else {}
    st.markdown(G.heatmap_html(counts, days=91, goal=goal), unsafe_allow_html=True)

    # ---- trends
    st.subheader("Trends")
    rng = st.radio("Period", list(RANGES), index=1, horizontal=True, label_visibility="collapsed")
    days = RANGES[rng]
    m = G.in_range(mdf, days)
    mem = G.in_range(memdf, days)

    cats = ["All categories"] + sorted(m["category"].unique()) if len(m) else ["All categories"]
    cat = st.selectbox("Category", cats)
    mm = m if cat == "All categories" else m[m.category == cat]
    daily = G.daily_math(mm)

    if len(daily):
        k1, k2, k3 = st.columns(3)
        k1.metric("Questions", int(daily["questions"].sum()))
        k2.metric("Accuracy", f"{mm.correct.mean() * 100:.0f}%")
        sp = mm[mm.correct]["seconds"].mean()
        k3.metric("Avg time (correct)", f"{sp:.1f}s" if pd.notna(sp) else "–")

        t1, t2, t3 = st.tabs(["⚡ Speed", "🎯 Accuracy", "📊 Volume"])
        with t1:
            st.caption("Average seconds per correct answer, per day — going **down** means you're getting faster.")
            st.line_chart(daily["avg_seconds"], height=240, y_label="seconds")
        with t2:
            st.caption("Percent correct per day.")
            st.line_chart(daily["accuracy"], height=240, y_label="% correct")
        with t3:
            st.caption("Questions answered per day.")
            st.bar_chart(daily["questions"], height=240, y_label="questions")
    else:
        st.caption("No math practice in this period.")

    # ---- then vs now
    st.subheader("How much have you improved?")
    tvn = G.then_vs_now(m)
    if len(tvn):
        st.caption(f"Your first 30% of attempts vs your latest 30% ({rng.lower()}), "
                   "for every type you've done at least 10 times.")
        show = pd.DataFrame({
            "Type": tvn["category"] + " · " + tvn["level"],
            "Attempts": tvn["attempts"],
            "Accuracy then → now": tvn["acc_then"].astype(str) + "% → " + tvn["acc_now"].astype(str) + "%",
            "Time then → now": tvn["sec_then"].map(lambda x: f"{x}s" if pd.notna(x) else "–") + " → "
                               + tvn["sec_now"].map(lambda x: f"{x}s" if pd.notna(x) else "–"),
            "Faster by": tvn["speed_change_%"].map(lambda x: f"{x:+.0f}%" if pd.notna(x) else "–"),
        })
        st.dataframe(show, hide_index=True, use_container_width=True)
        best = tvn.dropna(subset=["speed_change_%"]).sort_values("speed_change_%", ascending=False)
        if len(best) and best.iloc[0]["speed_change_%"] > 0:
            b = best.iloc[0]
            st.success(f"Biggest gain: **{b['category']} ({b['level']})** — {b['sec_then']}s → {b['sec_now']}s "
                       f"per question ({b['speed_change_%']:.0f}% faster).")
    else:
        st.caption("Do at least 10 questions of a type in this period to see your before/after comparison.")

    # ---- weak spots
    if len(m) >= 10:
        by = (m.groupby(["category", "level"])
                .agg(n=("correct", "size"), acc=("correct", "mean")).reset_index())
        by = by[by.n >= 5].sort_values("acc")
        if len(by) and by.iloc[0]["acc"] < 0.9:
            w = by.iloc[0]
            st.warning(f"Weakest spot: **{w['category']} ({w['level']})** at {w['acc'] * 100:.0f}% accuracy. "
                       f"Try a focused round on it.")

    # ---- memory
    st.subheader("Memory")
    dm = G.daily_memory(mem)
    if len(dm):
        a1, a2, a3 = st.columns(3)
        a1.metric("Attempts", len(mem))
        a2.metric("Perfect recalls", int(mem.correct.sum()))
        a3.metric("Best span (period)", int(mem[mem.correct]["length"].max()) if mem.correct.any() else 0)
        st.caption("Longest sequence recalled perfectly each day.")
        st.line_chart(dm["best_span"], height=200, y_label="digits")
    else:
        st.caption("No memory practice in this period.")

    # ---- export
    with st.expander("⬇ Export my data"):
        if len(mdf):
            st.download_button("Math history (CSV)", mdf.drop(columns=["user_id"]).to_csv(index=False),
                               "mindgym_math.csv", "text/csv")
        if len(memdf):
            st.download_button("Memory history (CSV)", memdf.drop(columns=["user_id"]).to_csv(index=False),
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
