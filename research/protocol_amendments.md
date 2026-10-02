# Protocol amendments before empirical outcome inspection

## 2026-09-29 — allocation-rule label maturity

The original tentative 2016–2021 evaluation range is insufficient to train an allocation rule in 2016–2018 and deploy it in 2019: the development outcomes mature only three years later. Before any dataset outcomes have been inspected, set development decisions to 2013–2015, reserve 2016–2017 as an allocation-learning embargo, and evaluate the frozen allocation rule at year-end 2018–2021. Each prediction origin separately restricts its supervised training cohorts to origin minus three years. A year-end 2018 decision can use outcomes observed through year-end 2018; this is not a forecast made at the beginning of 2018.

If the early cohort cannot support estimation, adopt an explicitly chronological rolling rule trained only on policy outcomes from origins at most t−3. Do not silently treat late-maturing development outcomes as available sooner. The final feasible choice must be fixed before inspecting held-out comparisons.

## 2026-09-29 — dual-objective interpretation

The common predictor targets subsequent technological attention. If it were perfectly specified, score-only top K would maximize the conditional expected sum of that target. Therefore an exploration quota is not assumed to dominate top K on the same target. The primary management contribution is the observable trade-off between total attention capture and preservation of technologically distant signals. A quota that beats top K on total realized attention is evidence of forecast error or distributional heterogeneity, not a general theorem that exploration improves firm performance.

## 2026-09-29 — dependence on human validation removed

No expert recruitment channel is presently established. The independently executable core study is historical patent intelligence and a limited-capacity signal portfolio. It will not label recommendations as expert-approved, commercially viable or actually adopted. Real expert validation may later strengthen the paper, but the manuscript cannot presuppose it.

## 2026-09-29 — comparable text measurement and outcome-aligned scoring

Before receiving the empirical citation outcomes, fix title-only TF–IDF for historical portfolio centroids, candidate relevance and MMR distances. Cross-domain history contains titles whereas domain candidates also contain abstracts; using unequal text fields would confound distance with document length and availability. Fit this title vocabulary on the same mature historical training cohorts, separately from the title-plus-abstract prediction vocabulary. Harmonized at-issue CPC and IPC subclasses define the primary unfamiliarity indicator; neither retrospectively assigned classifications nor missing classes establish novelty.

Use gradient-boosted binary classification as the primary high-attention probability score, matching the main decision outcome. Keep ridge prediction of log external citation attention, early-attention popularity and organizational title similarity as distinct baselines. Claims counts are not supplied by the acquired derived metadata and are omitted rather than represented as observed zeros. The main classifier's settings are fixed before outcome inspection; calibration is evaluated but not tuned on held-out cohorts. Title distance and predictor features have separate documented roles.

## 2026-09-29 — primary comparison and limited diagnostics

Designate boosted classification with K=30 as the primary descriptive comparison before any empirical outcomes are available. K=10 and K=50 establish capacity sensitivity; they are not independent discoveries. Present the full fixed-quota trade-off curve and both development-selected retention scenarios (90% and 100%). These are analytical scenarios, not measured managerial tolerance thresholds. Report held-out violations without retuning. The frozen rule is a small transparent decision rule, not a claim to a new optimization algorithm.

Add paired annual and leave-one-year-out summaries; organization resampling intervals condition on the observed historical candidate environment. Audit reuse of patents actually added or removed relative to top K. Decompose paired changes into the prespecified core and related-technology groups. Report the realized distant-pool opportunity rate and an ex-post slot-supply diagnostic; where no distant candidate exists the distant gain and its diagnostic remain zero. One supply-stratified concentration comparison uses development-fixed cutpoints and common support. No causal inference about concentration follows from this standardization.

The canonical candidate corpus requires a documented organizational owner, excludes duplicate grants of the same application by keeping the earliest visible grant, and retains missing abstracts for classification-eligible candidates. The main label excludes a citing record if any documented owner overlaps the cited patent's owners, and excludes same-application links. An applicant-citation sensitivity and retrospective disambiguated-owner outcome sensitivity are planned. Complete international family de-duplication is unavailable and will not be claimed.

## 2026-09-29 — mechanical implications of a deterministic reservation

For a fixed score ranking, the deterministic minimum-quota policy retains every distant candidate already present in the unconstrained top K. If the quota binds, its additions are distant and its removals are familiar. Therefore distant high-attention capture cannot decrease under this particular policy: the sign of that gain is not an empirical discovery. The informative quantities are how many additional high-attention signals occur among the displaced slots, how many other high-attention signals are lost, their out-of-time balance, comparison with MMR and randomized reservations, and persistence under alternative outcome measurements. Let g be high-attention additions and l high-attention removals. Then the paired distant gain is g and total gain is g−l. Check these identities in the saved change decomposition. Do not frame a positive distant gain alone as evidence for organizational exploration theory.

## 2026-09-29 18:08 local — development-pilot measurement correction

The first real-data pilot used only 2013–2015 decisions and the ten largest historically eligible organizations per year. No held-out policy results had been computed or inspected. It exposed an integer-tie problem in the proposed within-cohort upper-decile label: the positive proportion was 15.47% in 2013, 12.24% in 2014 and 30.41% in 2015, when the 90th-percentile cutoff fell to one citing organization. Calling the last event high attention would obscure a change in the outcome's meaning.

Before held-out evaluation, replace the primary event with a stable, interpretable definition: at least two distinct documented external citing organizations within the same three-year window. Call this multi-organization citation reach or a subsequent citation signal, rather than an exact top-decile outcome. Keep the original cohort-quantile definition as a fixed-list measurement sensitivity and report its actual tie-expanded rates. This is a documented, development-informed design revision, not a public preregistration claim or a change made after comparing held-out policy winners. All classifiers and allocation rules in the final run will be fitted to the revised event. The pilot's forecast and policy outputs are not final evidence and will not be pooled with the final study.
