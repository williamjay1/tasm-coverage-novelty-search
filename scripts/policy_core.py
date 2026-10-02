"""Capacity-constrained search policies. No outcome labels are used for selection."""
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.stats import rankdata


def stable_order(scores: np.ndarray, ids: np.ndarray) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError("Non-finite selection scores")
    return np.lexsort((np.asarray(ids, dtype=str), -scores))


def quota_select(scores, ids, distant, k, share, random_seed=None):
    """Minimum distant quota; remaining slots follow the common score ranking.

    This is a floor, not an exact cap: the score ranking can independently select
    further distant documents. A random seed randomizes quota slots only.
    """
    scores = np.asarray(scores, dtype=float)
    distant = np.asarray(distant, dtype=bool)
    k = min(int(k), len(scores))
    target = min(int(np.floor(k * float(share) + 0.5)), int(distant.sum()), k)
    ranking = stable_order(scores, ids)
    eligible = ranking[distant[ranking]]
    if random_seed is not None:
        eligible = np.random.default_rng(random_seed).permutation(eligible)
    selected = list(eligible[:target])
    used = set(selected)
    for j in ranking:
        if len(selected) == k:
            break
        if int(j) not in used:
            selected.append(int(j))
            used.add(int(j))
    return np.asarray(selected, dtype=int)


def mmr_select(scores, ids, normalized_vectors, k, weight=0.7):
    """Standard maximum marginal relevance using pairwise text cosine similarity.

    The input rows must have unit norm; scoring uses percentile ranks so MMR's
    weight is interpretable across different predictors. Ties follow patent ID.
    """
    n = len(scores)
    k = min(int(k), n)
    if n == 0 or k == 0:
        return np.array([], dtype=int)
    relevance = (rankdata(np.asarray(scores), method="average") - 1) / max(n - 1, 1)
    maximum_similarity = np.zeros(n, dtype=float)
    available = np.ones(n, dtype=bool)
    selected = []
    for _ in range(k):
        objective = weight * relevance - (1 - weight) * maximum_similarity
        objective[~available] = -np.inf
        # lexsort supports intentional -inf for excluded rows.
        j = int(np.lexsort((np.asarray(ids, dtype=str), -objective))[0])
        selected.append(j)
        available[j] = False
        product = normalized_vectors @ normalized_vectors[j].T
        similarity = product.toarray().ravel() if sparse.issparse(product) else np.asarray(product).ravel()
        maximum_similarity = np.maximum(maximum_similarity, similarity)
    return np.asarray(selected, dtype=int)


def portfolio_metrics(selected, future_attention, high_attention, distant, topic_codes=None):
    selected = np.asarray(selected, dtype=int)
    attention = np.asarray(future_attention, dtype=float)[selected]
    high = np.asarray(high_attention, dtype=bool)[selected]
    far = np.asarray(distant, dtype=bool)[selected]
    result = {
        "n_selected": int(len(selected)),
        "future_attention_sum": float(attention.sum()),
        "high_attention_hits": int(high.sum()),
        "distant_high_attention_hits": int((high & far).sum()),
        "distant_selected": int(far.sum()),
        "attention_positive_hits": int((attention > 0).sum()),
        "distant_attention_positive_hits": int(((attention > 0) & far).sum()),
    }
    if topic_codes is not None:
        all_codes = set()
        for i in selected:
            all_codes.update(str(topic_codes[i]).split("|"))
        all_codes.discard("")
        result["topic_coverage"] = len(all_codes)
    return result


def fit_allocation_rule(development_results, minimum_retention=0.9):
    """Choose a quota solely in development data, within context and capacity.

    Maximize distant high-attention hits subject to retaining a prespecified
    fraction of total high-attention hits of the score-only policy. The rule
    always contains a zero-share fallback. Ties choose the smaller quota.
    """
    import pandas as pd

    needed = {"context", "k", "share", "high_attention_hits", "distant_high_attention_hits"}
    missing = needed - set(development_results.columns)
    if missing:
        raise ValueError(f"Missing development columns: {sorted(missing)}")
    rows = []
    for (context, k), group in development_results.groupby(["context", "k"], observed=True):
        summary = group.groupby("share", as_index=False)[["high_attention_hits", "distant_high_attention_hits"]].sum()
        base = summary.loc[np.isclose(summary["share"], 0)]
        if len(base) != 1:
            raise ValueError("Each development context must include zero-share baseline")
        floor = float(base.iloc[0]["high_attention_hits"]) * minimum_retention
        feasible = summary.loc[summary["high_attention_hits"] >= floor].sort_values(
            ["distant_high_attention_hits", "high_attention_hits", "share"],
            ascending=[False, False, True],
        )
        best = feasible.iloc[0]
        rows.append({"context": str(context), "k": int(k), "share": float(best["share"]),
                     "minimum_retention": minimum_retention,
                     "development_total_hits": float(best["high_attention_hits"]),
                     "development_distant_hits": float(best["distant_high_attention_hits"])})
    return pd.DataFrame(rows)


def cluster_bootstrap_difference(frame, outcome, policy, baseline="topk", repeats=2000, seed=20260929):
    """Paired difference CI resampling organizations, not candidate patents."""
    import pandas as pd

    keys = ["organization_id", "year", "k", "model"]
    a = frame.loc[frame["policy"] == policy, keys + [outcome]]
    b = frame.loc[frame["policy"] == baseline, keys + [outcome]]
    paired = a.merge(b, on=keys, how="inner", validate="one_to_one", suffixes=("_policy", "_baseline"))
    paired["difference"] = paired[outcome + "_policy"] - paired[outcome + "_baseline"]
    if paired.empty:
        return {"n_organizations": 0, "n_decisions": 0, "mean_difference": None, "ci_low": None, "ci_high": None}
    by_org = paired.groupby("organization_id")["difference"].agg(["sum", "count"])
    if len(by_org) < 5:
        return {"n_organizations": int(len(by_org)), "n_decisions": int(len(paired)),
                "mean_difference": float(paired["difference"].mean()),
                "ci_low": None, "ci_high": None,
                "inference_note": "descriptive_only_fewer_than_five_organization_clusters"}
    rng = np.random.default_rng(seed)
    sums, counts = by_org["sum"].to_numpy(), by_org["count"].to_numpy()
    estimates = np.empty(repeats)
    for iteration in range(repeats):
        ix = rng.integers(0, len(by_org), size=len(by_org))
        estimates[iteration] = sums[ix].sum() / counts[ix].sum()
    return {"n_organizations": int(len(by_org)), "n_decisions": int(len(paired)),
            "mean_difference": float(paired["difference"].mean()),
            "ci_low": float(np.quantile(estimates, 0.025)),
            "ci_high": float(np.quantile(estimates, 0.975)),
            "inference_note": "few_clusters_interpret_cautiously" if len(by_org) < 10 else "organization_cluster_bootstrap"}
