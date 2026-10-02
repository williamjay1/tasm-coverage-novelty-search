# v8 Focused sensitivity and four-contrast joint inference

Route: SSCI technology-management archival replay. These are supplementary analyses of already examined outcomes, not an independent extension or organizational-use validation. No prediction training, source download, account access or2022 evaluation.

## Actual budget execution

{
  "status": "PASS",
  "seconds": 56.22249770001508,
  "policy_rows": 111700,
  "selected_events": 3522080,
  "feasibility_rows": 37258,
  "checks": 71608,
  "predictor_fits": 0,
  "new_source_acquisition": 0
}

## Joint family inference

{
  "status": "PASS",
  "seconds": 7.063271899998654,
  "draws_each": 4000,
  "family_size": 4,
  "global_unique_org_keys": 432,
  "global_unique_patent_keys": 28142,
  "shared_weights_across_all_four": true,
  "critical_values": {
    "paired_organization": 2.5449454006158594,
    "crossed_org_patent_sensitivity": 3.0465674045905
  },
  "construction": "Bootstrap distribution centered at each observed point; empirical SD standardizes departures; maximum absolute departure over the fixed four-contrast family gives one common 95% critical value. This is approximate fixed-list simultaneous inference, not an exact finite-sample coverage claim.",
  "crossed_caveat": "Crossed ranges retain complete-pool exposure denominators and are dependence sensitivity; they do not establish nominal frequentist coverage.",
  "p_values": "None computed or added. No multiplicity testing of identities, d distributions, descriptive parameter tables or handoff cases."
}

## Matched random reference

{
  "status": "PASS",
  "seconds": 21.68154879999929,
  "seeds": 100,
  "strata_checks": 286600,
  "n_situations_each_seed": "{('battery', 'boosting'): 356, ('battery', 'ridge'): 356, ('electronics', 'boosting'): 1077, ('electronics', 'ridge'): 1077}",
  "main_estimate": "Exact finite-pool conditional expectation, not seed-average estimate",
  "matched_dimensions": "30 total,9 core,exact actual unfamiliar count of N9m3,identical21 noncore IDs",
  "uniform_scheme": "Without replacement within unfamiliar core and familiar core strata independently",
  "meaning": "Tests ranking-specific selection against arbitrary selection at the identical observed composition. It does not estimate a causal organizational effect or provide a novelty placebo.",
  "seed_uncertainty": "Between-seed variation is Monte Carlo selection variation; 100 seeds do not add independent organizations."
}

## Complete-window cohort

{
  "status": "PASS",
  "seconds": 4.302360100002261,
  "origins": [
    2018,
    2019
  ],
  "horizons": [
    2,
    3,
    5
  ],
  "candidate_label_rows": 66147,
  "selected_events_per_window": 191100,
  "sources": [
    {
      "task": "battery",
      "included_candidates": 13481,
      "complete_five_year_filtered_edges": 19798
    },
    {
      "task": "electronics",
      "included_candidates": 8568,
      "complete_five_year_filtered_edges": 9897
    }
  ],
  "checks": [
    {
      "task": "battery",
      "check": "three_year_rebuild_task_linked",
      "candidate_ids": 13481,
      "mismatches": 0
    },
    {
      "task": "battery",
      "check": "three_year_rebuild_general_reach",
      "candidate_ids": 13481,
      "mismatches": 0
    },
    {
      "task": "electronics",
      "check": "three_year_rebuild_task_linked",
      "candidate_ids": 8568,
      "mismatches": 0
    },
    {
      "task": "electronics",
      "check": "three_year_rebuild_general_reach",
      "candidate_ids": 8568,
      "mismatches": 0
    },
    {
      "task": "battery",
      "check": "five_year_old_cache_task_linked",
      "candidate_ids": 13481,
      "mismatches": 0
    },
    {
      "task": "battery",
      "check": "five_year_old_cache_general_reach",
      "candidate_ids": 13481,
      "mismatches": 0
    },
    {
      "check": "window_monotonicity_task_linked",
      "passed": true
    },
    {
      "check": "window_monotonicity_general_reach",
      "passed": true
    }
  ],
  "scope": "Identical2018–2019 origin situations/lists for2/3/5 windows; 2020/2021 never labeled as complete five-year observations",
  "three_year_values_all_recovered": true,
  "new_raw_scans": 0
}

