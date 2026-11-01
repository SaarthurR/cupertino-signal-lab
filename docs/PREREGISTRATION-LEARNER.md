# Signal Learner held-out preregistration

Registered before any learner run on a held-out road. Simulation only; synthetic demand on new roads.
Spec: `docs/LEARNER-SPEC.md`. Code is frozen at the latest commit containing this file; the test command refuses
to run if `src/`, `roads/` or `tools/learner.py` differ from that commit.

## Roads

- Dev (used freely): Stevens Creek Blvd (5 signals, De Anza to Mary; world = VTA 2024 count-fitted routes)
  and Homestead Rd (5 signals: Wright Ave, Mary Ave, Kennewick Dr, Hollenbeck Ave, Forge Way).
- Held out, fixed now: **Wolfe Rd** north of Stevens Creek (Vallco Pkwy, I-280 south ramps, I-280 north ramps,
  Pruneridge Ave, Apple Park Way) and **De Anza Blvd** north of Stevens Creek (Lazaneo Dr, Mariani Ave,
  I-280 south ramps, I-280 north ramps). Neither shares a signal with a dev road.
- Built from OpenStreetMap only (`roads/<road>/`), signals pinned by OSM node ID in `src/world/roads.py`.
  Only configs and nets exist for held-out roads; no simulation has run on them.

## Worlds and old timing

- Held-out world demand: `world.worlds.build_demand`, seeds Wolfe 12, De Anza 13. PM rush 16:15–18:30 with
  a per-approach peak, per-approach flows and turn shares; hourly vehicles per through lane drawn from
  400–640 (mainline) and 130–280 (side). The rates were set on Homestead only. Labeled SYNTHETIC.
- Old timing: the textbook coordinated-actuated method (`baseline.actuated`) on stale demand: world routes with
  one seeded factor per origin approach in 0.6–1.4 (seed = world seed + 1000). Not Cupertino's timing.
- World files live in `worlds/` and `reports/learner_truth/`; a guard test fails if learner code reads them.

## Learner, frozen

- Watch: old timing, seeds 0–2, feed only (five-minute approach counts and occupancy, lane counts).
- Learn: 15-minute mean per lane; routeSampler (`--optimize full`, seed 0) on edge counts plus turn counts
  only where dedicated lanes serve the turn; warmup repeats the first quarter hour.
- Practice: Optuna TPE seed 0, **150 trials**, copy seeds 0–2, at most 3 simulations at once, nice 15.
  Searches cycle (v5 bounds 80–180 s, floor lowered to the old cycle if shorter), offsets and green shares
  (0.6–1.4). Phase order, clearances, minimum greens and passage times are unchanged. Feasible only if
  side-street all-requested delay ≤ 1.05× old and teleports ≤ old + 2 per seed. Old timing is trial 0.
- Recommend: re-run old vs best on copy seeds 10–19. Change only if best ≠ old, mean copy gain ≥ 2%,
  one-sided paired Wilcoxon p < .05 and feasible; otherwise the card says **no change**.
- Check (go-back) rule: after the change, compare each five-minute window's upstream occupancy with the
  watched old-timing level at the same time of day. Flag a window if mean approach occupancy rises more
  than max(5 points, 3 watched SDs), or at least 2 approaches each rise more than max(25 points, 3 SDs),
  or the vehicles served over the last 15 minutes are more than 6% below the watched level. Go back after
  3 flagged windows in a row. These thresholds were tuned on dev roads (go-back seeds 300–304): one
  approach alone gave false alarms on Homestead, and occupancy alone missed the saturated Stevens Creek
  road, so the two-approach and served-count flags were added. Dev result: bad plan undone 5/5 on both
  roads, no-op undone 0/5 on both.

## Test

- Paired old vs learner, seeds **200–219**, full PM cohort 16:30–18:30, 900 s warmup, 1800 s drain.
- Primary: `all_requested_delay_s` (900 s charged per unfinished trip and per teleport).
- One-sided paired Wilcoxon (learner minus old, alternative less), alpha .05, Holm across the two roads.
- A "no change" card means the learner arm is the old timing: zero differences, p = 1, no gain.
- Secondary, descriptive: unfinished trips, teleports, worst origin-approach delay, copy error against hidden
  truth (share of 15-minute turn counts with GEH < 5, total absolute error share), and a fresh textbook
  coordinated-actuated retiming built from true current world demand.
- Go-back test, seeds 220–229: a deliberately bad plan (shortest cycle, mainline share 0.6, others 1.4,
  offsets half a cycle off) and a no-op change (old timing renamed), applied at 17:00.
  Pass: bad plan undone on ≥ 80% of seeds with lower mean delay than holding it, and the no-op undone on ≤ 20%.
- Command: `PYTHONPATH=src .venv/bin/python -m tools.learner heldout-test`. It writes
  checkpoints in `reports/learner_heldout/`, resumes only missing work after a crash, and refuses once
  `results.json` exists.
- Results are reported as they come. No re-tuning on test seeds or held-out roads.

## Amendment before any held-out run — 2026-11-01

Independent review added the descriptive fresh-retiming arm above. It does not affect the primary learner test.
The command now writes atomic per-seed checkpoints and can resume an interrupted run. The earlier command would
have refused after a crash and wasted the single test. The freeze also rejects untracked code and road files.
The frozen commit is the commit containing this amendment and its reviewed code. No held-out simulation had run.
