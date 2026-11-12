"""Detailed performance analytics for MindGym (pure pandas/numpy — no Streamlit).

All functions take the per-attempt DataFrames from db.Store (with a `day` column added by
growth.with_day) and return tidy DataFrames / dicts that the app renders.
"""
from datetime import timedelta

import numpy as np
import pandas as pd

import growth as G

SESSION_GAP_MIN = 20          # a pause longer than this starts a new session
NEAR_MISS_REL = 0.02          # within 2% counts as a near miss


# ------------------------------------------------------------------ prep
def prepare_math(df, tz=G.TZ):
    """Add derived columns used everywhere: local time, hour, weekday, session, position."""
    if df is None or not len(df):
        return df
    df = df.sort_values("ts").copy()
    local = df["ts"].dt.tz_convert(tz)
    df["hour"] = local.dt.hour
    df["weekday"] = local.dt.day_name().str[:3]
    df["skill"] = df["category"] + " · " + df["level"]
    df["skipped"] = df["given"].fillna("").isin(["", "(skipped)"])
    gap = df["ts"].diff().dt.total_seconds().fillna(1e9) / 60
    df["session"] = (gap > SESSION_GAP_MIN).cumsum()
    df["pos_in_session"] = df.groupby("session").cumcount() + 1
    df["error_type"] = [classify_error(a, g, c, s)
                        for a, g, c, s in zip(df["answer"], df["given"], df["correct"], df["skipped"])]
    return df


def _num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def classify_error(answer, given, correct, skipped):
    if correct:
        return "Correct"
    if skipped:
        return "Skipped"
    a, g = _num(answer), _num(given)
    if g is None or a is None:
        return "Invalid input"
    if a != 0 and abs(g - a) / abs(a) <= NEAR_MISS_REL:
        return "Near miss (≤2%)"
    if a != 0 and g != 0:
        ratio = abs(g / a)
        for p in (10, 100, 1000, 0.1, 0.01, 0.001):
            if abs(ratio - p) < 1e-9 * max(1, p):
                return "Place-value error"
    sa, sg = str(int(abs(a))) if a == int(a) else str(abs(a)), str(int(abs(g))) if g == int(g) else str(abs(g))
    if len(sa) == len(sg):
        diff = sum(x != y for x, y in zip(sa, sg))
        if diff == 1:
            return "Single-digit slip"
        if diff == 2 and sorted(sa) == sorted(sg):
            return "Transposed digits"
    return "Calculation error"


# ------------------------------------------------------------------ headline KPIs
def kpis(df):
    """Headline numbers for a slice of attempts."""
    if df is None or not len(df):
        return dict(questions=0, accuracy=None, median_s=None, fluency=None, sessions=0, days=0,
                    minutes=0, skip_rate=None, best_streak=0)
    c = df[df.correct]
    mins = df["seconds"].sum() / 60
    return dict(
        questions=len(df),
        accuracy=df.correct.mean() * 100,
        median_s=c["seconds"].median() if len(c) else None,
        fluency=len(c) / mins if mins > 0 else None,         # correct answers per minute
        sessions=df["session"].nunique() if "session" in df else None,
        days=df["day"].nunique(),
        minutes=mins,
        skip_rate=df["skipped"].mean() * 100 if "skipped" in df else None,
        best_streak=longest_correct_run(df.correct.tolist()),
    )