## Four simultaneous task-link ranges

| task | model | n_situations | n_organizations | point | metric | comparison | method | draws | family_size | bootstrap_sd | joint_critical | lower | upper | bootstrap_mean | seed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| battery | boosting | 356 | 114 | -0.014045 | task_linked | N30_C9_m3_minus_B30_C9 | paired_organization | 4000 | 4 | 0.012834 | 2.544945 | -0.046707 | 0.018617 | -0.013812 | 2026100281 |
| battery | ridge | 356 | 114 | -0.022472 | task_linked | N30_C9_m3_minus_B30_C9 | paired_organization | 4000 | 4 | 0.010797 | 2.544945 | -0.049950 | 0.005006 | -0.022263 | 2026100281 |
| electronics | boosting | 1077 | 371 | 0.005571 | task_linked | N30_C9_m3_minus_B30_C9 | paired_organization | 4000 | 4 | 0.003956 | 2.544945 | -0.004497 | 0.015639 | 0.005548 | 2026100281 |
| electronics | ridge | 1077 | 371 | -0.001857 | task_linked | N30_C9_m3_minus_B30_C9 | paired_organization | 4000 | 4 | 0.002579 | 2.544945 | -0.008421 | 0.004707 | -0.001831 | 2026100281 |
| battery | boosting | 356 | 114 | -0.014045 | task_linked | N30_C9_m3_minus_B30_C9 | crossed_org_patent_sensitivity | 4000 | 4 | 0.044754 | 3.046567 | -0.150392 | 0.122302 | -0.012972 | 2026100281 |
| battery | ridge | 356 | 114 | -0.022472 | task_linked | N30_C9_m3_minus_B30_C9 | crossed_org_patent_sensitivity | 4000 | 4 | 0.027464 | 3.046567 | -0.106143 | 0.061199 | -0.022664 | 2026100281 |
| electronics | boosting | 1077 | 371 | 0.005571 | task_linked | N30_C9_m3_minus_B30_C9 | crossed_org_patent_sensitivity | 4000 | 4 | 0.011905 | 3.046567 | -0.030697 | 0.041839 | 0.005328 | 2026100281 |
| electronics | ridge | 1077 | 371 | -0.001857 | task_linked | N30_C9_m3_minus_B30_C9 | crossed_org_patent_sensitivity | 4000 | 4 | 0.004934 | 3.046567 | -0.016890 | 0.013176 | -0.001875 | 2026100281 |

The inferential family comprises only four fixed C9m3−B9 task-link contrasts; identities and descriptive parameter summaries are not hypothesis tests. Global organization and patent weights are shared within each draw across both tasks/rankers. Centered maximum standardized departures give one family critical value. Organization ranges are approximate bootstrap intervals; crossed ranges are dependence sensitivities rather than established exact-coverage confidence intervals. No additional p-values.

## Complete paired budget/floor/allocation summaries

