# V3 decision-analysis design and execution record

Design recorded 1 October 2026 before executing the new factorial comparisons. V1/V2 battery outcomes, including the weak novelty-minus-matched-capacity contrasts, are already known. This is an exploratory historical decision-rule analysis for Technology Analysis & Strategic Management, not a blind prospective test or causal evaluation. The article route is SSCI technology-management evaluation; the standard is a meaningful task-allocation comparison with fair eligibility and evidence-matched claims, not a new algorithm or an econometric treatment effect.

## Fixed question and information set

Does increasing battery-domain capacity explain more of the observed domain-link yield than recorded novelty selection at the same capacity? The task outcome is fixed as `future_core_signal_1patent`: at least one subsequent external coded battery-thermal citing grant in the original next-three-calendar-year window. General and applicant two-organization events remain secondary proxy comparisons. All original 356 raw-name/core-task organization-years and their four historical environments are the admission denominator. Frozen original Boosting and Ridge scores remain equally reported; no winning ranker is selected for the narrative.

Existing core-task pools, source scores, task labels and fine-control selections suffice. All pool construction, histories and code-novelty fields are retained from V2. No new outcome fitting or task-specific classifier is required. D-drive free space was approximately 115 GB at the feasibility check. V1/V2 are read-only; all new outputs use `results/revision_v3/decision_*` and this script/report only.

## Two-stage list construction

K=30. First allocate exact core capacity C in {0,3,6,9,12,15,30}; then select core and noncore documents. A situation is capacity-feasible only if core supply >=C and noncore supply >=30−C. Never silently shrink C. Record every shortfall and retain all situations in the admission/feasibility register. A separate `full_core_priority` selects as many coded-core documents as possible up to30, fills any remaining slots from noncore, and explicitly records actual capacity. It is distinct from exact C=30 and from unconstrained score-only top30.

Within each capacity and ranker, compare score-ranked core selection with a recorded-new-group or recorded-new-pair floor r in {0,.3,.5}. The number reserved is ceil(C*r). Selection uses only the same eligible core candidates and the same forecast ranking; all highest-score 30−C noncore IDs are fixed. If novel supply is insufficient for the required floor, record an infeasible cell instead of shrinking the reservation. The r=0 reference is identical across novelty definitions. Pair contrasts use common feasible situations for all r=0/.3/.5 at that C/boundary; individual feasibility means are also retained and labelled. C=0 has no meaningful within-core novelty contrast.

Keep the original V2 q30 novelty lists and their capacity-matched controls as interpretation anchors. Reconstruct the same control for Ridge from frozen scores and original selected sets. These use quota-induced capacities rather than the new exact grid. Confirm that all coded-core pool candidates are non-external under strict four-character subclass externality, and report core-slot changes under that policy. Different candidate-domain qualification is a design distinction, not a different numerical exploration intensity.

## Decision differences and known conditions

For every feasible policy and paired comparison retain selected IDs, actual additions/removals, target-link totals, within-boundary composition, and win/tie/loss against the specified reference. Policy ordering uses the fixed core1 outcome; tied counts remain tied. Compare pairwise ordering by core1 with ordering by general/applicant events, distinguishing strict reversal, tie-discordance and agreement. Also compare ranking by the naive novelty-minus-unconstrained gain with ranking by novelty-minus-capacity-matched gain. Report all model/boundary/floor cells; do not select favourable comparisons.

Describe associations with origin-known core history, pool core fraction, recorded-novel candidate supply and whether a reservation changes the r0 list. Use fixed, interpretable bins (prior core grants3–5/6–10/>10; pool core fraction<.1/.1–.2/>=.2; supply exactly at floor vs above; binding vs nonbinding). No causal moderator claim, outcome-derived cutpoint, noninferiority margin or precision-null claim is planned.

## Shared-patent uncertainty

Expand contrasts into organization–year–patent contributions, including zero contributions for unchanged selected documents and an explicit separate eligibility/exposure register for unselected pool candidates. A policy's target-count difference is the sum of signed patent outcomes divided by the number of feasible situations. The point sum must reproduce every decision-level difference exactly.

For a small locked comparison set (both rankers: exact C9 versus unconstrained; full core priority versus unconstrained; original group/pair novelty versus matched; exact C9 group/pair at r=.3/.5 versus r0), use 2,000 draws, seed20261001. Report ordinary paired organization resampling and crossed organization/patent product reweighting. The latter uses independent mean-one, variance-one exponential weights on organization and patent IDs. All years of an organization share one organization weight; every occurrence of a grant shares one patent weight. Reweight signed outcome contributions without selecting lists again.

