"""Secondary supply standardization and paired endpoint resampling.

Reads existing results without changing policies, primary metrics or their sample.
All intervals condition on the observed corpus; they do not assure future coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

CONTEXTS = ("concentrated", "diversified")
SEED = 20260929
GAIN = "delta_distant_high_attention_hits"
TOTAL = "delta_high_attention_hits"
HITS = "high_attention_hits"
BASE = "high_attention_hits_topk"
EXCESS = "excess_distant_gain"


def ratio(numerator, denominator):
    return float(numerator / denominator) if denominator > 0 else np.nan


def group_seed(key, seed):
    encoded = json.dumps([seed, *map(str, key)], ensure_ascii=True).encode()
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "little")


def joint_bootstrap(group, repeats=1000, seed=SEED):
    """The same organization draws determine both marginal endpoint intervals."""
    by_org = group.groupby("organization_id", sort=True).agg(
        distant_sum=(GAIN, "sum"), policy_sum=(HITS, "sum"),
        baseline_sum=(BASE, "sum"), decisions=(GAIN, "size"))
    count = len(by_org)
    result = dict(n_organizations=count, n_decisions=len(group),
                  mean_distant_gain=float(group[GAIN].mean()),
                  total_retention=ratio(group[HITS].sum(), group[BASE].sum()),
                  distant_gain_low=np.nan, distant_gain_high=np.nan,
                  retention_low=np.nan, retention_high=np.nan,
                  repeats_requested=repeats, repeats_run=0,
                  retention_zero_denominator_draws=0)
    if count < 5:
        result["interval_note"] = "suppressed_fewer_than_five_organizations"
        return result
    values = by_org.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    distant_draws = np.empty(repeats)
    retention_draws = np.full(repeats, np.nan)
    for start in range(0, repeats, 128):
        stop = min(start + 128, repeats)
        indices = rng.integers(0, count, size=(stop - start, count))
        totals = values[indices].sum(axis=1)
        distant_draws[start:stop] = totals[:, 0] / totals[:, 3]
        retention_draws[start:stop] = np.divide(
            totals[:, 1], totals[:, 2], out=np.full(stop - start, np.nan),
            where=totals[:, 2] > 0)
    result.update(repeats_run=repeats,
                  distant_gain_low=float(np.quantile(distant_draws, .025)),
                  distant_gain_high=float(np.quantile(distant_draws, .975)),
                  retention_zero_denominator_draws=int(np.isnan(retention_draws).sum()))
    # Discarding zero denominators would silently condition the ratio distribution.
    if np.isfinite(retention_draws).all():
        result.update(retention_low=float(np.quantile(retention_draws, .025)),
                      retention_high=float(np.quantile(retention_draws, .975)))
        result["interval_note"] = "fixed_corpus_organization_resampling"
    else:
        result["interval_note"] = "retention_interval_suppressed_zero_bootstrap_denominator"
    result["few_cluster_caution"] = count < 10
    return result


def derive_cutpoints(development, grouping):
    keys = ["organization_id", "year", *grouping]
    fields = ["pool_n", "distant_pool_n"]
    if (development.groupby(keys, dropna=False)[fields].nunique() > 1).any().any():
        raise ValueError("Opportunity supply varies across policies for a development decision")
    unique = development.drop_duplicates(keys).copy()
    unique["far_pool_fraction"] = unique.distant_pool_n / unique.pool_n
    unique["budget_fraction"] = unique.k / unique.pool_n
    cuts = unique.groupby(grouping, as_index=False, dropna=False).agg(
        far_supply_cut=("far_pool_fraction", "median"),
        budget_fraction_cut=("budget_fraction", "median"),
        development_decisions=("organization_id", "size"),
        development_first_year=("year", "min"),
        development_last_year=("year", "max"))
    return cuts


def context_standardization(paired, cuts, grouping):
    """Shared weights over year x two supply bins; descriptive, not causal."""
    data = paired.merge(cuts, on=grouping, how="left", validate="many_to_one", indicator=True)
    if not data["_merge"].eq("both").all():
        raise ValueError("A held-out model/budget/distance has no development cutpoints")
    data["far_supply_bin"] = np.where(data.far_pool_fraction >= data.far_supply_cut, "high", "low")
    data["budget_bin"] = np.where(data.budget_fraction >= data.budget_fraction_cut, "high", "low")
    strata = ["year", "far_supply_bin", "budget_bin"]
    summary_rows, cell_rows = [], []
    policy_groups = [*grouping, "policy"]
    outcomes = [GAIN, TOTAL, EXCESS, HITS, BASE]
    for key, group in data.groupby(policy_groups, sort=True, dropna=False):
        identity = dict(zip(policy_groups, key))
        counts = group.groupby([*strata, "context"], observed=True).size().unstack(fill_value=0)
        counts = counts.reindex(columns=list(CONTEXTS), fill_value=0)
        counts["overlap_count"] = counts[list(CONTEXTS)].min(axis=1)
        overlap_total = counts.overlap_count.sum()
        counts["common_weight"] = counts.overlap_count / overlap_total if overlap_total else 0.
        counts["common_support"] = counts.overlap_count > 0
        cell_table = counts.reset_index()
        for row in cell_table.to_dict("records"):
            cell_rows.append({**identity, **row})
        group = group.merge(cell_table[strata + ["common_weight", "common_support"]],
                            on=strata, how="left", validate="many_to_one")
        summary = {**identity, "n_decisions_all": len(group),
                   "n_common_cells": int(counts.common_support.sum()),
                   "n_supply_cells": len(counts),
                   "support_status": "available" if overlap_total else "no_common_support"}
        for context in CONTEXTS:
            g = group.loc[group.context.eq(context)]
            common = g.loc[g.common_support]
            prefix = context + "_"
            summary.update({prefix + "n_decisions": len(g),
                            prefix + "n_common_decisions": len(common),
                            prefix + "common_support_fraction": ratio(len(common), len(g)),
                            prefix + "raw_distant_gain": float(g[GAIN].mean()),
                            prefix + "raw_total_gain": float(g[TOTAL].mean()),
                            prefix + "raw_excess_gain": float(g[EXCESS].mean()),
                            prefix + "raw_retention": ratio(g[HITS].sum(), g[BASE].sum())})
            standardized = pd.Series(np.nan, index=outcomes, dtype=float)
            if overlap_total:
                means = common.groupby(strata, observed=True)[outcomes].mean()
                weights = counts.loc[counts.common_support, "common_weight"].reindex(means.index)
                if not np.isclose(weights.sum(), 1):
                    raise AssertionError("Both contexts must receive identical normalized cell weights")
                standardized = means.mul(weights, axis=0).sum()
            summary.update({prefix + "standardized_distant_gain": float(standardized[GAIN]),
                            prefix + "standardized_total_gain": float(standardized[TOTAL]),
                            prefix + "standardized_excess_gain": float(standardized[EXCESS]),
                            prefix + "standardized_retention": ratio(standardized[HITS], standardized[BASE])})
        for metric in ("distant_gain", "total_gain", "excess_gain"):
            for kind in ("raw", "standardized"):
                summary[f"{kind}_{metric}_concentrated_minus_diversified"] = (
                    summary[f"concentrated_{kind}_{metric}"] - summary[f"diversified_{kind}_{metric}"])
        summary_rows.append(summary)
    return pd.DataFrame(summary_rows), pd.DataFrame(cell_rows)


def validate(paired, development, grouping):
    required = {"organization_id", "year", "model", "k", "policy", "context",
                "pool_n", "distant_pool_n", "distant_selected", "distant_selected_topk",
                GAIN, TOTAL, HITS, BASE, EXCESS}
    missing = required - set(paired)
    if missing:
        raise ValueError(f"Paired diagnostics missing {sorted(missing)}")
    if paired.empty or development.empty:
        raise ValueError("Both held-out paired decisions and development decisions are required")
    if not set(paired.context.unique()).issubset(CONTEXTS):
        raise ValueError("Context must be concentrated or diversified; missing context is not a category")
    keys = ["organization_id", "year", *grouping, "policy"]
    if paired.duplicated(keys).any():
        raise ValueError("Duplicate paired decision keys")
    for name, data in (("paired", paired), ("development", development)):
        for col in ("pool_n", "distant_pool_n", "k"):
            if not np.isfinite(data[col].to_numpy(dtype=float)).all():
                raise ValueError(f"Nonfinite {name} {col}")
        if ((data.pool_n <= 0) | (data.distant_pool_n < 0) |
                (data.distant_pool_n > data.pool_n) | (data.k > data.pool_n)).any():
            raise ValueError(f"Invalid {name} candidate supply")
    for col in (GAIN, TOTAL, HITS, BASE):
        if not np.isfinite(paired[col].to_numpy(dtype=float)).all():
            raise ValueError(f"Nonfinite paired endpoint {col}")
    if (paired[[HITS, BASE]] < 0).any().any():
        raise ValueError("Negative high-attention counts")
    if not np.allclose(paired[TOTAL], paired[HITS] - paired[BASE]):
        raise ValueError("Supplied paired total difference disagrees with its source counts")
    if paired.organization_id.isna().any():
        raise ValueError("Missing organization identifier")
    if paired.year.min() <= development.year.max():
        raise ValueError("Development and held-out years overlap")


def run_analysis(run, output=None, development_end=2015, repeats=1000, seed=SEED):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    run = Path(run).resolve()
    output = Path(output).resolve() if output else run / "context_and_uncertainty"
    if os.name == "nt" and output.drive.upper() != "D:":
        raise ValueError("Working outputs must stay on the configured D: research drive")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use a fresh output directory; existing diagnostics are not overwritten")
    paired = pd.read_parquet(run / "paired_decision_diagnostics.parquet")
    all_results = pd.read_parquet(run / "all_policy_results.parquet")
    development = all_results.loc[all_results.year <= development_end].copy()
    grouping = ["model", "k"]
    if "distance_definition" in paired:
        if "distance_definition" not in development:
            raise ValueError("Development data lack held-out distance definition")
        grouping.append("distance_definition")
    validate(paired, development, grouping)
    paired = paired.copy()
    paired["far_pool_fraction"] = paired.distant_pool_n / paired.pool_n
    paired["budget_fraction"] = paired.k / paired.pool_n
    empty_far = paired.distant_pool_n.eq(0)
    if (paired.loc[empty_far, [GAIN, "distant_selected", "distant_selected_topk"]] != 0).any().any():
        raise ValueError("A zero-sized distant pool cannot supply distant selections or gains")
    corrected = int((empty_far & paired[EXCESS].isna()).sum())
    # Purely algebraic diagnostic convention, in memory only; primary endpoints stay unchanged.
    paired.loc[empty_far, EXCESS] = 0.
    if not np.isfinite(paired[EXCESS].to_numpy(dtype=float)).all():
        raise ValueError("Unexplained missing excess gain in a nonempty distant pool")
    cuts = derive_cutpoints(development, grouping)
    comparison, cells = context_standardization(paired, cuts, grouping)
    interval_rows = []
    for key, group in paired.groupby([*grouping, "policy"], sort=True, dropna=False):
        identity = dict(zip([*grouping, "policy"], key))
        scopes = [("all", group)] + [(context, group.loc[group.context.eq(context)]) for context in CONTEXTS]
        for scope, subset in scopes:
            if subset.empty:
                continue
            interval_rows.append({**identity, "scope": scope,
                                  **joint_bootstrap(subset, repeats, group_seed([*key, scope], seed))})
    notes = {
        "source_run": str(run), "input_paired_rows": len(paired),
        "development_end_requested": development_end,
        "development_years_observed": sorted(map(int, development.year.unique())),
        "heldout_years_observed": sorted(map(int, paired.year.unique())),
        "synthetic_software_test": "SYNTHETIC" in str(run).upper() or "SOFTWARE_TEST" in str(run).upper(),
        "seed": seed, "bootstrap_repeats": repeats,
        "cutpoints": "Development-only median distant-pool share and K/pool size, deduplicated by organization, year, model, K and distance; separate cutpoints per model/K/distance. Equality is high.",
        "standardization": "Secondary descriptive comparison. Cells are year x far-supply bin x budget-fraction bin. Only cells containing both contexts contribute. Both contexts use weights proportional to the smaller context count in each cell. Raw primary results and their sample are not changed.",
        "no_support": "No common support yields missing standardized effects, not extrapolation. Support counts and fractions are reported.",
        "joint_resampling": "Identical sampled organization indices jointly generate distant-gain means and ratio-of-sums total-hit retention. Intervals are pointwise marginal 2.5/97.5 percentiles, not a joint confidence region.",
        "uncertainty_scope": "Fixed historical corpus and years. Organization exchangeability is an additional assumption; shared candidates and year shocks are not solved by this resampling. No future-environment coverage or causal claim is made.",
        "small_clusters": "Fewer than five organizations: no intervals. Five to nine: caution flag. These are reporting safeguards, not sufficient conditions for reliable inference.",
        "zero_denominator": "Observed zero baseline gives undefined retention. If any bootstrap replicate has a zero baseline denominator, retention interval is suppressed rather than conditioning on nonzero draws.",
        "zero_far_pool_excess_diagnostic_convention_rows": corrected,
        "zero_far_pool_note": "With zero distant supply, selections and distant gains must be zero; the excess diagnostic is algebraically zero. Only the in-memory secondary diagnostic is completed; input files are untouched.",
        "retention_interpretation": "A development retention target is not a held-out guarantee. No tolerance threshold is justified by these intervals.",
        "random_policies": "Random-seed policy labels remain separate; no seed is treated as an independent organization.",
    }
    output.mkdir(parents=True, exist_ok=True)
    cuts.to_csv(output / "development_supply_cutpoints.csv", index=False)
    comparison.to_csv(output / "context_standardized_comparison.csv", index=False)
    cells.to_csv(output / "context_common_support_cells.csv", index=False)
    pd.DataFrame(interval_rows).to_csv(output / "joint_endpoint_intervals.csv", index=False)
    (output / "context_and_uncertainty_notes.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"event": "context_and_uncertainty_saved", "output": str(output),
                      "paired_rows": len(paired), "comparison_rows": len(comparison),
                      "interval_rows": len(interval_rows), "synthetic_software_test": notes["synthetic_software_test"]}))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--development-end", type=int, default=2015)
    parser.add_argument("--repeats", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    run_analysis(args.run, args.output, args.development_end, args.repeats, args.seed)