| task | model | axis | K | C | m | support | original_situations | n_situations | n_organizations | n_binding | introduced_events | mean_allocation_delta_task_linked | mean_within_delta_task_linked | mean_within_delta_general_reach | mean_within_delta_novel_document_exposure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| battery | boosting | allocation_floor3 | 30 | 3 | 3 | individual_feasible | 356 | 356 | 114 | 313 | 517 | -0.421348 | 0.028090 | 0.053371 | 1.452247 |
| battery | boosting | allocation_floor3 | 30 | 3 | 3 | axis_common | 356 | 356 | 114 | 313 | 517 | -0.421348 | 0.028090 | 0.053371 | 1.452247 |
| battery | boosting | allocation_floor3 | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | allocation_floor3 | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | allocation_floor3 | 30 | 15 | 3 | individual_feasible | 356 | 356 | 114 | 19 | 28 | 2.587079 | 0.028090 | 0.011236 | 0.078652 |
| battery | boosting | allocation_floor3 | 30 | 15 | 3 | axis_common | 356 | 356 | 114 | 19 | 28 | 2.587079 | 0.028090 | 0.011236 | 0.078652 |
| battery | boosting | capacity_absolute | 20 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 56 | 89 | 1.536517 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_absolute | 20 | 9 | 3 | axis_common | 356 | 356 | 114 | 56 | 89 | 1.536517 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_absolute | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_absolute | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_absolute | 50 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 56 | 89 | 0.297753 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_absolute | 50 | 9 | 3 | axis_common | 356 | 356 | 114 | 56 | 89 | 0.297753 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_fractional | 20 | 6 | 2 | individual_feasible | 356 | 356 | 114 | 45 | 58 | 0.862360 | -0.016854 | -0.050562 | 0.162921 |
| battery | boosting | capacity_fractional | 20 | 6 | 2 | axis_common | 356 | 356 | 114 | 45 | 58 | 0.862360 | -0.016854 | -0.050562 | 0.162921 |
| battery | boosting | capacity_fractional | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_fractional | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | capacity_fractional | 50 | 15 | 5 | individual_feasible | 356 | 356 | 114 | 59 | 122 | 1.769663 | 0.053371 | 0.025281 | 0.342697 |
| battery | boosting | capacity_fractional | 50 | 15 | 5 | axis_common | 356 | 356 | 114 | 59 | 122 | 1.769663 | 0.053371 | 0.025281 | 0.342697 |
| battery | boosting | floor_at9 | 30 | 9 | 0 | individual_feasible | 356 | 356 | 114 | 0 | 0 | 1.073034 | 0.000000 | 0.000000 | 0.000000 |
| battery | boosting | floor_at9 | 30 | 9 | 0 | axis_common | 356 | 356 | 114 | 0 | 0 | 1.073034 | 0.000000 | 0.000000 | 0.000000 |
| battery | boosting | floor_at9 | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | floor_at9 | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 56 | 89 | 1.073034 | -0.014045 | -0.028090 | 0.250000 |
| battery | boosting | floor_at9 | 30 | 9 | 6 | individual_feasible | 356 | 356 | 114 | 231 | 582 | 1.073034 | -0.022472 | -0.078652 | 1.634831 |
| battery | boosting | floor_at9 | 30 | 9 | 6 | axis_common | 356 | 356 | 114 | 231 | 582 | 1.073034 | -0.022472 | -0.078652 | 1.634831 |
| battery | boosting | floor_at9 | 30 | 9 | 9 | individual_feasible | 356 | 356 | 114 | 352 | 1552 | 1.073034 | -0.053371 | -0.095506 | 4.359551 |
| battery | boosting | floor_at9 | 30 | 9 | 9 | axis_common | 356 | 356 | 114 | 352 | 1552 | 1.073034 | -0.053371 | -0.095506 | 4.359551 |
| battery | ridge | allocation_floor3 | 30 | 3 | 3 | individual_feasible | 356 | 356 | 114 | 305 | 550 | -0.241573 | -0.407303 | -0.373596 | 1.544944 |
| battery | ridge | allocation_floor3 | 30 | 3 | 3 | axis_common | 356 | 356 | 114 | 305 | 550 | -0.241573 | -0.407303 | -0.373596 | 1.544944 |
| battery | ridge | allocation_floor3 | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | allocation_floor3 | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | allocation_floor3 | 30 | 15 | 3 | individual_feasible | 356 | 356 | 114 | 4 | 5 | 2.154494 | -0.002809 | 0.000000 | 0.014045 |
| battery | ridge | allocation_floor3 | 30 | 15 | 3 | axis_common | 356 | 356 | 114 | 4 | 5 | 2.154494 | -0.002809 | 0.000000 | 0.014045 |
| battery | ridge | capacity_absolute | 20 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 36 | 47 | 1.117978 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_absolute | 20 | 9 | 3 | axis_common | 356 | 356 | 114 | 36 | 47 | 1.117978 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_absolute | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_absolute | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_absolute | 50 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 36 | 47 | 0.016854 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_absolute | 50 | 9 | 3 | axis_common | 356 | 356 | 114 | 36 | 47 | 0.016854 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_fractional | 20 | 6 | 2 | individual_feasible | 356 | 356 | 114 | 73 | 99 | 0.485955 | -0.008427 | -0.019663 | 0.278090 |
| battery | ridge | capacity_fractional | 20 | 6 | 2 | axis_common | 356 | 356 | 114 | 73 | 99 | 0.485955 | -0.008427 | -0.019663 | 0.278090 |
| battery | ridge | capacity_fractional | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_fractional | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | capacity_fractional | 50 | 15 | 5 | individual_feasible | 356 | 356 | 114 | 31 | 53 | 1.488764 | 0.036517 | 0.025281 | 0.148876 |
| battery | ridge | capacity_fractional | 50 | 15 | 5 | axis_common | 356 | 356 | 114 | 31 | 53 | 1.488764 | 0.036517 | 0.025281 | 0.148876 |
| battery | ridge | floor_at9 | 30 | 9 | 0 | individual_feasible | 356 | 356 | 114 | 0 | 0 | 0.674157 | 0.000000 | 0.000000 | 0.000000 |
| battery | ridge | floor_at9 | 30 | 9 | 0 | axis_common | 356 | 356 | 114 | 0 | 0 | 0.674157 | 0.000000 | 0.000000 | 0.000000 |
| battery | ridge | floor_at9 | 30 | 9 | 3 | individual_feasible | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | floor_at9 | 30 | 9 | 3 | axis_common | 356 | 356 | 114 | 36 | 47 | 0.674157 | -0.022472 | -0.016854 | 0.132022 |
| battery | ridge | floor_at9 | 30 | 9 | 6 | individual_feasible | 356 | 356 | 114 | 194 | 471 | 0.674157 | 0.016854 | -0.008427 | 1.323034 |
| battery | ridge | floor_at9 | 30 | 9 | 6 | axis_common | 356 | 356 | 114 | 194 | 471 | 0.674157 | 0.016854 | -0.008427 | 1.323034 |
| battery | ridge | floor_at9 | 30 | 9 | 9 | individual_feasible | 356 | 356 | 114 | 353 | 1442 | 0.674157 | 0.047753 | -0.081461 | 4.050562 |
| battery | ridge | floor_at9 | 30 | 9 | 9 | axis_common | 356 | 356 | 114 | 353 | 1442 | 0.674157 | 0.047753 | -0.081461 | 4.050562 |
| electronics | boosting | allocation_floor3 | 30 | 3 | 3 | individual_feasible | 1077 | 1076 | 371 | 872 | 1352 | -3.657063 | -0.148699 | -0.105019 | 1.256506 |
| electronics | boosting | allocation_floor3 | 30 | 3 | 3 | axis_common | 1077 | 1072 | 370 | 869 | 1347 | -3.669776 | -0.149254 | -0.105410 | 1.256530 |
| electronics | boosting | allocation_floor3 | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 45 | 58 | -2.229341 | 0.005571 | -0.003714 | 0.053853 |
| electronics | boosting | allocation_floor3 | 30 | 9 | 3 | axis_common | 1077 | 1072 | 370 | 44 | 57 | -2.237873 | 0.005597 | -0.003731 | 0.053172 |
| electronics | boosting | allocation_floor3 | 30 | 15 | 3 | individual_feasible | 1077 | 1073 | 370 | 4 | 4 | -0.879776 | -0.001864 | -0.001864 | 0.003728 |
| electronics | boosting | allocation_floor3 | 30 | 15 | 3 | axis_common | 1077 | 1072 | 370 | 4 | 4 | -0.876866 | -0.001866 | -0.001866 | 0.003731 |
| electronics | boosting | capacity_absolute | 20 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 45 | 58 | -0.925720 | 0.005571 | -0.003714 | 0.053853 |
| electronics | boosting | capacity_absolute | 20 | 9 | 3 | axis_common | 1077 | 1073 | 369 | 45 | 58 | -0.926375 | 0.005592 | -0.003728 | 0.054054 |
| electronics | boosting | capacity_absolute | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 45 | 58 | -2.229341 | 0.005571 | -0.003714 | 0.053853 |
| electronics | boosting | capacity_absolute | 30 | 9 | 3 | axis_common | 1077 | 1073 | 369 | 45 | 58 | -2.227400 | 0.005592 | -0.003728 | 0.054054 |
| electronics | boosting | capacity_absolute | 50 | 9 | 3 | individual_feasible | 1077 | 1073 | 369 | 45 | 58 | -4.472507 | 0.005592 | -0.003728 | 0.054054 |
| electronics | boosting | capacity_absolute | 50 | 9 | 3 | axis_common | 1077 | 1073 | 369 | 45 | 58 | -4.472507 | 0.005592 | -0.003728 | 0.054054 |
| electronics | boosting | capacity_fractional | 20 | 6 | 2 | individual_feasible | 1077 | 1077 | 371 | 53 | 58 | -1.560817 | 0.002786 | 0.003714 | 0.053853 |
| electronics | boosting | capacity_fractional | 20 | 6 | 2 | axis_common | 1077 | 1070 | 369 | 52 | 57 | -1.567290 | 0.002804 | 0.003738 | 0.053271 |
| electronics | boosting | capacity_fractional | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 45 | 58 | -2.229341 | 0.005571 | -0.003714 | 0.053853 |
| electronics | boosting | capacity_fractional | 30 | 9 | 3 | axis_common | 1077 | 1070 | 369 | 44 | 57 | -2.237383 | 0.005607 | -0.003738 | 0.053271 |
| electronics | boosting | capacity_fractional | 50 | 15 | 5 | individual_feasible | 1077 | 1070 | 369 | 36 | 54 | -3.065421 | -0.008411 | -0.006542 | 0.050467 |
| electronics | boosting | capacity_fractional | 50 | 15 | 5 | axis_common | 1077 | 1070 | 369 | 36 | 54 | -3.065421 | -0.008411 | -0.006542 | 0.050467 |
| electronics | boosting | floor_at9 | 30 | 9 | 0 | individual_feasible | 1077 | 1077 | 371 | 0 | 0 | -2.229341 | 0.000000 | 0.000000 | 0.000000 |
| electronics | boosting | floor_at9 | 30 | 9 | 0 | axis_common | 1077 | 1074 | 371 | 0 | 0 | -2.238361 | 0.000000 | 0.000000 | 0.000000 |
| electronics | boosting | floor_at9 | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 45 | 58 | -2.229341 | 0.005571 | -0.003714 | 0.053853 |
| electronics | boosting | floor_at9 | 30 | 9 | 3 | axis_common | 1077 | 1074 | 371 | 44 | 57 | -2.238361 | 0.005587 | -0.003724 | 0.053073 |
| electronics | boosting | floor_at9 | 30 | 9 | 6 | individual_feasible | 1077 | 1075 | 371 | 532 | 1006 | -2.235349 | -0.141395 | -0.049302 | 0.935814 |
| electronics | boosting | floor_at9 | 30 | 9 | 6 | axis_common | 1077 | 1074 | 371 | 531 | 1005 | -2.238361 | -0.141527 | -0.049348 | 0.935754 |
| electronics | boosting | floor_at9 | 30 | 9 | 9 | individual_feasible | 1077 | 1074 | 371 | 1051 | 3780 | -2.238361 | -0.531657 | -0.243017 | 3.519553 |
| electronics | boosting | floor_at9 | 30 | 9 | 9 | axis_common | 1077 | 1074 | 371 | 1051 | 3780 | -2.238361 | -0.531657 | -0.243017 | 3.519553 |
| electronics | ridge | allocation_floor3 | 30 | 3 | 3 | individual_feasible | 1077 | 1076 | 371 | 776 | 1108 | -4.170074 | -0.136617 | -0.006506 | 1.029740 |
| electronics | ridge | allocation_floor3 | 30 | 3 | 3 | axis_common | 1077 | 1072 | 370 | 772 | 1099 | -4.185634 | -0.136194 | -0.005597 | 1.025187 |
| electronics | ridge | allocation_floor3 | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 14 | 15 | -2.655525 | -0.001857 | -0.002786 | 0.013928 |
| electronics | ridge | allocation_floor3 | 30 | 9 | 3 | axis_common | 1077 | 1072 | 370 | 13 | 14 | -2.669776 | -0.001866 | -0.002799 | 0.013060 |
| electronics | ridge | allocation_floor3 | 30 | 15 | 3 | individual_feasible | 1077 | 1073 | 370 | 0 | 0 | -1.200373 | 0.000000 | 0.000000 | 0.000000 |
| electronics | ridge | allocation_floor3 | 30 | 15 | 3 | axis_common | 1077 | 1072 | 370 | 0 | 0 | -1.199627 | 0.000000 | 0.000000 | 0.000000 |
| electronics | ridge | capacity_absolute | 20 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 14 | 15 | -1.532033 | -0.001857 | -0.002786 | 0.013928 |
| electronics | ridge | capacity_absolute | 20 | 9 | 3 | axis_common | 1077 | 1073 | 369 | 14 | 15 | -1.530289 | -0.001864 | -0.002796 | 0.013979 |
| electronics | ridge | capacity_absolute | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 14 | 15 | -2.655525 | -0.001857 | -0.002786 | 0.013928 |
| electronics | ridge | capacity_absolute | 30 | 9 | 3 | axis_common | 1077 | 1073 | 369 | 14 | 15 | -2.657036 | -0.001864 | -0.002796 | 0.013979 |
| electronics | ridge | capacity_absolute | 50 | 9 | 3 | individual_feasible | 1077 | 1073 | 369 | 14 | 15 | -4.747437 | -0.001864 | -0.002796 | 0.013979 |
| electronics | ridge | capacity_absolute | 50 | 9 | 3 | axis_common | 1077 | 1073 | 369 | 14 | 15 | -4.747437 | -0.001864 | -0.002796 | 0.013979 |
| electronics | ridge | capacity_fractional | 20 | 6 | 2 | individual_feasible | 1077 | 1077 | 371 | 26 | 27 | -2.288765 | 0.005571 | -0.001857 | 0.025070 |
| electronics | ridge | capacity_fractional | 20 | 6 | 2 | axis_common | 1077 | 1070 | 369 | 25 | 26 | -2.297196 | 0.005607 | -0.001869 | 0.024299 |
| electronics | ridge | capacity_fractional | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 14 | 15 | -2.655525 | -0.001857 | -0.002786 | 0.013928 |
| electronics | ridge | capacity_fractional | 30 | 9 | 3 | axis_common | 1077 | 1070 | 369 | 13 | 14 | -2.670093 | -0.001869 | -0.002804 | 0.013084 |
| electronics | ridge | capacity_fractional | 50 | 15 | 5 | individual_feasible | 1077 | 1070 | 369 | 9 | 9 | -3.203738 | -0.002804 | 0.000000 | 0.008411 |
| electronics | ridge | capacity_fractional | 50 | 15 | 5 | axis_common | 1077 | 1070 | 369 | 9 | 9 | -3.203738 | -0.002804 | 0.000000 | 0.008411 |
| electronics | ridge | floor_at9 | 30 | 9 | 0 | individual_feasible | 1077 | 1077 | 371 | 0 | 0 | -2.655525 | 0.000000 | 0.000000 | 0.000000 |
| electronics | ridge | floor_at9 | 30 | 9 | 0 | axis_common | 1077 | 1074 | 371 | 0 | 0 | -2.667598 | 0.000000 | 0.000000 | 0.000000 |
| electronics | ridge | floor_at9 | 30 | 9 | 3 | individual_feasible | 1077 | 1077 | 371 | 14 | 15 | -2.655525 | -0.001857 | -0.002786 | 0.013928 |
| electronics | ridge | floor_at9 | 30 | 9 | 3 | axis_common | 1077 | 1074 | 371 | 13 | 14 | -2.667598 | -0.001862 | -0.002793 | 0.013035 |
| electronics | ridge | floor_at9 | 30 | 9 | 6 | individual_feasible | 1077 | 1075 | 371 | 288 | 466 | -2.664186 | -0.026047 | -0.011163 | 0.433488 |
| electronics | ridge | floor_at9 | 30 | 9 | 6 | axis_common | 1077 | 1074 | 371 | 287 | 465 | -2.667598 | -0.026071 | -0.011173 | 0.432961 |
| electronics | ridge | floor_at9 | 30 | 9 | 9 | individual_feasible | 1077 | 1074 | 371 | 1021 | 2839 | -2.667598 | -0.291434 | -0.067970 | 2.643389 |
| electronics | ridge | floor_at9 | 30 | 9 | 9 | axis_common | 1077 | 1074 | 371 | 1021 | 2839 | -2.667598 | -0.291434 | -0.067970 | 2.643389 |

