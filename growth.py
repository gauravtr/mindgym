"""Long-term progress analytics (pure pandas, no Streamlit)."""
from datetime import timedelta

import pandas as pd

TZ = "Asia/Kolkata"


def with_day(df, tz=TZ):
    if df is None or not len(df):
        return df
    df = df.copy()
    df["day"] = df["ts"].dt.tz_convert(tz).dt.date
    return df


def today(tz=TZ):
    return pd.Timestamp.now(tz=tz).date()


def in_range(df, days, tz=TZ):
    """Keep the last `days` days (None = everything)."""
    if df is None or not len(df) or days is None:
        return df
    start = today(tz) - timedelta(days=days - 1)
    return df[df["day"] >= start]


def daily_math(df):
    """One row per practice day: questions, accuracy %, avg seconds (correct answers only)."""
    if df is None or not len(df):
        return pd.DataFrame(columns=["questions", "accuracy", "avg_seconds"])
    g = df.groupby("day")
    out = pd.DataFrame({
        "questions": g.size(),
        "accuracy": (g["correct"].mean() * 100).round(1),
        "avg_seconds": df[df.correct].groupby("day")["seconds"].mean().round(2),
    })
    out.index = pd.to_datetime(out.index)
    return out


def daily_memory(df):
    if df is None or not len(df):
        return pd.DataFrame(columns=["attempts", "best_span"])
    g = df.groupby("day")
    best = df[df.correct].groupby("day")["length"].max()
    out = pd.DataFrame({"attempts": g.size(), "best_span": best}).fillna({"best_span": 0})
    out.index = pd.to_datetime(out.index)
    return out


def streaks(days, tz=TZ):
    """(current_streak, longest_streak) in consecutive practice days."""
    days = sorted(set(days))
    if not days:
        return 0, 0
    longest = run = 1
    for a, b in zip(days, days[1:]):
        run = run + 1 if (b - a).days == 1 else 1
        longest = max(longest, run)
    t = today(tz)
    s = set(days)
    cur, d = 0, t if t in s else t - timedelta(days=1)  # today not done yet doesn't break the streak
    while d in s:
        cur += 1
        d -= timedelta(days=1)
    return cur, longest


def then_vs_now(df, min_attempts=10):
    """Per category+level: accuracy & speed in the earliest 30% of attempts vs the latest 30%."""
    rows = []
    if df is None or not len(df):
        return pd.DataFrame()
    for (cat, lvl), g in df.sort_values("ts").groupby(["category", "level"]):
        n = len(g)
        if n < min_attempts:
            continue
        k = max(3, int(n * 0.3))
        first, last = g.head(k), g.tail(k)

        def spd(x):
            x = x[x.correct]
            return round(x["seconds"].mean(), 1) if len(x) else None

        rows.append(dict(
            category=cat, level=lvl, attempts=n,
            acc_then=round(first.correct.mean() * 100), acc_now=round(last.correct.mean() * 100),
            sec_then=spd(first), sec_now=spd(last),
        ))
    out = pd.DataFrame(rows)
    if len(out):
        out["acc_change"] = out["acc_now"] - out["acc_then"]
        out["speed_change_%"] = ((out["sec_then"] - out["sec_now"]) / out["sec_then"] * 100).round(0)
    return out


def heatmap_html(day_counts, days=35, goal=30, tz=TZ):
    """GitHub-style calendar of the last `days` days. day_counts: {date: questions}."""
    t = today(tz)
    start = t - timedelta(days=days - 1)
    start -= timedelta(days=start.weekday())  # align to Monday
    cells, d = [], start
    while d <= t:
        n = day_counts.get(d, 0)
        if n == 0:
            color = "#e2e8f0"
        elif n < goal / 3:
            color = "#c7d2fe"
        elif n < goal:
            color = "#818cf8"
        else:
            color = "#4338ca"
        cells.append(f'<div title="{d:%d %b}: {n} questions" style="width:16px;height:16px;border-radius:4px;'
                     f'background:{color};{"outline:2px solid #f59e0b;" if d == t else ""}"></div>')
        d += timedelta(days=1)
    labels = "".join(f'<div style="height:16px;font-size:10px;color:#64748b;line-height:16px">{x}</div>'
                     for x in ["Mon", "", "Wed", "", "Fri", "", "Sun"])
    grid = ('<div style="display:grid;grid-template-rows:repeat(7,16px);grid-auto-flow:column;gap:3px">'
            + "".join(cells) + "</div>")
    legend = ('<div style="font-size:11px;color:#64748b;margin-top:6px">Less '
              + "".join(f'<span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:{c};'
                        f'margin:0 2px;vertical-align:middle"></span>' for c in ["#e2e8f0", "#c7d2fe", "#818cf8", "#4338ca"])
              + f' More &nbsp;·&nbsp; darkest = daily goal ({goal}) met</div>')
    return (f'<div style="display:flex;gap:6px"><div style="display:grid;grid-template-rows:repeat(7,16px);gap:3px">'
            f'{labels}</div>{grid}</div>{legend}')
