# Day 1 — de-risking

Goal today: prove every external dependency works **and** find two subjects that
reliably produce verified social-media matches. No pipeline code, no contract.
If day 1 fails, the design changes today — not on day 3 with the deadline live.

Deadline: **Sep 7, 11:59 PM IST**.

## Setup

**Use Python 3.11.** On 3.13, `facenet-pytorch`'s `numpy<2` pin forces a source
build of numpy that needs MSVC and fails. Already verified working on 3.11.9.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then fill in SERPAPI_KEY and IMGBB_KEY
```

Keys, both free, no card:
- SerpAPI — https://serpapi.com/ → dashboard → private API key (~100 searches/mo)
- imgbb — https://api.imgbb.com/ → get API key

## Step 0 — environment

```powershell
python scripts\day1_check.py
```

Downloads ~110MB of model weights on first run. Get this out of the way now so
it never happens mid-recording.

Then confirm the face half works, with no keys and no API credits:

```powershell
python scripts\day1_smoke.py
```

Verified baseline on public portraits: same person across a 6-year gap scored
**+0.781**, different people scored **+0.207** and **-0.010**. If your run does
not reproduce roughly that separation, stop and fix it before spending credits.

## Step 0.6 — verify the API keys

Costs zero search credits (uses SerpAPI's account endpoint, not search) and
confirms the imgbb URL is publicly fetchable — if it is not, SerpAPI cannot read
it and the pipeline stops at step one.

```powershell
python scripts\day1_keys.py
```

Key locations, both free:
- SerpAPI — sign up, then https://serpapi.com/manage-api-key
- imgbb — while logged in, https://imgbb.com/settings/api → Add API key

## Step 1 — calibrate the threshold

Do **not** ship the default 0.60. Derive it.

```
data/calibrate/
    person_a/  three or more genuinely different photos
    person_b/  ...
    person_c/  ...
```

Different angles, lighting and years — not crops of one shot, which would
flatter the numbers and hand you a threshold that fails on real data.

```powershell
python scripts\day1_calibrate.py
```

Read the separation gap. If the same-person and different-person populations
overlap, a single threshold cannot be correct, and that goes in the README's
limitations section rather than being papered over.

Put the suggested value in `.env` as `MATCH_THRESHOLD`.

## Step 2 — one live probe

```powershell
python scripts\day1_probe.py data\scout\subject_a.jpg --fresh
```

Costs one credit. Read `out/lens_cache/*.json` — the real response shape, not
what the docs claim. Confirm results carry `link`, `source` and `thumbnail`.

## Step 3 — subject scouting (the important one)

One photo per candidate in `data/scout/`, named after the person. Test 5–6.
Creators and influencers beat actors and politicians here: Lens returns news and
wiki pages for the famous, and actual Instagram/X posts for the online-native.

```powershell
python scripts\day1_scout.py
```

Costs ~1 credit per subject. You want **GO** — two subjects with verified
matches. Lock those in for the recording.

## Also today

Claim Base Sepolia faucet ETH. The faucets rate-limit and some require a mainnet
balance; discovering that on day 2 costs you a day.

## What each failure means

| Symptom | Read it as |
|---|---|
| `total` high, `social` 0 | Wrong subject type — scout online-native people |
| `social` high, `verified` 0, many undetectable | Thumbnails too small; check `undetectable` count |
| `social` high, `verified` 0, all rejected | Threshold too strict — re-run calibration |
| No face in query image | Crop tighter, use a clearer frontal photo |