Compare K changes only within an axis and its common origin support. Fixed C9/m3 changes other capacity, whereas the fractional axis changes C/m with K; their meanings differ. On the fixed C9/m3 axis, B and N select the same core IDs at every K, and within each K the same noncore IDs cancel from N−B. Therefore identical within-allocation residuals across K20/30/50 are a design identity on common support, not new empirical robustness evidence. The allocation-versus-U contrast does change because U and the number of noncore positions change. The fractional axis instead changes the core selection/floor, allowing non-identical within-allocation outcomes. Every individual shortage remains in budget_feasibility.csv. The new fixed-m allocation endpoints C3/15 complement the existing v7 C6/12 results; this is not an outcome-chosen grid. All negative/zero returns retained.

## Exact matched-uniform expectation

| task | model | n_situations | n_organizations | mean_matched_unfamiliar | mean_deterministic_task | mean_uniform_expected_task | mean_task_rank_increment | mean_deterministic_general | mean_uniform_expected_general | mean_general_rank_increment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| battery | boosting | 356 | 114 | 4.890449 | 3.646067 | 1.935003 | 1.711065 | 8.615169 | 6.978350 | 1.636819 |
| battery | ridge | 356 | 114 | 5.081461 | 3.601124 | 2.114500 | 1.486624 | 9.421348 | 7.731107 | 1.690242 |
| electronics | boosting | 1077 | 371 | 5.529248 | 3.608171 | 2.731288 | 0.876882 | 3.564531 | 3.284380 | 0.280151 |
| electronics | ridge | 1077 | 371 | 6.363045 | 3.514392 | 2.521582 | 0.992810 | 3.453110 | 2.962774 | 0.490336 |

