"""Transparent, paired decision diagnostics; no model or policy is retuned here."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def summarize(run: Path):
    data = pd.read_parquet(run / "heldout_policy_results.parquet")
    keys = ["organization_id", "year", "model", "k"]
    outcomes = ["high_attention_hits", "distant_high_attention_hits", "distant_selected", "future_attention_sum"]
    baseline = data.loc[data.policy.eq("topk"), keys + outcomes]
    paired = data.merge(baseline, on=keys, suffixes=("", "_topk"), validate="many_to_one")
    for outcome in outcomes:
        paired["delta_"+outcome] = paired[outcome] - paired[outcome+"_topk"]
    paired["distant_opportunity_rate"] = np.where(paired.distant_pool_n > 0,
        paired.pool_distant_high_attention / paired.distant_pool_n, np.nan)
    paired["excess_distant_gain"] = paired.delta_distant_high_attention_hits - (
        paired.delta_distant_selected * paired.distant_opportunity_rate)
    paired.loc[paired.distant_pool_n.eq(0),"excess_distant_gain"] = 0.
    paired["far_pool_fraction"] = paired.distant_pool_n / paired.pool_n
    paired["quota_requested"] = np.floor(paired.k * paired.share + .5)
    paired["quota_feasible"] = paired.distant_pool_n >= paired.quota_requested
    paired["quota_binding"] = paired.distant_selected_topk < paired.quota_requested
    for outcome,col in [("high_attention_hits","delta_high"),("distant_high_attention_hits","delta_distant_high")]:
        if "core_"+col in paired:
            if not np.allclose(paired["core_"+col]+paired["related_"+col],paired["delta_"+outcome]):
                raise AssertionError("Core/related changes must add exactly to the paired result")
    # This is an ex-post diagnostic, never an input to policy selection.
    paired.to_parquet(run / "paired_decision_diagnostics.parquet", index=False)
    groupings = [["model", "k", "policy"], ["context", "model", "k", "policy"],
                 ["year", "model", "k", "policy"]]
    for groups, name in zip(groupings, ["frontier", "context_frontier", "annual_frontier"]):
        rows = []
        for values, group in paired.groupby(groups, dropna=False):
            total_base = group.high_attention_hits_topk.sum()
            loss = group.delta_high_attention_hits < 0
            row = dict(zip(groups, values))
            row.update(n_decisions=len(group), n_organizations=group.organization_id.nunique(),
                mean_total_hits=group.high_attention_hits.mean(),
                mean_distant_hits=group.distant_high_attention_hits.mean(),
                mean_total_gain=group.delta_high_attention_hits.mean(),
                mean_distant_gain=group.delta_distant_high_attention_hits.mean(),
                pooled_total_retention=group.high_attention_hits.sum()/total_base if total_base else np.nan,
                baseline_zero_share=group.high_attention_hits_topk.eq(0).mean(),
                mean_excess_distant_gain=group.excess_distant_gain.mean(),
                share_decisions_losing_total_hits=loss.mean(),
                share_decisions_gaining_distant_hits=(group.delta_distant_high_attention_hits > 0).mean(),
                mean_distant_pool_n=group.distant_pool_n.mean(),
                mean_distant_opportunity_rate=group.distant_opportunity_rate.mean())
            policy=str(row["policy"])
            row["retention_target"]=float(policy.rsplit("_",1)[-1]) if policy.startswith("context_rule_retention_") else np.nan
            row["realized_constraint_met"]=(row["pooled_total_retention"]>=row["retention_target"]) if np.isfinite(row["retention_target"]) and np.isfinite(row["pooled_total_retention"]) else np.nan
            rows.append(row)
        pd.DataFrame(rows).to_csv(run / f"{name}.csv", index=False)
    loo = []
    for omitted_year in sorted(paired.year.unique()):
        for (model, k, policy), group in paired.loc[paired.year.ne(omitted_year)].groupby(["model", "k", "policy"]):
            base = group.high_attention_hits_topk.sum()
            loo.append(dict(omitted_year=int(omitted_year),model=model,k=k,policy=policy,
                n_decisions=len(group),mean_total_gain=group.delta_high_attention_hits.mean(),
                mean_distant_gain=group.delta_distant_high_attention_hits.mean(),
                pooled_total_retention=group.high_attention_hits.sum()/base if base else np.nan))
    pd.DataFrame(loo).to_csv(run / "leave_one_year_out.csv", index=False)
    change_files=sorted(run.glob("changed_selections_*.parquet"))
    if change_files:
        changes=pd.concat([pd.read_parquet(path) for path in change_files],ignore_index=True)
        changes=changes.loc[changes.year.isin(paired.year.unique())]
        reuse=[]
        for (year,k,policy),group in changes.groupby(["year","k","policy"]):
            frequencies=group.groupby("patent_id").organization_id.nunique()
            denominator=paired.loc[paired.year.eq(year)&paired.k.eq(k)&paired.model.eq("boosting")&paired.policy.eq(policy),"organization_id"].nunique()
            reuse.append(dict(year=year,k=k,policy=policy,n_changed_patents=len(frequencies),
                n_change_events=len(group),n_organizations=denominator,
                maximum_changed_patent_organization_fraction=frequencies.max()/denominator if denominator else np.nan,
                top_ten_changed_patents_event_share=frequencies.nlargest(10).sum()/len(group)))
        pd.DataFrame(reuse).to_csv(run/"changed_candidate_reuse.csv",index=False)
    if "core_delta_high" in paired:
        paired.groupby(["model","k","policy"],as_index=False)[["core_added","core_removed","core_delta_high",
            "core_delta_distant_high","related_added","related_removed","related_delta_high","related_delta_distant_high"]].mean().to_csv(run/"domain_change_decomposition.csv",index=False)
    decisions = data.loc[(data.model.eq("boosting")) & data.policy.eq("topk")].drop_duplicates(["organization_id", "year"])
    decisions[["organization_id","year","history_n","concentration","context","pool_n", "distant_pool_n",
        "pool_high_attention","pool_distant_high_attention","history_classification_coverage"]].to_csv(run / "decision_sample.csv",index=False)
    (run / "diagnostic_notes.json").write_text(json.dumps({
        "excess_distant_gain":"Observed paired distant-hit gain minus additional distant slots times the realized distant-pool high-attention rate; ex-post diagnostic, not a causal or model-free success criterion.",
        "retention":"Ratio of pooled policy hits to pooled baseline hits. Undefined if baseline sum is zero. A development retention constraint is not a held-out guarantee.",
        "uncertainty":"Organization-resampling intervals condition on the historical years and candidate corpus; shared candidates and four evaluation years limit generalization. Annual and leave-one-year-out results show historical sensitivity, not a four-cluster population confidence interval.",
        "all_candidates_shared":"Every policy within an organization-year has identical candidate availability and classification/relevance restrictions. Across organizations the opportunity sets differ."
    }, indent=2), encoding="utf-8")
    print(json.dumps({"event":"tradeoff_diagnostics_saved","run":str(run),"paired_rows":len(paired),
                      "decision_units":len(decisions)},ensure_ascii=False))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--run",type=Path,required=True)
    summarize(parser.parse_args().run)
