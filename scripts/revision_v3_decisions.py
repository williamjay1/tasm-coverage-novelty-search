"""Exploratory frozen-list V3 decision analysis. Never fit scores or select on outcomes."""
from __future__ import annotations
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '2'
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT / 'temp')
import argparse, json, math, shutil
import numpy as np
import pandas as pd
from scipy import sparse
from policy_core import stable_order

OUT = ROOT / 'results/revision_v3'
V2 = ROOT / 'results/revision_v2'
BOUNDS = ['core_newgroup', 'core_newpair']
MODELS = ['boosting', 'ridge']
CS = [0, 3, 6, 9, 12, 15, 30]
RS = [0., .3, .5]
LABELS = {'task': 'future_core_signal_1patent', 'general': 'future_external_signal_2org',
          'applicant': 'future_applicant_signal_2org'}
KEY = ['organization_id', 'year', 'model', 'boundary']
METRICS = [x + '_' + y for x in LABELS for y in ['T', 'U']]
SEED = 20261001

def emit(event, **values):
    print(json.dumps({'event': event, **values}, ensure_ascii=False), flush=True)

def markdown(frame):
    def cell(value):
        if isinstance(value, (float, np.floating)):
            return f'{value:.6f}'
        return str(value).replace('|', '\\|')
    return '\n'.join(['| ' + ' | '.join(map(str, frame.columns)) + ' |',
                      '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |',
                      *['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)]])

def policy(c, r):
    return f'C{c:02d}_r{int(round(r*100)):02d}'

def exact_floor(candidates, ranking, novel, c, target):
    """Reserve an explicit ceil(C*r) floor, fill by frozen score, no silent truncation."""
    ordered = candidates[ranking]
    reserved = list(ordered[novel[ordered]][:target])
    if len(reserved) != target:
        raise ValueError('Infeasible novelty floor')
    used = set(reserved)
    for j in ordered:
        if len(reserved) == c:
            break
        if int(j) not in used:
            reserved.append(int(j)); used.add(int(j))
    assert len(reserved) == c
    return np.asarray(reserved, int)

def point_run():
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'temp').mkdir(exist_ok=True)
    assert ROOT.exists(), 'Working project directory is unavailable'
    emit('space_check', D_free_bytes=shutil.disk_usage(ROOT).free)
    situations = pd.read_parquet(V2 / 'taskpool_raw_situations.parquet')
    situations = situations[(situations.relevance == 'core_task') & (situations.year >= 2018)]
    assert len(situations) == 356
    smap = situations.set_index(['organization_id', 'year'])
    labels = pd.read_parquet(ROOT / 'datasets/revision_v2/task_patent_labels.parquet',
                             columns=['patent_id', *LABELS.values()])
    labels['patent_id'] = labels.patent_id.astype(str)
    records, feasibility, selected_parts, exposures = [], [], [], []
    old_recovery = []
    for year in [2018, 2019, 2020, 2021]:
        pool = pd.read_parquet(V2 / f'taskpool_raw_pools_{year}.parquet')
        pool = pool[pool.relevance == 'core_task'].copy()
        pool['patent_id'] = pool.patent_id.astype(str)
        scores = pd.read_parquet(ROOT / f'results/primary_v1/scores_{year}.parquet',
                                 columns=['patent_id', 'score_boosting', 'score_ridge'])
        scores['patent_id'] = scores.patent_id.astype(str)
        pool = pool.merge(scores, on='patent_id', validate='many_to_one')
        pool = pool.merge(labels, on='patent_id', validate='many_to_one')
        assert not pool[list(LABELS.values()) + ['score_boosting', 'score_ridge']].isna().any().any()
        old = pd.read_parquet(V2 / f'taskpool_raw_selected_{year}.parquet')
        old = old[(old.relevance == 'core_task') & old.model.isin(MODELS) & old.boundary.isin(BOUNDS)
                  & old.q.isin([0., .3])].copy()
        old['patent_id'] = old.patent_id.astype(str)
        oldmap = {(o, m, b, float(q)): set(g.patent_id) for (o, m, b, q), g in
                  old.groupby(['organization_id', 'model', 'boundary', 'q'])}
        for org, p in pool.groupby('organization_id', sort=True):
            p = p.reset_index(drop=True)
            ids = p.patent_id.to_numpy(str); core = p.is_core.to_numpy(bool)
            n = len(p); ci = np.flatnonzero(core); ni = np.flatnonzero(~core)
            hist = smap.loc[(org, year)]
            assert n == hist.pool_n
            ex = p[['organization_id', 'year', 'patent_id', 'is_core', *BOUNDS]].copy()
            ex['pool_n'] = n; ex['exposure'] = 1. / n
            exposures.append(ex)
            assert not p.loc[p.is_core, 'subclass_external'].any()
            for model in MODELS:
                score = p['score_' + model].to_numpy(float)
                ranking = stable_order(score, ids)
                cr = stable_order(score[ci], ids[ci]); nr = stable_order(score[ni], ids[ni])
                top = ranking[:30]
                original_core = int(core[top].sum())
                context = 'low_lt9' if original_core < 9 else ('equal9' if original_core == 9 else 'high_gt9')
                for boundary in BOUNDS:
                    novel = p[boundary].to_numpy(bool)
                    common = dict(organization_id=org, year=year, model=model, boundary=boundary,
                                  pool_n=n, core_pool_n=len(ci), noncore_pool_n=len(ni),
                                  novel_core_pool_n=int(novel.sum()), original_top30_core_seats=original_core,
                                  original_core_context=context, history_n=int(hist.history_n),
                                  core_history_n=int(hist.core_history_n))
                    def add(name, ss, c_requested=-1, r=0., target=0):
                        ss = np.asarray(ss, int)
                        assert len(ss) == len(set(ss)) == 30
                        row = dict(common, policy=name, C_requested=c_requested, novelty_floor=r,
                                   floor_target=target, core_seats=int(core[ss].sum()),
                                   novel_core_seats=int(novel[ss].sum()))
                        for outcome, col in LABELS.items():
                            lab = p[col].to_numpy(bool)
                            row[outcome + '_T'] = int(lab[ss].sum())
                            row[outcome + '_U'] = int((lab[ss] & novel[ss]).sum())
                        records.append(row)
                        sf = p.iloc[ss][['patent_id', 'is_core', boundary, *LABELS.values()]].copy()
                        sf = sf.rename(columns={boundary: 'recorded_novel', **{v: k + '_signal' for k, v in LABELS.items()}})
                        sf['organization_id'] = org; sf['year'] = year; sf['model'] = model
                        sf['boundary'] = boundary; sf['policy'] = name
                        selected_parts.append(sf)
                    add('unconstrained_top30', top)
                    assert set(ids[top]) == oldmap[org, model, boundary, 0.]
                    fullc = min(30, len(ci))
                    add('full_core_priority', np.r_[ci[cr[:fullc]], ni[nr[:30-fullc]]])
                    qids = oldmap[org, model, boundary, .3]
                    qsel = np.flatnonzero(np.isin(ids, list(qids)))
                    qc = int(core[qsel].sum())
                    blind = np.r_[ci[cr[:qc]], qsel[~core[qsel]]]
                    assert set(ids[blind[~core[blind]]]) == set(ids[qsel[~core[qsel]]])
                    add('original_q30', qsel)
                    add('original_q30_matched', blind)
                    old_recovery.append(dict(organization_id=org, year=year, model=model, boundary=boundary,
                                             core_counts_match=True, noncore_ids_match=True))
                    for c in CS:
                        capacity_ok = len(ci) >= c and len(ni) >= 30-c
                        noncore = ni[nr[:30-c]]
                        reference_core = ci[cr[:c]]
                        for r in RS:
                            target = int(math.ceil(c * r))
                            feasible = capacity_ok and int(novel.sum()) >= target
                            feasibility.append(dict(common, policy=policy(c, r), C_requested=c,
                                                    novelty_floor=r, floor_target=target,
                                                    capacity_feasible=capacity_ok, novelty_feasible=int(novel.sum()) >= target,
                                                    feasible=feasible, reason='ok' if feasible else
                                                    ('core_supply' if len(ci) < c else 'noncore_supply' if len(ni) < 30-c else 'novel_supply')))
                            if not feasible:
                                continue
                            cc = exact_floor(ci, cr, novel, c, target)
                            assert set(noncore) == set(ni[nr[:30-c]])
                            ss = np.r_[cc, noncore]
                            add(policy(c, r), ss, c, r, target)
                            records[-1]['reservation_binding'] = int(novel[reference_core].sum()) < target
                            records[-1]['novel_supply_at_floor'] = int(novel.sum()) == target
        emit('year_points_done', year=year, policy_rows=len(records))
    detail = pd.DataFrame(records)
    feas = pd.DataFrame(feasibility)
    selected = pd.concat(selected_parts, ignore_index=True)
    exposure = pd.concat(exposures, ignore_index=True)
    detail.to_parquet(OUT / 'decision_policy_detail.parquet', index=False)
    selected.to_parquet(OUT / 'decision_selected.parquet', index=False)
    exposure.to_parquet(OUT / 'decision_pool_exposure.parquet', index=False)
    exposure.groupby('patent_id').agg(pool_occurrences=('year', 'size'), exposed_organizations=('organization_id', 'nunique'),
                                     standardized_exposure=('exposure', 'sum')).reset_index().to_csv(OUT / 'decision_patent_exposure.csv', index=False)
    feas.to_csv(OUT / 'decision_feasibility.csv', index=False)
    feas.groupby(['model', 'boundary', 'C_requested', 'novelty_floor', 'floor_target']).agg(
        admission_situations=('feasible', 'size'), feasible_situations=('feasible', 'sum'),
        capacity_feasible=('capacity_feasible', 'sum'), novelty_feasible=('novelty_feasible', 'sum')).reset_index().to_csv(
            OUT / 'decision_feasibility_summary.csv', index=False)
    summary = detail.groupby(['model', 'boundary', 'policy']).agg(
        situations=('year', 'size'), organizations=('organization_id', 'nunique'),
        **{c: (c, 'mean') for c in ['core_seats', 'novel_core_seats', *METRICS]}).reset_index()
    summary['support'] = 'individual_feasible'
    summary.to_csv(OUT / 'decision_policy_summary.csv', index=False)
    common_parts = []
    for (m, b, c), g in feas.groupby(['model', 'boundary', 'C_requested']):
        good = g.groupby(['organization_id', 'year']).feasible.all()
        kk = set(good[good].index)
        dd = detail[(detail.model == m) & (detail.boundary == b) & (detail.C_requested == c)].copy()
        dd = dd[[(o, y) in kk for o, y in zip(dd.organization_id, dd.year)]]
        if len(dd): common_parts.append(dd)
    common_grid = pd.concat(common_parts, ignore_index=True)
    common_grid.groupby(['model', 'boundary', 'C_requested', 'novelty_floor']).agg(
        situations=('year', 'size'), organizations=('organization_id', 'nunique'),
        **{c: (c, 'mean') for c in ['core_seats', 'novel_core_seats', *METRICS]}).reset_index().to_csv(
            OUT / 'decision_grid_common_summary.csv', index=False)
    contrasts = []
    for (model, boundary), g in detail.groupby(['model', 'boundary']):
        policies = {name: pp.set_index(['organization_id', 'year']) for name, pp in g.groupby('policy')}
        comparisons = [('full_core_priority', 'unconstrained_top30'), ('original_q30', 'unconstrained_top30'),
                       ('original_q30_matched', 'unconstrained_top30'), ('original_q30', 'original_q30_matched')]
        for c in CS:
            comparisons.append((policy(c, 0), 'unconstrained_top30'))
            if c:
                comparisons.extend([(policy(c, .3), policy(c, 0)), (policy(c, .5), policy(c, 0))])
        for alt, ref in comparisons:
            if alt not in policies or ref not in policies: continue
            ix = policies[alt].index.intersection(policies[ref].index)
            if alt.startswith('C') and ref.startswith('C'):
                c = int(alt[1:3])
                for r in RS:
                    ix = ix.intersection(policies.get(policy(c, r), pd.DataFrame()).index)
            aa, bb = policies[alt].loc[ix], policies[ref].loc[ix]
            if not len(ix): continue
            z = aa[METRICS].subtract(bb[METRICS]).add_prefix('delta_').reset_index()
            z['model'] = model; z['boundary'] = boundary; z['alternative'] = alt; z['reference'] = ref
            z['comparison'] = alt + '_minus_' + ref
            for col in ['original_top30_core_seats', 'original_core_context', 'core_history_n', 'core_pool_n', 'pool_n']:
                z[col] = aa[col].to_numpy()
            z['delta_core_seats'] = aa.core_seats.to_numpy() - bb.core_seats.to_numpy()
            z['delta_novel_core_seats'] = aa.novel_core_seats.to_numpy() - bb.novel_core_seats.to_numpy()
            contrasts.append(z)
    cd = pd.concat(contrasts, ignore_index=True)
    cd.to_parquet(OUT / 'decision_contrast_detail.parquet', index=False)
    def aggregate_contrasts(frame, groups):
        rows = []
        for key, g in frame.groupby(groups, dropna=False):
            key = key if isinstance(key, tuple) else (key,)
            row = dict(zip(groups, key), situations=len(g), organizations=g.organization_id.nunique())
            for col in ['delta_core_seats', 'delta_novel_core_seats', *['delta_' + c for c in METRICS]]:
                row[col] = float(g[col].mean())
            for outcome in LABELS:
                v = g['delta_' + outcome + '_T']
                row[outcome + '_wins'] = int((v > 0).sum()); row[outcome + '_ties'] = int((v == 0).sum())
                row[outcome + '_losses'] = int((v < 0).sum())
            rows.append(row)
        return pd.DataFrame(rows)
    cs = aggregate_contrasts(cd, ['model', 'boundary', 'comparison'])
    cs.to_csv(OUT / 'decision_contrasts.csv', index=False)
    aggregate_contrasts(cd, ['model', 'boundary', 'comparison', 'original_core_context']).to_csv(
        OUT / 'decision_context_contrasts.csv', index=False)
    aggregate_contrasts(cd, ['year', 'model', 'boundary', 'comparison']).to_csv(
        OUT / 'decision_annual_contrasts.csv', index=False)
    # Export selected-union patent contributions for the locked bootstrap contrasts.
    anchors = selected[selected.policy.isin(['original_q30', 'original_q30_matched'])].copy()
    ix = KEY + ['patent_id']
    a = anchors[anchors.policy == 'original_q30'].drop(columns='policy').set_index(ix)
    b = anchors[anchors.policy == 'original_q30_matched'].drop(columns='policy').set_index(ix)
    union = a.index.union(b.index)
    present_a = pd.Series(1, index=a.index).reindex(union, fill_value=0)
    present_b = pd.Series(1, index=b.index).reindex(union, fill_value=0)
    values = pd.concat([a, b]).groupby(level=list(range(len(ix)))).first().reindex(union)
    contributions = values.reset_index()
    contributions['alternative_selected'] = present_a.to_numpy(); contributions['reference_selected'] = present_b.to_numpy()
    contributions['membership_delta'] = (present_a - present_b).to_numpy()
    contributions['comparison'] = 'original_q30_minus_original_q30_matched'
    for outcome in LABELS:
        contributions['delta_' + outcome + '_T'] = contributions.membership_delta * contributions[outcome + '_signal'].astype(int)
        contributions['delta_' + outcome + '_U'] = contributions['delta_' + outcome + '_T'] * contributions.recorded_novel.astype(int)
    contributions.to_parquet(OUT / 'decision_patent_contributions.parquet', index=False)
    unit = contributions.groupby(KEY)[['delta_' + c for c in METRICS]].sum().sort_index()
    expected = cd[cd.comparison == 'original_q30_minus_original_q30_matched'].set_index(KEY)[unit.columns].sort_index()
    assert unit.index.equals(expected.index)
    assert np.array_equal(unit.to_numpy(), expected.to_numpy())
    # Reconcile Boost's published matched-control lists and all endpoint totals.
    oldlists = pd.read_parquet(V2 / 'fine_core_slot_selected.parquet')
    oldlists['patent_id'] = oldlists.patent_id.astype(str)
    policy_map = {'score_only': 'unconstrained_top30', 'novelty_quota_30': 'original_q30',
                  'matched_core_slots_blind': 'original_q30_matched'}
    oldsets = oldlists.groupby(['organization_id', 'year', 'boundary', 'policy']).patent_id.agg(set)
    newsets = selected[selected.model == 'boosting'].groupby(['organization_id', 'year', 'boundary', 'policy']).patent_id.agg(set)
    assert all(v == newsets.loc[(o, y, b, policy_map[pp])] for (o, y, b, pp), v in oldsets.items())
    od = pd.read_parquet(V2 / 'fine_core_slot_detail.parquet')
    oldmetrics = od.assign(policy=od.policy.map(policy_map)).rename(columns={'core1_T': 'task_T', 'core1_U': 'task_U'}).set_index(
        ['organization_id', 'year', 'boundary', 'policy'])[METRICS].sort_index()
    newmetrics = detail[(detail.model == 'boosting') & detail.policy.isin(policy_map.values())].set_index(
        ['organization_id', 'year', 'boundary', 'policy'])[METRICS].sort_index()
    assert oldmetrics.index.equals(newmetrics.index)
    assert np.array_equal(oldmetrics.to_numpy(), newmetrics.to_numpy())
    audit = dict(status='PASS', original_situations=356, organizations=situations.organization_id.nunique(),
                 n_policy_rows=len(detail), n_selection_events=len(selected), n_pool_exposures=len(exposure),
                 boost_published_list_recovery='exact for all 2136 lists', boost_published_endpoint_recovery='exact',
                 matched_core_count_mismatches=0, matched_noncore_id_mismatches=0,
                 selected_union_contribution_point_audit='exact all six metrics, four model/boundary contrasts',
                 core_candidates_strict_subclass_external=0,
                 explicit_floor_targets=[dict(C=c, r=r, ceil_target=math.ceil(c*r), prior_nearest_target=math.floor(c*r+.5)) for c in CS for r in RS],
                 original_case_membership='preserved; never written by this script',
                 scope='Known-outcome battery exploratory diagnostic; frozen scores; no retraining or outcome-based selection')
    (OUT / 'decision_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    emit('POINTS_READY', anchors=cs[cs.comparison == 'original_q30_minus_original_q30_matched'].to_dict('records'),
         C9=cs[(cs.boundary == 'core_newpair') & (cs.comparison == 'C09_r00_minus_unconstrained_top30')].to_dict('records'))

def bootstrap(repeats=2000):
    cd = pd.read_parquet(OUT / 'decision_contrast_detail.parquet')
    cd = cd[cd.comparison == 'original_q30_minus_original_q30_matched'].copy()
    contrib = pd.read_parquet(OUT / 'decision_patent_contributions.parquet')
    ex = pd.read_parquet(OUT / 'decision_pool_exposure.parquet')
    orgs = sorted(ex.organization_id.unique()); pids = sorted(ex.patent_id.unique())
    om = {o: j for j, o in enumerate(orgs)}; pm = {p: j for j, p in enumerate(pids)}
    e = sparse.coo_matrix((ex.exposure.to_numpy(float), (ex.organization_id.map(om), ex.patent_id.map(pm))),
                          shape=(len(orgs), len(pids))).tocsr()
    assert np.isclose(e.sum(), 356.)
    matrices, points, ordinary, keys = [], [], [], []
    for (model, boundary), g in cd.groupby(['model', 'boundary']):
        stats = g.groupby('organization_id')[[*['delta_' + c for c in METRICS]]].sum().reindex(orgs, fill_value=0)
        counts = g.groupby('organization_id').size().reindex(orgs, fill_value=0).to_numpy(float)
        assert np.array_equal(counts, ex.groupby(['organization_id', 'year']).size().reset_index().groupby('organization_id').size().reindex(orgs).to_numpy())
        rng = np.random.default_rng(SEED)
        draws = rng.integers(0, len(orgs), size=(repeats, len(orgs)))
        den = counts[draws].sum(axis=1)
        boot = stats.to_numpy(float)[draws].sum(axis=1) / den[:, None]
        cc = contrib[(contrib.model == model) & (contrib.boundary == boundary)]
        for j, metric in enumerate(METRICS):
            col = 'delta_' + metric
            mm = sparse.coo_matrix((cc[col].to_numpy(float), (cc.organization_id.map(om), cc.patent_id.map(pm))),
                                   shape=e.shape).tocsr()
            mm.eliminate_zeros()
            point = float(g[col].mean())
            assert np.isclose(mm.sum()/356, point, rtol=0, atol=1e-12)
            matrices.append(mm); points.append(point); ordinary.append(boot[:, j]); keys.append((model, boundary, metric))
    crossed = np.empty((repeats, len(matrices)), float)
    rng = np.random.default_rng(SEED)
    for start in range(0, repeats, 100):
        end = min(start+100, repeats); nb = end-start
        wo = rng.exponential(1., size=(nb, len(orgs)))
        wp = rng.exponential(1., size=(nb, len(pids)))
        denominator = ((e @ wp.T).T * wo).sum(axis=1)
        assert np.all(denominator > 0)
        for j, mm in enumerate(matrices):
            crossed[start:end, j] = ((mm @ wp.T).T * wo).sum(axis=1) / denominator
        if end % 500 == 0: emit('crossed_bootstrap_progress', completed=end, repeats=repeats)
    rows = []
    for j, (model, boundary, metric) in enumerate(keys):
        for method, dist in [('organization_bootstrap', ordinary[j]), ('crossed_org_patent_multiplier_sensitivity', crossed[:, j])]:
            rows.append(dict(model=model, boundary=boundary, comparison='original_q30_minus_original_q30_matched',
                             metric=metric, method=method, situations=356, organizations=len(orgs), unique_pool_patents=len(pids),
                             repeats=repeats, seed=SEED, point=points[j], lower=float(np.quantile(dist, .025)),
                             upper=float(np.quantile(dist, .975))))
    pd.DataFrame(rows).to_csv(OUT / 'decision_bootstrap.csv', index=False)
    (OUT / 'decision_bootstrap_notes.json').write_text(json.dumps(dict(
        status='PASS', seed=SEED, repeats=repeats, comparisons=4, endpoint_metrics=6,
        point_audit='Each signed patent-contribution sum/356 exactly reproduces decision-level means',
        organization='Resample 114 organizations with replacement; retain every historical situation, divide by sampled situation count',
        crossed='Independent Exp(1) weights for organization and patent, product shared across occurrences; fixed lists',
        denominator='Complete pool exposure 1/pool_n per organization-year-patent, including zero-contribution unselected candidates; unit sum356',
        limits='Exploratory dependency sensitivity, not exact confidence coverage or new-environment inference; four observed years remain fixed',
        scope_reduction='Bootstrap limited to original group/pair novelty-minus-matched contrasts for both rankers; grid bootstrap not executed'),
        indent=2), encoding='utf-8')
    emit('BOOTSTRAP_READY', rows=len(rows))

def report():
    cs = pd.read_csv(OUT / 'decision_contrasts.csv')
    sm = pd.read_csv(OUT / 'decision_policy_summary.csv')
    ctx = pd.read_csv(OUT / 'decision_context_contrasts.csv')
    feas = pd.read_csv(OUT / 'decision_feasibility_summary.csv')
    boots = pd.read_csv(OUT / 'decision_bootstrap.csv') if (OUT / 'decision_bootstrap.csv').exists() else pd.DataFrame()
    cols = ['model', 'boundary', 'delta_task_T', 'delta_task_U', 'delta_general_T', 'delta_applicant_T',
            'task_wins', 'task_ties', 'task_losses']
    anchors = cs[cs.comparison == 'original_q30_minus_original_q30_matched'][cols]
    fixed = cs[(cs.boundary == 'core_newpair') & (cs.comparison == 'C09_r00_minus_unconstrained_top30')][cols]
    text = '\n\n## Executed V3 results (1 October 2026)\n\n'
    text += 'All 356 original situations and 114 raw organization keys are retained as the admission denominator. Frozen Boost and Ridge scores, original eligible pools and original novelty fields are reused. No outcomes enter selection and no model is retrained. The exact grid fixes noncore IDs within each C/model; the floor is explicitly ceil(r*C). It is a minimum, so ranked filling may select further novel core documents. The earlier nearest-integer formula happens to agree for all planned C/r cells, but the implementation explicitly uses ceil; the exported audit gives every exact target and crosscheck.\n\n'
    # The exported exact-target audit, not a verbal equivalence claim, governs every cell.
    text += 'Original q30 minus exact-core/noncore matched control:\n\n' + markdown(anchors) + '\n\n'
    text += 'Exact C9 novelty-blind versus unconstrained top30 (pair novelty used for the U composition field):\n\n' + markdown(fixed) + '\n\n'
    cx = ctx[(ctx.boundary == 'core_newpair') & (ctx.comparison == 'C09_r00_minus_unconstrained_top30')]
    text += 'Origin-known context bins are defined from each ranker original top30 core seats before examining outcomes: low<9, equal9, high>9. These are descriptive associations, not causal moderators.\n\n' + markdown(cx[['model', 'original_core_context', 'situations', 'delta_task_T', 'task_wins', 'task_ties', 'task_losses']]) + '\n\n'
    text += 'Grid feasibility:\n\n' + markdown(feas[['model', 'boundary', 'C_requested', 'novelty_floor', 'floor_target', 'admission_situations', 'feasible_situations']]) + '\n\n'
    if len(boots):
        text += 'Paired intervals for the primary task endpoint (all six task/general/applicant T/U metrics are retained in CSV):\n\n' + markdown(boots[boots.metric.isin(['task_T', 'task_U'])][['model', 'boundary', 'metric', 'method', 'point', 'lower', 'upper']]) + '\n\n'
    text += 'Selected-union patent contributions include unchanged selected documents with zero signed contribution. Complete pool candidates, including unselected candidates, are retained separately with exposure1/pool_n. Signed contribution sums exactly recover every original matched point contrast. Boost lists and all six endpoint totals exactly reproduce all 2,136 prior fine-control lists. The product multiplier reweights organization and patent IDs independently with Exp(1), keeps each list fixed and divides by weighted complete pool exposure. Its 2.5/97.5 percentile limits are dependency sensitivities, not exact coverage or environmental generalization. Four observed years and patent-family limitations remain.\n\n'
    text += 'Bootstrap scope was explicitly narrowed to four original q30 novelty-minus-matched comparisons (two novelty definitions, two rankers), each with 2,000 organization draws and 2,000 crossed multiplier draws, seed20261001. Grid intervals were not computed. The full exact grid and its paired win/tie/loss, annual and fixed-origin context points are supplied.\n\n'
    text += 'Outputs: decision_policy_detail.parquet; decision_selected.parquet; decision_policy_summary.csv; decision_grid_common_summary.csv; decision_feasibility.csv; decision_feasibility_summary.csv; decision_contrast_detail.parquet; decision_contrasts.csv; decision_context_contrasts.csv; decision_annual_contrasts.csv; decision_pool_exposure.parquet; decision_patent_exposure.csv; decision_patent_contributions.parquet; decision_bootstrap.csv; decision_bootstrap_notes.json; decision_audit.json. Existing decision_case_membership.parquet is preserved.\n'
    path = ROOT / 'research/revision_v3_decisions.md'
    old = path.read_text(encoding='utf-8')
    marker = '\n\n## Executed V3 results'
    path.write_text(old.split(marker)[0] + text, encoding='utf-8')
    emit('REPORT_READY', path=str(path))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--points-only', action='store_true')
    parser.add_argument('--bootstrap-only', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    parser.add_argument('--repeats', type=int, default=2000)
    args = parser.parse_args()
    if args.report_only:
        report()
    elif not args.bootstrap_only:
        point_run()
    if not args.points_only and not args.report_only:
        bootstrap(args.repeats); report()
