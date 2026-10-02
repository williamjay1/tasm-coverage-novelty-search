"""Re-evaluate fixed primary-model lists under alternative citation measurements.

These are outcome-measurement sensitivities, not independently optimized systems.
The model, distances, lists and development-selected allocation rules stay fixed.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--patents",type=Path,required=True)
    args=parser.parse_args()
    run=args.run
    patents=pd.read_parquet(args.patents)
    patents["year"]=pd.to_datetime(patents.patent_date).dt.year
    patents["future_cohort_quantile"]=patents.future_external_attention
    outcomes=["future_external_attention","future_applicant_attention","future_disambig_attention","future_external_citing_patents","future_cohort_quantile"]
    coverage=[]
    for outcome in outcomes:
        patents[outcome+"_high"]=np.nan
        for year,group in patents.groupby("year"):
            known=group[outcome].notna()
            if not known.any():continue
            threshold=max(1.,float(group.loc[known,outcome].quantile(.9))) if outcome=="future_cohort_quantile" else 2.
            ix=group.loc[known].index
            patents.loc[ix,outcome+"_high"]=(group.loc[ix,outcome]>=threshold).astype(float)
            coverage.append(dict(outcome=outcome,year=year,n=len(group),known_n=int(known.sum()),
                threshold=threshold,positive_rate=float((group.loc[ix,outcome]>=threshold).mean())))
    pd.DataFrame(coverage).to_csv(run/"alternative_label_definitions.csv",index=False)
    audit=json.loads((run/"context_rule_audit.json").read_text())
    selections=pd.concat([pd.read_parquet(p) for p in sorted(run.glob("selected_primary_*.parquet"))],ignore_index=True)
    selections=selections.loc[selections.year>=audit["test_start_after_label_maturity"]]
    decision_context=pd.read_parquet(run/"heldout_policy_results.parquet")
    context=decision_context.loc[decision_context.model.eq("boosting")&decision_context.policy.eq("topk"),
        ["organization_id","year","k","context"]]
    selections=selections.merge(context,on=["organization_id","year","k"],validate="many_to_one")
    rules=pd.read_csv(run/"development_allocation_rules.csv")
    additions=[]
    for retention in [.9,1.]:
        local=rules.loc[rules.model.eq("boosting")&rules.minimum_retention.eq(retention),["context","k","share"]]
        chosen=selections.merge(local,on=["context","k"],how="left",validate="many_to_one")
        chosen["share"]=chosen.share.fillna(0.)
        chosen["desired_policy"]=chosen.share.map(lambda s:"topk" if s==0 else f"quota_{s:.1f}")
        chosen=chosen.loc[chosen.policy.eq(chosen.desired_policy)].copy()
        chosen["policy"]=f"context_rule_retention_{retention:.1f}"
        additions.append(chosen[selections.columns])
    selections=pd.concat([selections,*additions],ignore_index=True)
    selections=selections.merge(patents[["patent_id"]+[o+"_high" for o in outcomes]],on="patent_id",validate="many_to_one")
    rows=[]
    keys=["organization_id","year","k","policy"]
    for outcome in outcomes:
        h=outcome+"_high"
        temp=selections.assign(high=selections[h],distant_high=selections[h]*selections.distant)
        decisions=temp.groupby(keys,as_index=False).agg(hits=("high","sum"),distant_hits=("distant_high","sum"),
            unknown=(h,lambda x:int(x.isna().sum())),n_selected=("patent_id","size"))
        base=decisions.loc[decisions.policy.eq("topk"),["organization_id","year","k","hits","distant_hits","unknown"]]
        paired=decisions.merge(base,on=["organization_id","year","k"],suffixes=("","_topk"),validate="many_to_one")
        for (k,policy),g in paired.groupby(["k","policy"]):
            # Unknown resolved owners are not converted to zero. Mark comparisons
            # as incomplete and retain the missing-selection count explicitly.
            complete=g.unknown.eq(0)&g.unknown_topk.eq(0)
            observed=g.loc[complete]
            denominator=observed.hits_topk.sum()
            rows.append(dict(outcome=outcome,k=k,policy=policy,n_decisions=len(g),complete_decisions=len(observed),
                incomplete_decisions=int((~complete).sum()),
                mean_distant_gain=(observed.distant_hits-observed.distant_hits_topk).mean(),
                mean_total_gain=(observed.hits-observed.hits_topk).mean(),
                pooled_total_retention=observed.hits.sum()/denominator if denominator else np.nan))
    pd.DataFrame(rows).to_csv(run/"fixed_list_label_sensitivity.csv",index=False)
    (run/"label_sensitivity_notes.json").write_text(json.dumps({
        "scope":"Fixed-list outcome sensitivity; no retraining or quota reselection.",
        "resolved_owner_missing":"Pairs with any missing disambiguated-outcome selected record are incomplete for this sensitivity; their number is reported. Do not treat a changed subset as an identical sample.",
        "thresholds":"Primary and alternative count measurements require at least two observed units. The separately labelled cohort-quantile sensitivity uses max(1,90th percentile) with ties; actual rates are reported.",
        "owner_interpretation":"External is relative to the cited patent's owners. A focal searching organization may itself later cite a selected patent; this label does not exclude it."
    },indent=2),encoding="utf-8")
    print(json.dumps({"event":"fixed_list_label_sensitivity_complete","rows":len(rows)}))

if __name__=="__main__":main()
