"""Pure game logic for MindGym — no Streamlit imports, so it is easy to test."""
import random

LEVELS = ["Easy", "Medium", "Hard", "Beast"]

CATEGORIES = {
    "Addition": "➕",
    "Subtraction": "➖",
    "Multiplication": "✖️",
    "Division": "➗",
    "Squares": "x²",
    "Cubes": "x³",
    "Square roots": "√",
    "Cube roots": "∛",
    "Percentages": "%",
}

# What each level means, shown to the player so difficulty is never a mystery.
LEVEL_INFO = {
    "Addition":       ["2-digit + 2-digit", "3-digit + 3-digit", "4-digit + 4-digit", "three 3-digit numbers"],
    "Subtraction":    ["2-digit − 2-digit", "3-digit − 3-digit", "4-digit − 3-digit", "4-digit − 4-digit"],
    "Multiplication": ["2-digit × 1-digit", "2-digit × 2-digit", "3-digit × 2-digit", "3-digit × 3-digit"],
    "Division":       ["2-digit ÷ 1-digit", "3-digit ÷ 1-digit", "4-digit ÷ 2-digit", "5-digit ÷ 2-digit"],
    "Squares":        ["1 – 25", "26 – 99", "100 – 199", "200 – 999"],
    "Cubes":          ["1 – 10", "11 – 20", "21 – 50", "51 – 99"],
    "Square roots":   ["perfect squares, root 1–20", "perfect squares, root 21–99", "perfect squares, root 100–999", "non-perfect, 1 decimal"],
    "Cube roots":     ["perfect cubes, root 1–10", "perfect cubes, root 11–30", "perfect cubes, root 31–99", "non-perfect, 1 decimal"],
    "Percentages":    ["10/20/25/50% of round numbers", "multiples of 5% of 2–3 digits", "any % of 2–3 digits (2 dp)", "decimal % like 17.5% (2 dp)"],
}

TIPS = {
    "Addition": "Add left-to-right: 478 + 365 → 700, 130, 13 → 843.",
    "Subtraction": "Round and compensate: 832 − 397 = 832 − 400 + 3 = 435.",
    "Multiplication": "Split one number: 47 × 36 = 47 × 30 + 47 × 6 = 1410 + 282 = 1692. "
                      "Near 100? (100−a)(100−b) = 100(100−a−b) + ab.",
    "Division": "Estimate the leading digit first, then fix with the remainder. 7392 ÷ 24 → 300 (7200), 192 ÷ 24 = 8 → 308.",
    "Squares": "(a+b)² = a² + 2ab + b². Ending in 5: n5² = n(n+1) then append 25 → 75² = 56|25.",
    "Cubes": "(a+b)³ = a³ + 3a²b + 3ab² + b³. Memorise 1³–12³ cold.",
    "Square roots": "Last digit of the square narrows the last digit of the root (…6 → 4 or 6). "
                    "Bracket the leading part between known squares.",
    "Cube roots": "Last digit of a cube maps 1-to-1: 2↔8, 3↔7, others same. Drop the last 3 digits "
                  "and find the largest cube ≤ what's left → that's the tens digit. 357911 → 357 → 7, ends in 1 → 71.",
    "Percentages": "x% of y = y% of x. 18% of 50 = 50% of 18 = 9. Build from 10% and 1%.",
}


def _d(rng, digits):
    """Random integer with exactly `digits` digits."""
    return rng.randint(10 ** (digits - 1), 10 ** digits - 1)


def _fmt(x):
    return f"{x:,}"


