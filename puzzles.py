"""Distraction puzzles for Memory mode: probability, finance and brain teasers.

Classic quant-interview style questions (written fresh, multiple choice, answer first in `opts`).
"""
import random

# (topic, question, [correct, wrong, wrong, wrong], explanation)
BANK = [
    # ---------------- Probability
    ("Probability", "Two fair dice are rolled. What is the probability the sum is 7?",
     ["1/6", "1/12", "7/36", "1/9"], "6 of the 36 outcomes give 7: (1,6),(2,5)…(6,1)."),
    ("Probability", "You flip a fair coin until the first head. Expected number of flips?",
     ["2", "1.5", "3", "4"], "Geometric with p = 1/2 → mean 1/p = 2."),
    ("Probability", "Expected number of rolls of a fair die until you see a 6?",
     ["6", "3.5", "5", "7"], "Geometric with p = 1/6 → mean 6."),
    ("Probability", "Roll a die 4 times. Probability of at least one 6 (closest)?",
     ["0.52", "0.67", "0.48", "0.33"], "1 − (5/6)⁴ ≈ 0.518."),
    ("Probability", "A family has 3 children and at least one is a boy. P(all three are boys)?",
     ["1/7", "1/8", "1/4", "1/3"], "7 equally likely outcomes have ≥1 boy; only BBB is all boys."),
    ("Probability", "Smallest group size where a shared birthday is more likely than not?",
     ["23", "183", "50", "32"], "At 23 people the chance of a match passes 50%."),
    ("Probability", "Monty Hall: you switch doors after the host opens a goat door. P(win)?",
     ["2/3", "1/2", "1/3", "3/4"], "Your first pick is right 1/3 of the time; switching wins the other 2/3."),
    ("Probability", "Expected number of fair-coin flips until you get two heads in a row (HH)?",
     ["6", "4", "3", "8"], "Solve E = ½(1+E_H) + ½(1+E) with E_H = ½·1 + ½(1+E) → E = 6."),
    ("Probability", "Expected flips until the pattern HT first appears?",
     ["4", "6", "3", "5"], "Wait for an H (2 flips), then wait for a T (2 flips) → 4."),
    ("Probability", "Break a stick at two uniformly random points. P(the 3 pieces form a triangle)?",
     ["1/4", "1/2", "1/3", "1/8"], "Every piece must be under half the length — probability 1/4."),
    ("Probability", "Two cards drawn without replacement from a 52-card deck. P(both aces)?",
     ["1/221", "1/169", "1/52", "1/26"], "(4/52)·(3/51) = 1/221."),
    ("Probability", "Expected number of die rolls to see all six faces at least once (closest)?",
     ["14.7", "6", "10", "21"], "Coupon collector: 6·(1+½+…+⅙) ≈ 14.7."),
    ("Probability", "Bag has 3 red and 2 blue balls. Draw 2 without replacement. P(both red)?",
     ["3/10", "9/25", "1/2", "2/5"], "(3/5)·(2/4) = 3/10."),
    ("Probability", "Two numbers chosen uniformly in [0,1]. P(they are within 0.5 of each other)?",
     ["3/4", "1/2", "2/3", "1/4"], "The two corner triangles where |x−y| > ½ have total area ¼."),
    ("Probability", "Expected value of the larger of two fair dice (closest)?",
     ["4.47", "3.5", "5", "4"], "Σ k·P(max = k) = 161/36 ≈ 4.47."),
    ("Probability", "Three ants on the corners of a triangle each walk along a random edge. P(no collision)?",
     ["1/4", "1/8", "1/2", "1/3"], "Only all-clockwise or all-anticlockwise works: 2/8 = 1/4."),
    ("Probability", "A number is picked from 1 to 100. P(it is divisible by 3 or 5)?",
     ["47/100", "53/100", "1/2", "8/15"], "33 + 20 − 6 = 47 numbers (inclusion–exclusion)."),
    ("Probability", "Expected value of a fair die roll, squared — E[X²]?",
     ["91/6", "49/4", "21/2", "15"], "(1+4+9+16+25+36)/6 = 91/6 ≈ 15.17."),
    # ---------------- Finance
    ("Finance", "₹1,000 grows at 10% a year, compounded annually. Value after 2 years?",
     ["₹1,210", "₹1,200", "₹1,100", "₹1,221"], "1000 × 1.1² = 1210."),
    ("Finance", "Rule of 72: roughly how long to double money at 8% a year?",
     ["9 years", "8 years", "12 years", "7 years"], "72 / 8 = 9."),
    ("Finance", "Interest rates rise sharply. What usually happens to existing bond prices?",
     ["They fall", "They rise", "No change", "They go to par"], "Price moves opposite to yield."),
    ("Finance", "A stock rises 50% and then falls 50%. Net change?",
     ["−25%", "0%", "+25%", "−50%"], "1.5 × 0.5 = 0.75 → down 25%."),
    ("Finance", "After a 20% loss, what gain do you need to get back to even?",
     ["25%", "20%", "22%", "30%"], "0.8 × 1.25 = 1."),
    ("Finance", "Present value of ₹110 received in one year at a 10% discount rate?",
     ["₹100", "₹99", "₹110", "₹121"], "110 / 1.1 = 100."),
    ("Finance", "A perpetuity pays ₹50 a year forever; discount rate 5%. Its value?",
     ["₹1,000", "₹2,500", "₹500", "₹250"], "Cash flow / rate = 50 / 0.05."),
    ("Finance", "A call option has strike 100; the stock is 120 at expiry. Payoff per share?",
     ["20", "0", "120", "−20"], "max(S − K, 0) = 20."),
    ("Finance", "A put option has strike 100; the stock is 120 at expiry. Payoff per share?",
     ["0", "20", "−20", "100"], "max(K − S, 0) = 0 — the put expires worthless."),
    ("Finance", "Put–call parity for European options says C − P equals:",
     ["S − PV(K)", "K − S", "S + PV(K)", "PV(K) − S"], "Long call + short put replicates a forward."),
    ("Finance", "Portfolio: half in a stock with beta 1.2, half in one with beta 0.8. Portfolio beta?",
     ["1.0", "0.96", "2.0", "1.2"], "Beta is the weighted average: 0.6 + 0.4."),
    ("Finance", "Nominal return 9%, inflation 6%. Approximate real return?",
     ["≈3%", "≈15%", "≈1.5%", "≈6%"], "Real ≈ nominal − inflation (exactly 1.09/1.06 − 1 ≈ 2.8%)."),
    ("Finance", "Macaulay duration of a 5-year zero-coupon bond?",
     ["5 years", "2.5 years", "Less than 5 years", "It depends on the coupon"], "A zero has one cash flow at maturity."),
    ("Finance", "Annual volatility is 20%. Approximate daily volatility (252 trading days)?",
     ["≈1.26%", "≈0.08%", "≈5%", "≈20%"], "20% / √252 ≈ 1.26%."),
    ("Finance", "Which raises a call option's price, all else equal?",
     ["Higher volatility", "Lower stock price", "Higher strike", "Less time to expiry"],
     "More volatility = more upside potential for the holder."),
    # ---------------- Brain teasers
    ("Brain teaser", "A bat and a ball cost ₹110 together. The bat costs ₹100 more than the ball. Ball price?",
     ["₹5", "₹10", "₹1", "₹15"], "Ball x, bat x+100 → 2x + 100 = 110 → x = 5."),
    ("Brain teaser", "25 horses, a track that races 5 at a time, no timer. Minimum races to find the top 3?",
     ["7", "6", "8", "10"], "5 heats + race of winners + one final race among the 5 remaining candidates."),
    ("Brain teaser", "2 eggs, 100-floor building. Minimum drops to guarantee finding the critical floor?",
     ["14", "10", "50", "7"], "Drop at 14, 27, 39… — n(n+1)/2 ≥ 100 → n = 14."),
    ("Brain teaser", "100 lockers, person k toggles every k-th locker (k = 1…100). How many end up open?",
     ["10", "50", "1", "25"], "Only perfect squares have an odd number of divisors."),
    ("Brain teaser", "Angle between the hour and minute hands at 3:15?",
     ["7.5°", "0°", "15°", "22.5°"], "Hour hand has moved ¼ of 30° past 3 → 7.5°."),
    ("Brain teaser", "How many trailing zeros does 100! have?",
     ["24", "20", "25", "10"], "⌊100/5⌋ + ⌊100/25⌋ = 20 + 4."),
    ("Brain teaser", "10 people each shake hands with everyone else once. Total handshakes?",
     ["45", "90", "100", "50"], "10 choose 2 = 45."),
    ("Brain teaser", "Lily pads double daily and cover the pond on day 48. When is it half covered?",
     ["Day 47", "Day 24", "Day 46", "Day 36"], "It doubles from half to full in one day."),
    ("Brain teaser", "What is the last digit of 7¹⁰⁰?",
     ["1", "7", "9", "3"], "Last digits cycle 7, 9, 3, 1 every 4 powers; 100 is a multiple of 4."),
    ("Brain teaser", "Sum of the integers from 1 to 100?",
     ["5050", "5000", "10100", "4950"], "n(n+1)/2 = 100·101/2."),
    ("Brain teaser", "How many squares of any size are on an 8×8 chessboard?",
     ["204", "64", "100", "128"], "1² + 2² + … + 8² = 204."),
    ("Brain teaser", "A clock's hands overlap how many times in 12 hours?",
     ["11", "12", "24", "22"], "Every 12/11 hours, so 11 times."),
]

TOPICS = ["Mixed", "Probability", "Finance", "Brain teaser"]


def pick(n, topic="Mixed", rng=random):
    """Return n puzzle dicts with shuffled options."""
    pool = [b for b in BANK if topic == "Mixed" or b[0] == topic]
    chosen = rng.sample(pool, min(n, len(pool)))
    out = []
    for t, q, opts, why in chosen:
        shuffled = opts[:]
        rng.shuffle(shuffled)
        out.append(dict(topic=t, q=q, options=shuffled, answer=opts[0], why=why))
    return out