def longest_correct_run(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def periods(df, days):
    """(current, previous) slices of equal length for period-over-period deltas."""
    if df is None or not len(df) or days is None:
        return df, None
    t = G.today()
    cur_start = t - timedelta(days=days - 1)
    prev_start = cur_start - timedelta(days=days)
    return df[df["day"] >= cur_start], df[(df["day"] >= prev_start) & (df["day"] < cur_start)]


def delta(cur, prev, key, fmt="{:+.1f}"):
    a, b = cur.get(key), (prev or {}).get(key)
    if a is None or b is None or (isinstance(b, (int, float)) and b == 0 and key != "accuracy"):
        return None
    return fmt.format(a - b)


# ------------------------------------------------------------------ skills
def mastery(acc, cv, n):
    if n < 10:
        return "🔘 Not enough data"
    if acc >= 90 and cv <= 0.5 and n >= 20:
        return "🟢 Mastered"
    if acc >= 75:
        return "🟡 Developing"
    return "🔴 Needs work"


def skill_table(df):
    """One row per category+level with a full set of performance measures."""
    if df is None or not len(df):
        return pd.DataFrame()
    rows = []
    for (cat, lvl), g in df.groupby(["category", "level"]):
        c = g[g.correct]
        sec = c["seconds"]
        n = len(g)
        acc = g.correct.mean() * 100
        cv = (sec.std() / sec.mean()) if len(sec) > 1 and sec.mean() > 0 else 0.0
        rows.append(dict(
            Skill=f"{cat} · {lvl}", category=cat, level=lvl,
            Attempts=n,
            Accuracy=round(acc, 1),
            **{"Median (s)": round(sec.median(), 1) if len(sec) else None,
               "Best (s)": round(sec.min(), 1) if len(sec) else None,
               "90th pct (s)": round(sec.quantile(0.9), 1) if len(sec) else None,
               "Consistency": round(max(0.0, 1 - min(cv, 1.0)) * 100),
               "Per min": round(len(c) / (g["seconds"].sum() / 60), 1) if g["seconds"].sum() else None,
               "Speed trend %/wk": speed_trend(g),
               "Last practised": g["day"].max()},
            Status=mastery(acc, cv, n),
        ))
    out = pd.DataFrame(rows).sort_values(["category", "level"])
    return out


def speed_trend(g, min_days=3):
    """Linear trend of daily median time, as % change per week (negative = getting faster)."""
    c = g[g.correct]
    if not len(c):
        return None
    d = c.groupby("day")["seconds"].median()
    if len(d) < min_days:
        return None
    x = np.array([(pd.Timestamp(i) - pd.Timestamp(d.index[0])).days for i in d.index], dtype=float)
    if x.max() == 0:
        return None
    slope = np.polyfit(x, d.values, 1)[0]
    return round(slope * 7 / d.mean() * 100, 1)


def strengths_weaknesses(tbl, k=3):
    t = tbl[tbl.Attempts >= 10].copy()
    if not len(t):
        return [], []
    # composite: accuracy weighted with consistency
    t["score"] = t["Accuracy"] * 0.7 + t["Consistency"] * 0.3
    t = t.sort_values("score", ascending=False)
    return t.head(k)["Skill"].tolist(), t.tail(k).iloc[::-1]["Skill"].tolist()


# ------------------------------------------------------------------ time series
def daily_series(df, window=7):
    """Daily accuracy / median speed / fluency / volume plus rolling averages."""
    if df is None or not len(df):
        return pd.DataFrame()
    g = df.groupby("day")
    c = df[df.correct].groupby("day")
    out = pd.DataFrame({
        "Questions": g.size(),
        "Accuracy %": g["correct"].mean() * 100,
        "Median time (s)": c["seconds"].median(),
        "Minutes": g["seconds"].sum() / 60,
    })
    out["Correct / min"] = c.size().reindex(out.index).fillna(0) / out["Minutes"].replace(0, np.nan)
    out.index = pd.to_datetime(out.index)
    full = pd.date_range(out.index.min(), out.index.max(), freq="D")
    out = out.reindex(full)
    out["Questions"] = out["Questions"].fillna(0)
    for col in ["Accuracy %", "Median time (s)", "Correct / min"]:
        out[f"{col} · {window}d avg"] = out[col].rolling(window, min_periods=1).mean()
    return out.round(2)


def weekly_summary(df):
    if df is None or not len(df):
        return pd.DataFrame()
    d = df.copy()
    d["week"] = pd.to_datetime(d["day"]).dt.to_period("W-SUN").dt.start_time.dt.date
    rows = []
    for w, g in d.groupby("week"):
        k = kpis(g)
        rows.append({"Week of": w, "Days active": k["days"], "Questions": k["questions"],
                     "Minutes": round(k["minutes"], 1), "Accuracy %": round(k["accuracy"], 1),
                     "Median time (s)": round(k["median_s"], 2) if k["median_s"] else None,
                     "Correct / min": round(k["fluency"], 2) if k["fluency"] else None})
    out = pd.DataFrame(rows)
    if len(out) > 1:
        out["Δ accuracy"] = out["Accuracy %"].diff().round(1)
        out["Δ median time"] = out["Median time (s)"].diff().round(2)
    return out.sort_values("Week of", ascending=False)


def speed_distribution(df, bins=(0, 2, 4, 6, 8, 10, 15, 20, 30, 60, 1e9)):
    c = df[df.correct]
    if not len(c):
        return pd.DataFrame()
    labels = [f"{int(bins[i])}–{int(bins[i + 1])}s" if bins[i + 1] < 1e9 else f"{int(bins[i])}s+"
              for i in range(len(bins) - 1)]
    cut = pd.cut(c["seconds"], bins=list(bins), labels=labels, right=False)
    return cut.value_counts().reindex(labels).fillna(0).astype(int).rename("Answers").to_frame()


def category_speed_by_period(df, freq_days=7):
    """Median seconds per category in consecutive blocks — shows each skill's speed curve."""
    c = df[df.correct]
    if not len(c):
        return pd.DataFrame()
    c = c.copy()
    c["block"] = pd.to_datetime(c["day"]).dt.to_period("W-SUN").dt.start_time
    return c.pivot_table(index="block", columns="category", values="seconds", aggfunc="median").round(2)


# ------------------------------------------------------------------ errors
def error_breakdown(df):
    w = df[~df.correct]
    if not len(w):
        return pd.DataFrame()
    out = w["error_type"].value_counts().rename("Count").to_frame()
    out["Share %"] = (out["Count"] / out["Count"].sum() * 100).round(1)
    return out


def error_by_skill(df):
    w = df[~df.correct]
    if not len(w):
        return pd.DataFrame()
    return pd.crosstab(w["skill"], w["error_type"])


def most_missed(df, k=10):
    w = df[~df.correct]
    if not len(w):
        return pd.DataFrame()
    g = w.groupby(["question", "answer"]).agg(Misses=("correct", "size"), Last=("ts", "max")).reset_index()
    g["Your answers"] = [", ".join(w[(w.question == q)]["given"].astype(str).head(3)) for q in g["question"]]
    g["Last"] = g["Last"].dt.tz_convert(G.TZ).dt.strftime("%d %b")
    return g.sort_values(["Misses", "Last"], ascending=False).head(k).rename(
        columns={"question": "Question", "answer": "Correct"})


# ------------------------------------------------------------------ habits
TOD = [("Night (0–5)", 0, 5), ("Morning (5–12)", 5, 12), ("Afternoon (12–17)", 12, 17),
       ("Evening (17–21)", 17, 21), ("Late night (21–24)", 21, 24)]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _profile(df, key, order):
    rows = []
    for k in order:
        g = df[key(df) == k] if callable(key) else df[df[key] == k]
        if not len(g):
            continue
        kp = kpis(g)
        rows.append({"When": k, "Questions": kp["questions"], "Accuracy %": round(kp["accuracy"], 1),
                     "Median time (s)": round(kp["median_s"], 2) if kp["median_s"] else None,
                     "Correct / min": round(kp["fluency"], 2) if kp["fluency"] else None})
    return pd.DataFrame(rows)


def time_of_day(df):
    def bucket(d):
        return d["hour"].map(lambda h: next(name for name, a, b in TOD if a <= h < b))
    return _profile(df, bucket, [t[0] for t in TOD])


def weekday_profile(df):
    return _profile(df, "weekday", WEEKDAYS)


def session_stats(df):
    if df is None or not len(df):
        return pd.DataFrame()
    rows = []
    for sid, g in df.groupby("session"):
        k = kpis(g)
        start = g["ts"].min().tz_convert(G.TZ)
        rows.append({"Started": start.strftime("%d %b %H:%M"), "Questions": k["questions"],
                     "Minutes": round(k["minutes"], 1), "Accuracy %": round(k["accuracy"], 1),
                     "Median time (s)": round(k["median_s"], 2) if k["median_s"] else None,
                     "Best run": k["best_streak"], "Skills": ", ".join(sorted(g["category"].unique()))})
    return pd.DataFrame(rows).iloc[::-1]


def fatigue_curve(df, bucket=10):
    """Accuracy and speed by position within a session (1–10, 11–20, …)."""
    if df is None or not len(df):
        return pd.DataFrame()
    d = df.copy()
    d["block"] = ((d["pos_in_session"] - 1) // bucket) * bucket + 1
    d = d[d["block"] <= 91]
    rows = []
    for b, g in d.groupby("block"):
        c = g[g.correct]
        rows.append({"Questions into session": f"{b}–{b + bucket - 1}", "n": len(g),
                     "Accuracy %": round(g.correct.mean() * 100, 1),
                     "Median time (s)": round(c["seconds"].median(), 2) if len(c) else None})
    return pd.DataFrame(rows)


def speed_accuracy_by_pace(df):
    """Do you make more mistakes when you rush? Accuracy split by answer-time quartile."""
    if df is None or len(df) < 20:
        return pd.DataFrame()
    d = df[~df.skipped].copy()
    d["Pace"] = pd.qcut(d["seconds"].rank(method="first"), 4, labels=["Fastest 25%", "Fast", "Slow", "Slowest 25%"])
    return d.groupby("Pace", observed=True).agg(
        Answers=("correct", "size"), **{"Accuracy %": ("correct", lambda x: round(x.mean() * 100, 1)),
                                        "Avg time (s)": ("seconds", lambda x: round(x.mean(), 2))}).reset_index()


# ------------------------------------------------------------------ memory
def memory_kpis(m):
    if m is None or not len(m):
        return {}
    ok = m[m.correct]
    return dict(attempts=len(m), success=m.correct.mean() * 100,
                best_span=int(ok["length"].max()) if len(ok) else 0,
                reliable_span=reliable_span(m),
                digit_accuracy=(m["digits_right"].sum() / m["length"].sum() * 100) if m["length"].sum() else None)


def reliable_span(m, threshold=0.75, min_tries=2):
    """Longest length you recall perfectly at least 75% of the time."""
    best = 0
    for L, g in m.groupby("length"):
        if len(g) >= min_tries and g.correct.mean() >= threshold:
            best = max(best, int(L))
    return best


def memory_by_length(m):
    if m is None or not len(m):
        return pd.DataFrame()
    g = m.groupby("length").agg(Attempts=("correct", "size"), Perfect=("correct", "sum"),
                                DigitsRight=("digits_right", "sum"))
    g["Success %"] = (g["Perfect"] / g["Attempts"] * 100).round(1)
    g["Digit accuracy %"] = (g["DigitsRight"] / (g.index.to_series() * g["Attempts"]) * 100).round(1)
    return g[["Attempts", "Success %", "Digit accuracy %"]]


def memory_position_curve(m, n_bins=10):
    """Where in the sequence do you lose digits? (relative position, start → end)."""
    if m is None or "target" not in m or not m["target"].notna().any():
        return pd.DataFrame()
    hits = np.zeros(n_bins)
    tot = np.zeros(n_bins)
    for t, a in zip(m["target"].fillna(""), m["attempt"].fillna("")):
        if not t:
            continue
        L = len(t)
        for i, ch in enumerate(t):
            b = min(n_bins - 1, int(i / L * n_bins))
            tot[b] += 1
            hits[b] += int(i < len(a) and a[i] == ch)
    labels = [f"{int(i * 100 / n_bins)}–{int((i + 1) * 100 / n_bins)}%" for i in range(n_bins)]
    out = pd.DataFrame({"Position in sequence": labels, "Accuracy %": np.where(tot > 0, hits / np.maximum(tot, 1) * 100, np.nan)})
    return out[tot > 0].round(1).set_index("Position in sequence")


def memory_by_mode(m):
    if m is None or not len(m):
        return pd.DataFrame()
    g = m.groupby(["style", "direction"]).agg(Attempts=("correct", "size"),
                                              **{"Success %": ("correct", lambda x: round(x.mean() * 100, 1)),
                                                 "Avg length": ("length", lambda x: round(x.mean(), 1)),
                                                 "Best": ("length", "max")}).reset_index()
    return g.rename(columns={"style": "Display", "direction": "Recall"})


def memory_daily(m):
    if m is None or not len(m):
        return pd.DataFrame()
    g = m.groupby("day")
    out = pd.DataFrame({"Best span": m[m.correct].groupby("day")["length"].max(),
                        "Avg length tried": g["length"].mean(),
                        "Success %": g["correct"].mean() * 100}).round(1)
    out.index = pd.to_datetime(out.index)
    return out


# ------------------------------------------------------------------ narrative
def insights(df, m, tbl):
    """Plain-English observations, most useful first."""
    out = []
    if df is not None and len(df) >= 20:
        k = kpis(df)
        out.append(f"You answered **{k['questions']}** questions in **{k['minutes']:.0f} min** "
                   f"at **{k['accuracy']:.0f}%** accuracy — about **{k['fluency']:.1f} correct answers per minute**.")
        t = tbl.dropna(subset=["Speed trend %/wk"]) if len(tbl) else tbl
        if len(t):
            best = t.sort_values("Speed trend %/wk").iloc[0]
            if best["Speed trend %/wk"] < 0:
                out.append(f"Fastest-improving skill: **{best['Skill']}** — getting "
                           f"**{abs(best['Speed trend %/wk']):.0f}% faster per week**.")
            worst = t.sort_values("Speed trend %/wk").iloc[-1]
            if worst["Speed trend %/wk"] > 5:
                out.append(f"**{worst['Skill']}** is slowing down ({worst['Speed trend %/wk']:+.0f}%/wk) — revisit it.")
        tod = time_of_day(df)
        tod = tod[tod.Questions >= 15]
        if len(tod) >= 2:
            b = tod.sort_values("Accuracy %", ascending=False).iloc[0]
            w = tod.sort_values("Accuracy %").iloc[0]
            if b["Accuracy %"] - w["Accuracy %"] >= 5:
                out.append(f"You're sharpest in the **{b['When'].split(' (')[0].lower()}** "
                           f"({b['Accuracy %']:.0f}% vs {w['Accuracy %']:.0f}% in the {w['When'].split(' (')[0].lower()}).")
        pace = speed_accuracy_by_pace(df)
        if len(pace) == 4:
            f_, s_ = pace.iloc[0]["Accuracy %"], pace.iloc[2]["Accuracy %"]
            if s_ - f_ >= 8:
                out.append(f"Rushing costs you: your fastest 25% of answers are **{f_:.0f}%** accurate "
                           f"vs **{s_:.0f}%** at a steadier pace.")
        fat = fatigue_curve(df)
        fat = fat[fat.n >= 10]
        if len(fat) >= 3:
            drop = fat.iloc[0]["Accuracy %"] - fat.iloc[-1]["Accuracy %"]
            if drop >= 8:
                out.append(f"Accuracy drops **{drop:.0f} points** late in long sessions — "
                           f"shorter, more frequent sessions may help.")
        eb = error_breakdown(df)
        eb = eb.drop(index=[i for i in ["Skipped"] if i in eb.index]) if len(eb) else eb
        if len(eb):
            top = eb.index[0]
            out.append(f"Most common mistake type: **{top.lower()}** ({eb.iloc[0]['Share %']:.0f}% of errors).")
    if m is not None and len(m) >= 5:
        mk = memory_kpis(m)
        out.append(f"Memory: best perfect recall **{mk['best_span']} digits**; reliable span "
                   f"(≥75% success) **{mk['reliable_span']} digits**.")
        pc = memory_position_curve(m)
        if len(pc) >= 4:
            mid = pc.iloc[len(pc) // 2 - 1: len(pc) // 2 + 1]["Accuracy %"].mean()
            ends = (pc.iloc[0]["Accuracy %"] + pc.iloc[-1]["Accuracy %"]) / 2
            if ends - mid >= 8:
                out.append("You lose digits mostly in the **middle** of sequences — try chunking in 3s and "
                           "rehearsing the middle group.")
    return out