The crossed ratio denominator uses the complete eligible-pool exposure: each organization–year–patent receives exposure1/pool_n, so its unit-weight sum is one situation. Thus the statistic remains a count difference per standardized screening situation, rather than a mean per changed patent. Unselected contributions are exactly zero but remain in the exposure denominator. The bootstrap keeps the four observed annual environments; it is a dependency-sensitivity interval, not an exact finite-sample interval or new-environment performance guarantee. Product-weight bootstrap rationale: [Owen and Eckles (2012), Bootstrapping data arrays of arbitrary order](https://doi.org/10.1214/12-AOAS547). Their crossed-effects conditions are not asserted to be fully validated here; the original inconclusive organization intervals remain visible.

## Outcome-free desk-audit membership

Before new outcomes are summarized, copy the original core-combination q30 and matched-capacity memberships to `decision_case_membership.parquet`, retaining only organization/year/model/policy/patent/core/recorded-novel fields. No citation labels or scores appear in that file. The separate case agent locks an outcome-independent sampling rule from these memberships. These are existing V2 lists, not newly claimed unseen cases.

## Execution status

At protocol lock, implementation and results were pending. The completed run is recorded below, retaining the design and its actual narrowed bootstrap scope.


## Executed V3 results (1 October 2026)

All 356 original situations and 114 raw organization keys are retained as the admission denominator. Frozen Boost and Ridge scores, original eligible pools and original novelty fields are reused. No outcomes enter selection and no model is retrained. The exact grid fixes noncore IDs within each C/model; the floor is explicitly ceil(r*C). It is a minimum, so ranked filling may select further novel core documents. The earlier nearest-integer formula happens to agree for all planned C/r cells, but the implementation explicitly uses ceil; the exported audit gives every exact target and crosscheck.

Original q30 minus exact-core/noncore matched control:

| model | boundary | delta_task_T | delta_task_U | delta_general_T | delta_applicant_T | task_wins | task_ties | task_losses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boosting | core_newgroup | -0.070225 | 0.331461 | 0.081461 | 0.036517 | 50 | 241 | 65 |
| boosting | core_newpair | 0.050562 | 0.963483 | 0.294944 | 0.070225 | 119 | 149 | 88 |
| ridge | core_newgroup | 0.115169 | 0.367978 | 0.056180 | 0.005618 | 73 | 241 | 42 |
| ridge | core_newpair | 0.230337 | 0.929775 | 0.151685 | 0.109551 | 122 | 164 | 70 |

Exact C9 novelty-blind versus unconstrained top30 (pair novelty used for the U composition field):

| model | boundary | delta_task_T | delta_task_U | delta_general_T | delta_applicant_T | task_wins | task_ties | task_losses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boosting | core_newpair | 1.073034 | 0.595506 | -0.014045 | -0.140449 | 254 | 96 | 6 |
| ridge | core_newpair | 0.674157 | 0.595506 | -0.286517 | -0.109551 | 186 | 131 | 39 |

Origin-known context bins are defined from each ranker original top30 core seats before examining outcomes: low<9, equal9, high>9. These are descriptive associations, not causal moderators.

| model | original_core_context | situations | delta_task_T | task_wins | task_ties | task_losses |
| --- | --- | --- | --- | --- | --- | --- |
| boosting | equal9 | 17 | 0.000000 | 0 | 17 | 0 |
| boosting | high_gt9 | 24 | -0.166667 | 0 | 21 | 3 |
| boosting | low_lt9 | 315 | 1.225397 | 254 | 58 | 3 |
| ridge | equal9 | 13 | 0.000000 | 0 | 13 | 0 |
| ridge | high_gt9 | 28 | -1.571429 | 0 | 4 | 24 |
| ridge | low_lt9 | 315 | 0.901587 | 186 | 114 | 15 |

Grid feasibility:

| model | boundary | C_requested | novelty_floor | floor_target | admission_situations | feasible_situations |
| --- | --- | --- | --- | --- | --- | --- |
| boosting | core_newgroup | 0 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 0 | 0.300000 | 0 | 356 | 356 |
| boosting | core_newgroup | 0 | 0.500000 | 0 | 356 | 356 |
| boosting | core_newgroup | 3 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 3 | 0.300000 | 1 | 356 | 356 |
| boosting | core_newgroup | 3 | 0.500000 | 2 | 356 | 356 |
| boosting | core_newgroup | 6 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 6 | 0.300000 | 2 | 356 | 356 |
| boosting | core_newgroup | 6 | 0.500000 | 3 | 356 | 356 |
| boosting | core_newgroup | 9 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 9 | 0.300000 | 3 | 356 | 356 |
| boosting | core_newgroup | 9 | 0.500000 | 5 | 356 | 356 |
| boosting | core_newgroup | 12 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 12 | 0.300000 | 4 | 356 | 356 |
| boosting | core_newgroup | 12 | 0.500000 | 6 | 356 | 355 |
| boosting | core_newgroup | 15 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 15 | 0.300000 | 5 | 356 | 356 |
| boosting | core_newgroup | 15 | 0.500000 | 8 | 356 | 354 |
| boosting | core_newgroup | 30 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newgroup | 30 | 0.300000 | 9 | 356 | 353 |
| boosting | core_newgroup | 30 | 0.500000 | 15 | 356 | 352 |
| boosting | core_newpair | 0 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 0 | 0.300000 | 0 | 356 | 356 |
| boosting | core_newpair | 0 | 0.500000 | 0 | 356 | 356 |
| boosting | core_newpair | 3 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 3 | 0.300000 | 1 | 356 | 356 |
| boosting | core_newpair | 3 | 0.500000 | 2 | 356 | 356 |
| boosting | core_newpair | 6 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 6 | 0.300000 | 2 | 356 | 356 |
| boosting | core_newpair | 6 | 0.500000 | 3 | 356 | 356 |
| boosting | core_newpair | 9 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 9 | 0.300000 | 3 | 356 | 356 |
| boosting | core_newpair | 9 | 0.500000 | 5 | 356 | 356 |
| boosting | core_newpair | 12 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 12 | 0.300000 | 4 | 356 | 356 |
| boosting | core_newpair | 12 | 0.500000 | 6 | 356 | 356 |
| boosting | core_newpair | 15 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 15 | 0.300000 | 5 | 356 | 356 |
| boosting | core_newpair | 15 | 0.500000 | 8 | 356 | 356 |
| boosting | core_newpair | 30 | 0.000000 | 0 | 356 | 356 |
| boosting | core_newpair | 30 | 0.300000 | 9 | 356 | 356 |
| boosting | core_newpair | 30 | 0.500000 | 15 | 356 | 356 |
| ridge | core_newgroup | 0 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 0 | 0.300000 | 0 | 356 | 356 |
| ridge | core_newgroup | 0 | 0.500000 | 0 | 356 | 356 |
| ridge | core_newgroup | 3 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 3 | 0.300000 | 1 | 356 | 356 |
| ridge | core_newgroup | 3 | 0.500000 | 2 | 356 | 356 |
| ridge | core_newgroup | 6 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 6 | 0.300000 | 2 | 356 | 356 |
| ridge | core_newgroup | 6 | 0.500000 | 3 | 356 | 356 |
| ridge | core_newgroup | 9 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 9 | 0.300000 | 3 | 356 | 356 |
| ridge | core_newgroup | 9 | 0.500000 | 5 | 356 | 356 |
| ridge | core_newgroup | 12 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 12 | 0.300000 | 4 | 356 | 356 |
| ridge | core_newgroup | 12 | 0.500000 | 6 | 356 | 355 |
| ridge | core_newgroup | 15 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 15 | 0.300000 | 5 | 356 | 356 |
| ridge | core_newgroup | 15 | 0.500000 | 8 | 356 | 354 |
| ridge | core_newgroup | 30 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newgroup | 30 | 0.300000 | 9 | 356 | 353 |
| ridge | core_newgroup | 30 | 0.500000 | 15 | 356 | 352 |
| ridge | core_newpair | 0 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 0 | 0.300000 | 0 | 356 | 356 |
| ridge | core_newpair | 0 | 0.500000 | 0 | 356 | 356 |
| ridge | core_newpair | 3 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 3 | 0.300000 | 1 | 356 | 356 |
| ridge | core_newpair | 3 | 0.500000 | 2 | 356 | 356 |
| ridge | core_newpair | 6 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 6 | 0.300000 | 2 | 356 | 356 |
| ridge | core_newpair | 6 | 0.500000 | 3 | 356 | 356 |
| ridge | core_newpair | 9 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 9 | 0.300000 | 3 | 356 | 356 |
| ridge | core_newpair | 9 | 0.500000 | 5 | 356 | 356 |
| ridge | core_newpair | 12 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 12 | 0.300000 | 4 | 356 | 356 |
| ridge | core_newpair | 12 | 0.500000 | 6 | 356 | 356 |
| ridge | core_newpair | 15 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 15 | 0.300000 | 5 | 356 | 356 |
| ridge | core_newpair | 15 | 0.500000 | 8 | 356 | 356 |
| ridge | core_newpair | 30 | 0.000000 | 0 | 356 | 356 |
| ridge | core_newpair | 30 | 0.300000 | 9 | 356 | 356 |
| ridge | core_newpair | 30 | 0.500000 | 15 | 356 | 356 |

Paired intervals for the primary task endpoint (all six task/general/applicant T/U metrics are retained in CSV):

| model | boundary | metric | method | point | lower | upper |
| --- | --- | --- | --- | --- | --- | --- |
| boosting | core_newgroup | task_T | organization_bootstrap | -0.070225 | -0.155137 | 0.012277 |
| boosting | core_newgroup | task_T | crossed_org_patent_multiplier_sensitivity | -0.070225 | -0.374724 | 0.248026 |
| boosting | core_newgroup | task_U | organization_bootstrap | 0.331461 | 0.244044 | 0.415519 |
| boosting | core_newgroup | task_U | crossed_org_patent_multiplier_sensitivity | 0.331461 | 0.181007 | 0.578050 |
| boosting | core_newpair | task_T | organization_bootstrap | 0.050562 | -0.043366 | 0.148256 |
| boosting | core_newpair | task_T | crossed_org_patent_multiplier_sensitivity | 0.050562 | -0.727488 | 0.786716 |
| boosting | core_newpair | task_U | organization_bootstrap | 0.963483 | 0.877888 | 1.048719 |
| boosting | core_newpair | task_U | crossed_org_patent_multiplier_sensitivity | 0.963483 | 0.560578 | 1.561059 |
| ridge | core_newgroup | task_T | organization_bootstrap | 0.115169 | 0.043859 | 0.186030 |
| ridge | core_newgroup | task_T | crossed_org_patent_multiplier_sensitivity | 0.115169 | -0.111564 | 0.341546 |
| ridge | core_newgroup | task_U | organization_bootstrap | 0.367978 | 0.280692 | 0.457628 |
| ridge | core_newgroup | task_U | crossed_org_patent_multiplier_sensitivity | 0.367978 | 0.199732 | 0.613844 |
| ridge | core_newpair | task_T | organization_bootstrap | 0.230337 | 0.159517 | 0.308578 |
| ridge | core_newpair | task_T | crossed_org_patent_multiplier_sensitivity | 0.230337 | -0.454506 | 0.912455 |
| ridge | core_newpair | task_U | organization_bootstrap | 0.929775 | 0.837382 | 1.026895 |
| ridge | core_newpair | task_U | crossed_org_patent_multiplier_sensitivity | 0.929775 | 0.530698 | 1.537760 |

Selected-union patent contributions include unchanged selected documents with zero signed contribution. Complete pool candidates, including unselected candidates, are retained separately with exposure1/pool_n. Signed contribution sums exactly recover every original matched point contrast. Boost lists and all six endpoint totals exactly reproduce all 2,136 prior fine-control lists. The product multiplier reweights organization and patent IDs independently with Exp(1), keeps each list fixed and divides by weighted complete pool exposure. Its 2.5/97.5 percentile limits are dependency sensitivities, not exact coverage or environmental generalization. Four observed years and patent-family limitations remain.

Bootstrap scope was explicitly narrowed to four original q30 novelty-minus-matched comparisons (two novelty definitions, two rankers), each with 2,000 organization draws and 2,000 crossed multiplier draws, seed20261001. Grid intervals were not computed. The full exact grid and its paired win/tie/loss, annual and fixed-origin context points are supplied.

Outputs: decision_policy_detail.parquet; decision_selected.parquet; decision_policy_summary.csv; decision_grid_common_summary.csv; decision_feasibility.csv; decision_feasibility_summary.csv; decision_contrast_detail.parquet; decision_contrasts.csv; decision_context_contrasts.csv; decision_annual_contrasts.csv; decision_pool_exposure.parquet; decision_patent_exposure.csv; decision_patent_contributions.parquet; decision_bootstrap.csv; decision_bootstrap_notes.json; decision_audit.json. Existing decision_case_membership.parquet is preserved.

Final code-to-text correction: the original group q30 anchor uses a supply-capped target, with LGCHEMLTD2019/2020/2021 containing7/5/8 qualifying candidates. The pair q30 floor is met in all356 situations. This differs from the new grid's strict infeasibility rule and is now explicit in the article. Strict subclass nonoverlap excludes coded-core reserved candidates but leaves whole-list core means3.839888 (Boost) and3.853933 (Ridge). Final exchange, reversal and table checks are recorded in revision_v3_final_content_review.md.
