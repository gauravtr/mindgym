# 🧠 MindGym — mental maths & memory trainer

A Streamlit app for daily mental-ability practice.

**Math Drills** — addition, subtraction, multiplication (2×1 up to 3×3 digit), division, squares, cubes,
square roots, cube roots and percentages, each with 4 difficulty levels (Easy → Beast). Mix several
categories in one round. Modes: Sprint (fixed count), Timed (beat the clock), Zen (endless).
Instant feedback, streaks, a trick for every question type, and a review of your misses.

**Memory** — digit-span training. Digits flash all at once (optionally chunked in 3s) or one by one;
type them back forward or backward. Adaptive mode adds a digit when you're right and drops one when you miss.

**Progress** — accuracy and speed per category/level, slowest correct answers, best digit span, CSV export.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy free on Streamlit Community Cloud
1. Create a new GitHub repository (e.g. `mindgym`) and upload `app.py`, `logic.py`, `requirements.txt`.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app → Deploy a public app from GitHub**, pick the repo, branch `main`, main file `app.py`.
4. Click **Deploy**. In ~2 minutes you get a link like `https://mindgym.streamlit.app`.