Random selection preserves each deterministic list’s core count, actual unfamiliar count and every noncore identifier. Expected values use finite-pool stratum label means; no Monte Carlo accuracy claim is needed for the main estimate.100 seeds are computational checks and selection variability, not independent organizations or causal placebo observations. This comparison assesses ranking within a fixed composition; it does not isolate a cognitive novelty effect.

##2/3/5grant-year windows on identical2018–2019 situations

| task | model | horizon | n_situations | n_organizations | task_linked_delta_allocation | general_reach_delta_allocation | task_linked_delta_C9m3 | general_reach_delta_C9m3 | task_linked_delta_legacy | general_reach_delta_legacy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| battery | boosting | 2 | 158 | 87 | 1.056962 | 0.031646 | 0.006329 | -0.006329 | -0.246835 | 0.158228 |
| battery | boosting | 3 | 158 | 87 | 1.582278 | 0.240506 | -0.012658 | -0.025316 | -0.259494 | 0.525316 |
| battery | boosting | 5 | 158 | 87 | 1.829114 | 0.664557 | -0.006329 | 0.037975 | -0.335443 | 0.632911 |
| battery | ridge | 2 | 158 | 87 | 0.962025 | -0.196203 | -0.025316 | 0.000000 | -0.151899 | 0.094937 |
| battery | ridge | 3 | 158 | 87 | 1.322785 | -0.234177 | -0.018987 | 0.006329 | 0.265823 | 0.436709 |
| battery | ridge | 5 | 158 | 87 | 2.386076 | -0.348101 | -0.018987 | 0.006329 | -0.778481 | 0.582278 |
| electronics | boosting | 2 | 479 | 271 | -1.513570 | -0.231733 | 0.004175 | 0.002088 | 0.004175 | 0.002088 |
| electronics | boosting | 3 | 479 | 271 | -2.436326 | -0.212944 | 0.008351 | 0.002088 | 0.008351 | 0.002088 |
| electronics | boosting | 5 | 479 | 271 | -3.665971 | -1.158664 | 0.006263 | 0.006263 | 0.006263 | 0.006263 |
| electronics | ridge | 2 | 479 | 271 | -1.670146 | 0.104384 | 0.002088 | 0.000000 | 0.002088 | 0.000000 |
| electronics | ridge | 3 | 479 | 271 | -2.304802 | 0.244259 | 0.004175 | 0.002088 | 0.004175 | 0.002088 |
| electronics | ridge | 5 | 479 | 271 | -3.705637 | -0.828810 | 0.004175 | 0.002088 | 0.004175 | 0.002088 |

