"""Temporal patent-intelligence policy evaluation on an acquired real corpus.

Input contract is documented in --help. Derived data and all outputs stay on D.
The model learns only from fully matured labels at each decision origin.
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score, ndcg_score, brier_score_loss
from sklearn.preprocessing import normalize
from lightgbm import LGBMClassifier

from policy_core import quota_select, mmr_select, portfolio_metrics, fit_allocation_rule, cluster_bootstrap_difference

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260929


def emit(event, **kw):
    print(json.dumps({"time": dt.datetime.now(dt.timezone.utc).isoformat(), "event": event, **kw}, ensure_ascii=False), flush=True)


def code_set(value):
    return {x.strip() for x in str(value).split("|") if x.strip() and x.strip() != "nan"}


def normalized_subclass(value):
    return {x[:4] for x in code_set(value) if len(x) >= 4}


def load_data(path, require_labels=True, high_threshold=2):
    frame = pd.read_parquet(path)
    required = {"patent_id", "patent_date", "patent_title", "assignee_id", "cpc_codes", "is_core", "future_external_attention"}
    if require_labels:
        required.add("early_external_attention")
    if not require_labels:
        required.remove("future_external_attention")
        if "future_external_attention" not in frame:
            frame["future_external_attention"] = np.nan
    if not required.issubset(frame):
        raise ValueError(f"Input requires {sorted(required)}; missing {sorted(required-set(frame))}")
    frame["patent_id"] = frame["patent_id"].astype(str)
    if frame["patent_id"].duplicated().any():
        raise ValueError("Input must have one row per patent_id; resolve assignee and CPC lists before analysis")
    frame["patent_date"] = pd.to_datetime(frame["patent_date"], errors="raise")
    frame["year"] = frame["patent_date"].dt.year
    frame["assignee_id"] = frame["assignee_id"].fillna("").astype(str)
    # Canonical assignee_id is a pipe-delimited set of all documented owners,
    # never only the first listed assignee.
    frame["owners"] = frame["assignee_id"].map(code_set)
    frame["is_core"] = frame.get("is_core", pd.Series(False, index=frame.index)).fillna(False).astype(bool)
    frame["cpc_codes"] = frame["cpc_codes"].fillna("").astype(str)
    frame["future_external_attention"] = pd.to_numeric(frame["future_external_attention"], errors="raise")
    if (frame["future_external_attention"].dropna() < 0).any():
        raise ValueError("Future attention cannot be negative")
    abstract = frame.get("patent_abstract", pd.Series("", index=frame.index)).fillna("")
    frame["text"] = frame["patent_title"].fillna("") + ". " + abstract
    frame["subclasses"] = frame["cpc_codes"].map(normalized_subclass)
    frame["num_claims"] = pd.to_numeric(frame.get("num_claims", pd.Series(0, index=frame.index)), errors="coerce").fillna(0)
    frame["early_external_attention"] = pd.to_numeric(frame.get("early_external_attention", pd.Series(0, index=frame.index)), errors="coerce").fillna(0)
    # Stable primary event: reach at least two distinct external organizations.
    # A cohort-quantile sensitivity is retained separately because integer citation
    # ties can make an upper-decile cutoff select a much larger share.
    frame["high_attention"] = False
    for year, ix in frame.groupby("year").groups.items():
        values = frame.loc[ix, "future_external_attention"].dropna()
        if len(values):
            threshold = float(high_threshold) if high_threshold else max(1., float(values.quantile(.9)))
            frame.loc[ix, "high_attention"] = frame.loc[ix, "future_external_attention"] >= threshold
    return frame.sort_values(["year", "patent_id"]).reset_index(drop=True)


def numeric_features(frame):
    return np.column_stack([
        np.log1p(frame["text"].str.len().to_numpy()),
        frame["patent_date"].dt.month.to_numpy() / 12.,
        np.log1p(frame["early_external_attention"].to_numpy()),
        frame["subclasses"].map(len).to_numpy(),
    ]).astype(np.float32)


def score_year(frame, year, output, max_features=20000, portfolios=None):
    train = frame.loc[(frame["year"] <= year-3) & (frame["year"] >= 2010)].copy()
    if train["future_external_attention"].isna().any():
        raise ValueError("Mature training labels are missing; resolve source coverage instead of dropping them silently")
    profile_source = frame if portfolios is None else portfolios
    history = profile_source.loc[(profile_source["year"] >= year-5) & (profile_source["year"] < year)].copy()
    current = frame.loc[frame["year"] == year].copy()
    if current["future_external_attention"].isna().any():
        raise ValueError("A complete outcome window is required for every candidate in an evaluated cohort")
    visible = pd.concat([history,current],ignore_index=True)
    if len(train) < 100 or len(current) < 50:
        emit("skip_year_insufficient_training", year=year, n_train=len(train), n_current=len(current))
        return None
    start = time.time()
    vectorizer = TfidfVectorizer(max_features=max_features, min_df=2, max_df=.98,
        ngram_range=(1,2), stop_words="english", dtype=np.float32, sublinear_tf=True)
    x_train = vectorizer.fit_transform(train["text"])
    current_mask = (visible["year"] == year).to_numpy()
    x_current = vectorizer.transform(current["text"])
    # Portfolios outside the domain have titles but not always abstracts.
    # Use the same title-only representation for both sides of every distance
    # and diversity comparison; abstracts remain prediction features only.
    title_vectorizer = TfidfVectorizer(max_features=max_features, min_df=2, max_df=.98,
        ngram_range=(1,2), stop_words="english", dtype=np.float32, sublinear_tf=True)
    title_vectorizer.fit(train["patent_title"].fillna(""))
    x_title_visible = title_vectorizer.transform(visible["patent_title"].fillna(""))
    x_title_current = x_title_visible[current_mask]
    numeric_train, numeric_current = numeric_features(train), numeric_features(current)
    y_train = train["future_external_attention"].to_numpy(dtype=float)
    ridge = Ridge(alpha=20., solver="lsqr", max_iter=1000)
    ridge.fit(sparse.hstack([x_train, sparse.csr_matrix(numeric_train)], format="csr"), np.log1p(y_train))
    ridge_score = ridge.predict(sparse.hstack([x_current, sparse.csr_matrix(numeric_current)], format="csr"))
    dims = min(48, x_train.shape[1]-1, x_train.shape[0]-1)
    svd = TruncatedSVD(n_components=dims, random_state=SEED, n_iter=5)
    z_train = svd.fit_transform(x_train)
    z_current = svd.transform(x_current)
    # Primary predictor targets the same high-attention event used in the
    # decision objective. Ridge remains a distinct continuous-attention baseline.
    boosting = LGBMClassifier(objective="binary", n_estimators=180, learning_rate=.04,
        num_leaves=15, min_child_samples=30, reg_lambda=2., subsample=1.,
        colsample_bytree=1., random_state=SEED, n_jobs=2, verbosity=-1)
    if train["high_attention"].nunique() < 2:
        raise ValueError("Training cohort has fewer than two outcome classes")
    boosting.fit(np.column_stack([z_train, numeric_train]), train["high_attention"].astype(int))
    boosting_score = boosting.predict_proba(np.column_stack([z_current, numeric_current]))[:,1]
    current["score_ridge"] = ridge_score
    current["score_boosting"] = boosting_score
    current["score_popularity"] = current["early_external_attention"]
    metrics = []
    truth = current["future_external_attention"].to_numpy()
    valid = np.isfinite(truth)
    for model, scores in [("ridge", ridge_score), ("boosting", boosting_score), ("popularity", current["score_popularity"].to_numpy())]:
        y, s = truth[valid], scores[valid]
        high = current.loc[valid, "high_attention"].to_numpy()
        metrics.append({"year":year,"model":model,"n_train":len(train),"n_test":int(valid.sum()),
            "last_training_cohort":int(train["year"].max()), "last_label_year":int(train["year"].max()+3),
            "average_precision":float(average_precision_score(high,s)) if high.any() else np.nan,
            "brier_score":float(brier_score_loss(high,s)) if model == "boosting" else np.nan,
            "constant_historical_prevalence_brier":float(brier_score_loss(high,np.full(len(high),train["high_attention"].mean()))),
            "training_high_prevalence":float(train["high_attention"].mean()),
            "test_high_prevalence":float(high.mean()),
            "ndcg_at_50":float(ndcg_score(y[None,:],s[None,:],k=50)) if y.sum() else np.nan})
    if train["year"].max()+3 > year:
        raise AssertionError("Unmatured labels entered the training set")
    current.drop(columns=["subclasses", "owners", "text"]).to_parquet(output/f"scores_{year}.parquet",index=False)
    (output/f"vocabulary_audit_{year}.json").write_text(json.dumps({
        "year":year,"n_train":len(train),"latest_training_grant_year":int(train["year"].max()),
        "latest_training_label_year":int(train["year"].max()+3),"vocabulary_size":len(vectorizer.vocabulary_),
        "distance_vocabulary_size":len(title_vectorizer.vocabulary_),
        "distance_representation":"title_only_for_both_portfolios_and_candidates",
        "n_visible":len(visible),"n_candidate":len(current),"fit_seconds":round(time.time()-start,2)},indent=2),encoding="utf-8")
    emit("year_models_fitted",year=year,n_train=len(train),n_candidates=len(current),seconds=round(time.time()-start,1))
    return visible, current, x_title_visible, x_title_current, metrics


def evaluate_year(scored, year, args):
    visible, current, x_visible, x_current, model_metrics = scored
    history_mask = (visible["year"] < year).to_numpy()
    history = visible.loc[history_mask]
    x_history = x_visible[history_mask]
    memberships = history[["patent_id","owners","is_core"]].explode("owners").dropna(subset=["owners"])
    counts = memberships.groupby("owners")["patent_id"].nunique()
    core_counts = memberships.loc[memberships["is_core"]].groupby("owners")["patent_id"].nunique()
    eligible = counts.loc[(counts >= args.min_history) & (core_counts.reindex(counts.index,fill_value=0) >= args.min_core_history)].sort_values(ascending=False)
    if args.max_organizations:
        # A bounded pilot uses only contemporaneous history; never future performance.
        eligible = eligible.head(args.max_organizations)
    rows, sample_lists, changed_selections, selected_primary = [], [], [], []
    ids = current["patent_id"].to_numpy()
    owner_sets = current["owners"].tolist()
    current_subclasses = current["subclasses"].tolist()
    shares = [0., .1, .2, .3, .4]
    for organization_id in eligible.index:
        member = history["owners"].map(lambda owners: organization_id in owners).to_numpy()
        classified_history = history.loc[member,"subclasses"].map(bool)
        classification_coverage = float(classified_history.mean())
        if classification_coverage < args.min_classification_coverage:
            continue
        centroid = sparse.csr_matrix(np.asarray(x_history[member].mean(axis=0)))
        centroid = normalize(centroid)
        similarity = (x_current @ centroid.T).toarray().ravel()
        # Absolute semantic floor is deliberately held common across all policies.
        externally_owned = np.asarray([organization_id not in owners for owners in owner_sets])
        classified_candidate = np.asarray([bool(codes) for codes in current_subclasses])
        pool = np.flatnonzero((similarity >= args.relevance_floor) & externally_owned & classified_candidate)
        if len(pool) < max(args.capacities):
            continue
        historical_codes = set().union(*history.loc[member,"subclasses"].tolist())
        topic_counts = {}
        for values in history.loc[member,"subclasses"]:
            for code in values:
                topic_counts[code] = topic_counts.get(code, 0) + 1 / max(len(values),1)
        weights = np.asarray(list(topic_counts.values()),dtype=float)
        concentration = float(np.sum((weights/weights.sum())**2)) if len(weights) else np.nan
        far_unseen = np.asarray([bool(current_subclasses[i]) and not bool(current_subclasses[i] & historical_codes) for i in pool])
        # Relative text distance is separate from unseen classification and is reported as such.
        threshold = float(np.quantile(similarity[pool], .25))
        far_text = similarity[pool] <= threshold
        far = far_text if args.distance == "text_quartile" else far_unseen
        attention = current.iloc[pool]["future_external_attention"].to_numpy()
        high = current.iloc[pool]["high_attention"].to_numpy()
        core = current.iloc[pool]["is_core"].to_numpy()
        codes = current.iloc[pool]["cpc_codes"].to_numpy()
        common = {"organization_id":str(organization_id),"year":year,
                  "history_n":int(member.sum()),"concentration":concentration,"pool_n":len(pool),
                  "history_classification_coverage":classification_coverage,
                  "distant_pool_n":int(far.sum()),"distance_definition":args.distance,
                  "pool_high_attention":int(high.sum()),"pool_distant_high_attention":int((high & far).sum())}
        models = {"ridge":current.iloc[pool]["score_ridge"].to_numpy(),
                  "boosting":current.iloc[pool]["score_boosting"].to_numpy(),
                  "popularity":current.iloc[pool]["score_popularity"].to_numpy(),
                  "similarity":similarity[pool]}
        models = {name:score for name,score in models.items() if name in args.models}
        for model, scores in models.items():
            # MMR is a greedy nested ranking: shorter lists are exact prefixes.
            mmr_rankings = {weight:mmr_select(scores,ids[pool],x_current[pool],max(args.capacities),weight)
                            for weight in [.5,.7,.9]}
            for k in args.capacities:
                policies = [("topk",0.,quota_select(scores,ids[pool],far,k,0.))]
                for share in shares[1:]:
                    policies.append((f"quota_{share:.1f}",share,quota_select(scores,ids[pool],far,k,share)))
                    for seed in range(args.random_repeats):
                        policies.append((f"random_{share:.1f}_s{seed}",share,
                            quota_select(scores,ids[pool],far,k,share,random_seed=SEED+seed)))
                for weight in [.5,.7,.9]:
                    policies.append((f"mmr_{weight:.1f}",np.nan,
                        mmr_rankings[weight][:k]))
                baseline_set = set(policies[0][2].tolist())
                for policy, share, chosen in policies:
                    row = {**common,"model":model,"k":k,"policy":policy,"share":share,
                           **portfolio_metrics(chosen,attention,high,far,codes)}
                    row["mean_similarity"] = float(similarity[pool[chosen]].mean())
                    row["distant_signal_recall"] = row["distant_high_attention_hits"] / common["pool_distant_high_attention"] if common["pool_distant_high_attention"] else np.nan
                    row["total_signal_recall"] = row["high_attention_hits"] / common["pool_high_attention"] if common["pool_high_attention"] else np.nan
                    selected_set = set(chosen.tolist())
                    added = np.asarray(sorted(selected_set-baseline_set),dtype=int)
                    removed = np.asarray(sorted(baseline_set-selected_set),dtype=int)
                    for domain,mask in [("core",core),("related",~core)]:
                        a,r = added[mask[added]],removed[mask[removed]]
                        row[domain+"_added"] = len(a)
                        row[domain+"_removed"] = len(r)
                        row[domain+"_delta_high"] = int(high[a].sum()-high[r].sum())
                        row[domain+"_delta_distant_high"] = int((high[a]&far[a]).sum()-(high[r]&far[r]).sum())
                    if model == "boosting" and not policy.startswith("random_"):
                        for j in chosen:
                            selected_primary.append({"organization_id":str(organization_id),"year":year,
                                "k":k,"policy":policy,"patent_id":str(ids[pool[j]]),
                                "distant":bool(far[j]),"is_core":bool(core[j])})
                        for operation,changed in [("added",added),("removed",removed)]:
                            for j in changed:
                                changed_selections.append({"organization_id":str(organization_id),"year":year,
                                    "model":model,"k":k,"policy":policy,"operation":operation,
                                    "patent_id":str(ids[pool[j]]),"is_core":bool(core[j]),
                                    "high_attention":bool(high[j]),"distant":bool(far[j])})
                    rows.append(row)
                    if model == "boosting" and k == args.capacities[0] and policy in {"topk","quota_0.3","mmr_0.7"}:
                        for rank,j in enumerate(chosen,1):
                            sample_lists.append({"organization_id":str(organization_id),"year":year,"policy":policy,
                                "rank":rank,"patent_id":str(ids[pool[j]]),"score":float(scores[j]),
                                "similarity":float(similarity[pool[j]]),"distant":bool(far[j]),
                                "future_attention":float(attention[j]),"title":str(current.iloc[pool[j]]["patent_title"])})
    emit("year_policy_evaluation",year=year,organizations=len({x["organization_id"] for x in rows}),rows=len(rows))
    if selected_primary:
        pd.DataFrame(selected_primary).to_parquet(args.output/f"selected_primary_{year}.parquet",index=False)
    return pd.DataFrame(rows), pd.DataFrame(sample_lists), pd.DataFrame(model_metrics),pd.DataFrame(changed_selections)


def summarize(results, out, development_end):
    dev = results.loc[results["year"] <= development_end].copy()
    # Allocation learning consumes outcomes too. A three-year embargo is just
    # as necessary here as it is for the predictor's training labels.
    test_start = development_end + 3
    holdout = results.loc[results["year"] >= test_start].copy()
    if len(dev) == 0 or len(holdout) == 0:
        emit("no_final_rule_evaluation",reason="both development and holdout years required")
        return
    threshold = float(dev.drop_duplicates(["organization_id","year"])["concentration"].median())
    if not np.isfinite(threshold) or results["concentration"].isna().any():
        raise ValueError("Missing knowledge concentration cannot be coded as diversified")
    results["context"] = np.where(results["concentration"] >= threshold,"concentrated","diversified")
    dev = results.loc[results["year"] <= development_end].copy()
    holdout = results.loc[results["year"] >= test_start].copy()
    rule_rows, chosen_rows = [], []
    for model in sorted(results["model"].unique()):
        policy_subset = dev.loc[(dev["model"]==model) & (dev["policy"].eq("topk") | dev["policy"].str.startswith("quota_"))]
        for retention in [.9,1.]:
            rule = fit_allocation_rule(policy_subset,retention)
            rule["model"] = model
            rule_rows.append(rule)
            lookup = {(r["context"],r["k"]):r["share"] for r in rule.to_dict("records")}
            base_decisions = holdout.loc[(holdout["model"]==model)&holdout["policy"].eq("topk")]
            for (context,k),base_group in base_decisions.groupby(["context","k"]):
                fallback = (context,k) not in lookup
                share = lookup.get((context,k),0.)
                policy = "topk" if share == 0 else f"quota_{share:.1f}"
                picked = holdout.loc[(holdout["model"]==model)&(holdout["context"]==context)
                                    &(holdout["k"]==k)&(holdout["policy"]==policy)].copy()
                expected_keys = set(map(tuple,base_group[["organization_id","year"]].to_numpy()))
                observed_keys = set(map(tuple,picked[["organization_id","year"]].to_numpy()))
                if expected_keys != observed_keys or len(picked) != len(base_group):
                    raise AssertionError("Context-rule and baseline decisions must be identical, including unseen-context fallback")
                picked["source_policy"] = policy
                picked["unseen_context_fallback"] = fallback
                picked["policy"] = f"context_rule_retention_{retention:.1f}"
                chosen_rows.append(picked)
    pd.concat(rule_rows,ignore_index=True).to_csv(out/"development_allocation_rules.csv",index=False)
    augmented = pd.concat([holdout,*chosen_rows],ignore_index=True)
    augmented.to_parquet(out/"heldout_policy_results.parquet",index=False)
    (out/"context_rule_audit.json").write_text(json.dumps({"development_end":development_end,
        "concentration_threshold":threshold,"test_start_after_label_maturity":test_start,
        "test_years":sorted(holdout["year"].unique().tolist()),
        "threshold_derived_from":"development decisions only"},indent=2),encoding="utf-8")
    summary = augmented.groupby(["model","k","policy"],as_index=False).agg(
        n_decisions=("organization_id","size"),n_organizations=("organization_id","nunique"),
        high_attention_hits=("high_attention_hits","mean"),distant_high_attention_hits=("distant_high_attention_hits","mean"),
        future_attention_sum=("future_attention_sum","mean"),distant_selected=("distant_selected","mean"))
    summary.to_csv(out/"heldout_summary.csv",index=False)
    annual = augmented.groupby(["year","model","k","policy"],as_index=False).agg(
        n_decisions=("organization_id","size"),high_attention_hits=("high_attention_hits","mean"),
        distant_high_attention_hits=("distant_high_attention_hits","mean"),future_attention_sum=("future_attention_sum","mean"))
    annual.to_csv(out/"heldout_annual_summary.csv",index=False)
    estimates=[]
    for (model,k),group in augmented.groupby(["model","k"]):
        for policy in ["quota_0.2","quota_0.3","mmr_0.7","context_rule_retention_0.9","context_rule_retention_1.0"]:
            for outcome in ["high_attention_hits","distant_high_attention_hits","future_attention_sum"]:
                estimates.append({"model":model,"k":int(k),"policy":policy,"outcome":outcome,
                    **cluster_bootstrap_difference(group,outcome,policy,repeats=1000)})
    pd.DataFrame(estimates).to_csv(out/"heldout_paired_effects.csv",index=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True,help="Parquet canonical patent table with fixed-window labels; see load_data required columns")
    parser.add_argument("--portfolios",type=Path,help="Optional canonical cross-domain historical portfolio table; the origin-specific core eligibility rule still applies")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--years",type=int,nargs="+",default=[2013,2014,2015,2018,2019,2020,2021])
    parser.add_argument("--development-end",type=int,default=2015)
    parser.add_argument("--capacities",type=int,nargs="+",default=[10,30,50])
    parser.add_argument("--min-history",type=int,default=15)
    parser.add_argument("--min-core-history",type=int,default=3)
    parser.add_argument("--min-classification-coverage",type=float,default=.8)
    parser.add_argument("--max-organizations",type=int,default=0,help="0 means all eligible; nonzero is a declared history-based pilot bound")
    parser.add_argument("--relevance-floor",type=float,default=.03)
    parser.add_argument("--distance",choices=["text_quartile","unseen_subclass"],default="unseen_subclass")
    parser.add_argument("--random-repeats",type=int,default=5)
    parser.add_argument("--max-features",type=int,default=20000)
    parser.add_argument("--high-threshold",type=int,default=2,help="Primary reach event: at least this many external organizations; 0 requests cohort upper-decile sensitivity")
    parser.add_argument("--models",nargs="+",choices=["ridge","boosting","popularity","similarity"],
                        default=["ridge","boosting","popularity","similarity"])
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Use a fresh versioned output folder to retain previous runs")
    args.output.mkdir(parents=True,exist_ok=True)
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}
    config["seed"]=SEED
    config["created_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
    config["software_note"]="Patent cohort labels become eligible only after the three-year window has matured. This run is not a human study."
    (args.output/"run_config.json").write_text(json.dumps(config,indent=2),encoding="utf-8")
    frame=load_data(args.input,high_threshold=args.high_threshold)
    portfolios=load_data(args.portfolios,require_labels=False) if args.portfolios else None
    emit("input_loaded",rows=len(frame),years=[int(frame.year.min()),int(frame.year.max())])
    all_results,all_examples,all_model_metrics=[],[],[]
    for year in args.years:
        scored=score_year(frame,year,args.output,args.max_features,portfolios=portfolios)
        if scored is None:continue
        result,examples,metrics,changes=evaluate_year(scored,year,args)
        if len(result):
            result.to_parquet(args.output/f"policy_results_{year}.parquet",index=False)
            if len(changes):changes.to_parquet(args.output/f"changed_selections_{year}.parquet",index=False)
            all_results.append(result);all_examples.append(examples);all_model_metrics.append(metrics)
    if not all_results:
        emit("no_evaluable_decisions");return
    combined=pd.concat(all_results,ignore_index=True)
    combined.to_parquet(args.output/"all_policy_results.parquet",index=False)
    pd.concat(all_examples,ignore_index=True).to_csv(args.output/"candidate_examples.csv",index=False)
    pd.concat(all_model_metrics,ignore_index=True).to_csv(args.output/"forecast_metrics.csv",index=False)
    summarize(combined,args.output,args.development_end)
    emit("complete",decisions=len(combined.drop_duplicates(["organization_id","year"])),policy_rows=len(combined))


if __name__=="__main__":
    main()
