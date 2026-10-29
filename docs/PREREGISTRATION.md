# Optimization v2 preregistration — 2026-10-28

Committed before any new optimization or evaluation run. We will report the result whichever way it goes.

- Primary endpoint: PM holdout all-requested delay per requested vehicle, `(sum(completed timeLoss + departDelay) + 900 * (unfinished vehicles + cohort teleport events)) / requested vehicles`. Unfinished includes running and never-inserted vehicles; the charge is a convention, not measured delay.
- Constraint: side-origin all-requested delay, computed with the same numerator and origin-specific denominator, must be at most 5% above the paired textbook plan. Enforce the constraint on the multi-seed mean during search and selection; report the final paired mean constraint check for every scenario/window.
- Secondary endpoints: completed-only time loss, EB/WB corridor travel time, unfinished vehicles, and teleports. Also report side completed-only time loss and insertion delay.
- Sensitivity: the primary formula with charges of 0, 900, and 1800 seconds applied to both unfinished vehicles and teleport events.
- Training: 200 trials on common random seeds 0–2, including the exact textbook plan as trial 0; reject candidates with more than baseline + 2 teleports on any paired seed. Rescore the top 10 on seeds 3–12 and select the lowest feasible mean primary score; retain textbook as a feasible fallback. No tuning on final test seeds.
- Final test: brand-new seeds 13–32 (20 seeds), unused by the existing artifacts and audits, comparing textbook, frozen current v1, and v2 on PM holdout, continuous full PM, and estimated night. Preserve existing routes, warmup, drain, phase order and clearances. PM full and holdout overlap and are not independent replications.
- Inference: one-sided paired Wilcoxon signed-rank tests, alternative candidate < textbook, paired by seed. The confirmatory comparison is v2 versus textbook on the primary PM holdout endpoint, nominal alpha .05; v1 comparisons, full PM, night, sensitivities and secondary endpoints are descriptive/unadjusted. All-zero paired differences give p=1. Report constraint success independently of significance.
- Caveats: fixed fitted demand tests simulation randomness and later queues, not unseen measured traffic; historical 2018 counts, three estimated quarter-hour profiles, imperfect count fit, and teleports limit field applicability.