2020/2021 are excluded from every row, including2/3year comparisons, so the5year horizon is complete through2024. The denominator difference from the356/1077 full period is explicit. Reconstructed3year candidate indicators match every original included label, and the5year battery indicators additionally match the old5year cache. These are archival citing-grant windows, not times of adoption or engineering use.

## Local replay and dependencies

There are two different reproduction layers. A compact local statistical replay package needs this script, `policy_core.py`, the four frozen v7 Parquets (`effective_pools`, `effective_selected`, `effective_contrast_detail`, `effective_signed_events`), the v8 protocol/lock, and `mature_window_candidate_labels.parquet`. Preserve the project-relative layout. Run `python -B scripts/revision_v8_sensitivity_analysis.py --pilot`, and then the individual `--budget`, `--joint`, `--random` commands. `--window-summary-replay` rebuilds all fixed-list 2/3/5-year statistical summaries from the cached mature candidate labels and verifies their three-year indicators against v7 pools; it does not reconstruct citation edges or re-establish maturity from source data. No source DuckDB is needed for this compact replay.

The full source-label reconstruction layer uses `--windows` or the no-flag full run and additionally requires the cached battery five-year edges/labels, electronics grants and the read-only canonical labels DuckDB with its `edges` table. It checks the original candidate-level three-year indicators and old battery five-year cache. No original source TSV scan is needed, but these source dependencies are not claimed to be inside the compact package. `--report` updates the report and complete local dependency hashes; it requires the source dependencies to be present. All dependency sizes/SHA values are enumerated in `sensitivity_source_manifest.json`. The 2022 protocol and lock are audited for preservation only and never used for new 2022 results.

Actual environment: Python 3.12.10, numpy==2.5.1, pandas==3.0.5, scipy==1.18.0, duckdb==1.5.5, pyarrow==25.0.0. These are the replay dependencies; no scikit-learn or predictor training is required.

## Storage and boundaries

New v8 outputs total 18,482,768 bytes, below the1GB cap. All sources remain on their original drives and are read-only inputs. Sparse or supply-limited cells are disclosed; supplementary designs do not provide new causal identification, independent cases from repeated selections, or new-sample confirmation. Source sizes/SHA values are recorded separately.