def make_question(category, level, rng=random):
    """Return dict: prompt (str), answer (float), tol (float), decimals (int)."""
    li = LEVELS.index(level)
    tol, dec = 0, 0

    if category == "Addition":
        if li == 3:
            nums = [_d(rng, 3) for _ in range(3)]
        else:
            n = [2, 3, 4][li]
            nums = [_d(rng, n), _d(rng, n)]
        prompt = " + ".join(_fmt(x) for x in nums)
        ans = sum(nums)

    elif category == "Subtraction":
        da, db = [(2, 2), (3, 3), (4, 3), (4, 4)][li]
        a, b = _d(rng, da), _d(rng, db)
        if b > a:
            a, b = b, a
        if a == b:
            a += rng.randint(1, 9)
        prompt, ans = f"{_fmt(a)} − {_fmt(b)}", a - b

    elif category == "Multiplication":
        da, db = [(2, 1), (2, 2), (3, 2), (3, 3)][li]
        a, b = _d(rng, da), _d(rng, db)
        if db == 1:
            b = rng.randint(2, 9)
        prompt, ans = f"{_fmt(a)} × {_fmt(b)}", a * b

    elif category == "Division":
        # build from divisor × quotient so it is always exact
        if li == 0:
            d = rng.randint(2, 9); q = rng.randint(2, 99 // d)
        elif li == 1:
            d = rng.randint(2, 9); q = rng.randint(100 // d + 1, 999 // d)
        elif li == 2:
            d = rng.randint(11, 99); q = rng.randint(1000 // d + 1, 9999 // d)
        else:
            d = rng.randint(11, 99); q = rng.randint(10000 // d + 1, 99999 // d)
        prompt, ans = f"{_fmt(d * q)} ÷ {d}", q

    elif category == "Squares":
        lo, hi = [(1, 25), (26, 99), (100, 199), (200, 999)][li]
        n = rng.randint(lo, hi)
        prompt, ans = f"{n}²", n * n

    elif category == "Cubes":
        lo, hi = [(1, 10), (11, 20), (21, 50), (51, 99)][li]
        n = rng.randint(lo, hi)
        prompt, ans = f"{n}³", n ** 3

    elif category == "Square roots":
        if li < 3:
            lo, hi = [(1, 20), (21, 99), (100, 999)][li]
            r = rng.randint(lo, hi)
            prompt, ans = f"√{_fmt(r * r)}", r
        else:
            n = rng.randint(2, 999)
            while int(n ** 0.5) ** 2 == n:
                n += 1
            prompt, ans, tol, dec = f"√{n}  (1 decimal)", round(n ** 0.5, 1), 0.1, 1

    elif category == "Cube roots":
        if li < 3:
            lo, hi = [(1, 10), (11, 30), (31, 99)][li]
            r = rng.randint(lo, hi)
            prompt, ans = f"∛{_fmt(r ** 3)}", r
        else:
            n = rng.randint(2, 9999)
            while round(n ** (1 / 3)) ** 3 == n:
                n += 1
            prompt, ans, tol, dec = f"∛{_fmt(n)}  (1 decimal)", round(n ** (1 / 3), 1), 0.1, 1

    elif category == "Percentages":
        if li == 0:
            p = rng.choice([10, 20, 25, 50]); y = rng.randint(1, 50) * 20
        elif li == 1:
            p = rng.randint(1, 19) * 5; y = rng.randint(2, 99) * 10
        elif li == 2:
            p = rng.randint(1, 99); y = rng.randint(10, 999)
        else:
            p = rng.randint(1, 99) + rng.choice([0.5, 0.25, 0.75]); y = rng.randint(10, 999)
        ans = round(p * y / 100, 2)
        if ans != int(ans):
            tol, dec = 0.01, 2
        p_txt = f"{p:g}"
        prompt = f"{p_txt}% of {_fmt(y)}" + ("  (2 dp)" if dec else "")

    else:
        raise ValueError(f"Unknown category {category}")

    return {"prompt": prompt, "answer": float(ans), "tol": tol, "decimals": dec,
            "category": category, "level": level}


def parse_answer(text):
    """Turn user text into a float, or None if it isn't a number."""
    if text is None:
        return None
    t = text.strip().replace(",", "").replace(" ", "")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def is_correct(q, value):
    if value is None:
        return False
    return abs(value - q["answer"]) <= q["tol"] + 1e-9


def show_answer(q):
    a = q["answer"]
    if q["decimals"]:
        return f"{a:.{q['decimals']}f}"
    return _fmt(int(round(a)))


# ---------- memory mode ----------

def make_sequence(length, rng=random, no_leading_zero=True):
    digits = [str(rng.randint(0, 9)) for _ in range(length)]
    if no_leading_zero and digits and digits[0] == "0":
        digits[0] = str(rng.randint(1, 9))
    return "".join(digits)


def chunk(seq, size=3):
    return " ".join(seq[i:i + size] for i in range(0, len(seq), size))


def compare_sequence(target, attempt):
    """Per-position check. Returns (num_correct_positions, list of (digit, ok))."""
    attempt = "".join(ch for ch in (attempt or "") if ch.isdigit())
    marks = []
    for i, ch in enumerate(target):
        ok = i < len(attempt) and attempt[i] == ch
        marks.append((ch, ok))
    return sum(ok for _, ok in marks), marks, attempt


def next_adaptive_length(current, correct, lo=3, hi=40):
    return min(hi, current + 1) if correct else max(lo, current - 1)
