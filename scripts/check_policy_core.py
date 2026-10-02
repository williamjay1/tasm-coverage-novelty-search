"""Small deterministic checks for selection leakage, capacity and paired inference.

Arrays here are synthetic software fixtures, never empirical paper evidence.
"""
import numpy as np
import pandas as pd
from scipy import sparse
from policy_core import quota_select, mmr_select, portfolio_metrics, fit_allocation_rule, cluster_bootstrap_difference

scores = np.array([.9, .8, .7, .6, .5, .4])
ids = np.array(["a", "b", "c", "d", "e", "f"])
distant = np.array([False, False, False, True, True, True])
assert quota_select(scores, ids, distant, 4, .5).tolist() == [3, 4, 0, 1]
assert quota_select(scores, ids, distant, 4, 0).tolist() == [0, 1, 2, 3]
assert len(set(quota_select(scores, ids, distant, 10, .8))) == 6
assert np.array_equal(quota_select(scores, ids, distant, 3, .5, 7), quota_select(scores, ids, distant, 3, .5, 7))

vectors = sparse.csr_matrix([[1.,0.], [1.,0.], [0.,1.], [0.,1.], [0.,1.], [0.,1.]])
chosen = mmr_select(scores, ids, vectors, 3, weight=.3)
assert chosen[0] == 0 and chosen[1] == 2 and len(set(chosen)) == 3
m = portfolio_metrics([0,3], [3,0,1,2,0,0], [True,False,False,True,False,False], distant)
assert m["high_attention_hits"] == 2 and m["distant_high_attention_hits"] == 1

dev = pd.DataFrame({"context":["c"]*3,"k":[10]*3,"share":[0,.2,.4],
                    "high_attention_hits":[10,9,6],"distant_high_attention_hits":[1,3,5]})
rule = fit_allocation_rule(dev, .9)
assert rule.iloc[0]["share"] == .2

paired = pd.DataFrame([dict(organization_id=o,year=y,k=10,model="m",policy=p,hits=v)
    for o in ["a","b","c"] for y in [2020,2021] for p,v in [("topk",2),("quota",3)]])
ci = cluster_bootstrap_difference(paired,"hits","quota",repeats=100)
assert ci["n_organizations"] == 3 and ci["mean_difference"] == 1 and ci["ci_low"] is None
print("PASS: deterministic policy capacity, common selection inputs, MMR, development-only allocation and organization-clustered paired inference")
