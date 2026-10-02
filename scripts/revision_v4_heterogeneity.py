"""Post-hoc organization heterogeneity of fixed v3 pair lists; no reselection/model fit."""
from __future__ import annotations
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '2'
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT/'temp')
import json, shutil
import numpy as np
import pandas as pd

OUT = ROOT/'results/revision_v4'
V3 = ROOT/'results/revision_v3'
KEY = ['organization_id', 'year', 'model']
GROUPS = {'core_history_fraction': 'core_share_group', 'history_n': 'history_size_group',
          'pool_n': 'pool_size_group', 'history_subclass_breadth': 'breadth_group'}
SEED = 20261001
REPEATS = 2000

def emit(event, **values):
    print(json.dumps({'event': event, **values}, ensure_ascii=False), flush=True)

def codes(value):
    return {x for x in str(value).split('|') if x and x not in {'nan', 'None', '<NA>'}}

def md(frame):
    def cell(v):
        return f'{v:.4f}' if isinstance(v, (float, np.floating)) else str(v).replace('|', '\\|')
    return '\n'.join(['| '+' | '.join(frame.columns)+' |', '| '+' | '.join(['---']*len(frame.columns))+' |',
                      *['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False, name=None)]])

def main():
    assert ROOT.exists(), 'Working project directory is unavailable'
    OUT.mkdir(parents=True, exist_ok=True); (ROOT/'temp').mkdir(exist_ok=True)
    protocol = dict(stage='V4 post-hoc descriptive boundary analysis after battery outcomes were known',
        task='Existing battery core_task raw-name sample, frozen pair lists, K30, both rankers',
        admission='All356 organization-year situations and114 unique raw organization keys',
        grouping=dict(core_history_fraction='low<.02; middle .02<=fraction<=.05; high>.05',
                      tertiles='Linear quantiles at1/3 and2/3 over356 origin situations, not model duplicates; low<=q1, mid q1<x<=q2, high>q2; do not split ties',
                      breadth='Distinct four-character CPC/IPC subclass union over all focal preceding-five-complete-year granted patents, including core and noncore; raw-name membership, co-owned grants counted once per focal owner'),
        main='Original pair q30 minus Top30 (naive), matched minus Top30 (capacity), q30 minus matched (controlled); task T',
        descriptors=['situations', 'unique raw organization keys', 'Top30 core seats', 'delta core seats',
                     'three task differences and W/T/L', 'strict naive-positive/controlled-negative frequency',
                     'original quota binding and changed ID quantities'],
        supporting='C9 novelty-blind minus Top30 within the same descriptive groups',
        uncertainty='Only core-share controlled contrast:2000 paired organization resamples seed20261001; eligible only if n>=30 situations and>=15 unique organizations; otherwise descriptive only',
        limits='Origin groups are post-hoc and the same organization can appear in several groups across years. No causal moderation, new independent validation, cognitive distance or absorptive-capacity measure. No group significance ranking. No grid/model rerun.',
        D_free_bytes=shutil.disk_usage(ROOT).free)
    # Lock the outcome-independent grouping rule before importing the existing outcome summaries.
    (OUT/'heterogeneity_protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    emit('protocol_locked', D_free_bytes=protocol['D_free_bytes'])
    s = pd.read_parquet(ROOT/'results/revision_v2/taskpool_raw_situations.parquet')
    s = s[(s.relevance=='core_task') & (s.year>=2018)].copy()
    assert len(s)==356 and s.organization_id.nunique()==114
    assert not s.duplicated(['organization_id', 'year']).any()
    assert np.allclose(s.core_history_fraction, s.core_history_n/s.history_n, atol=1e-15, rtol=0)
    h = pd.read_parquet(ROOT/'datasets/canonical_v1/study_portfolios.parquet',
                        columns=['patent_id', 'patent_date', 'assignee_id', 'cpc_codes', 'is_core'])
    assert h.patent_id.nunique()==len(h)
    h['grant_year'] = pd.to_datetime(h.patent_date).dt.year
    h = h[(h.grant_year>=2013) & (h.grant_year<=2020)].copy()
    h['owners'] = h.assignee_id.map(codes)
    h['subclasses'] = h.cpc_codes.map(codes)
    breadth = []
    for year, sy in s.groupby('year'):
        hy = h[(h.grant_year>=year-5) & (h.grant_year<year)].reset_index(drop=True)
        member = hy[['patent_id', 'owners']].explode('owners')
        member = member[member.owners.isin(sy.organization_id)]
        groups = member.groupby('owners').groups
        for row in sy.itertuples():
            ii = np.asarray(groups[row.organization_id], int)
            assert len(ii)==row.history_n
            assert int(hy.iloc[ii].is_core.sum())==row.core_history_n
            union = set().union(*hy.iloc[ii].subclasses)
            assert all(len(x)==4 for x in union)
            coverage = float(hy.iloc[ii].subclasses.map(bool).mean())
            assert np.isclose(coverage, row.classification_coverage, atol=1e-12, rtol=0)
            breadth.append(dict(organization_id=row.organization_id, year=int(year), history_subclass_breadth=len(union)))
        emit('origin_features_year', year=int(year), situations=len(sy))
    s = s.merge(pd.DataFrame(breadth), on=['organization_id', 'year'], validate='one_to_one')
    s['core_share_group'] = np.select([s.core_history_fraction<.02, s.core_history_fraction<=.05],
                                    ['low_lt2pct', 'middle_2_to5pct_inclusive'], default='high_gt5pct')
    thresholds = []
    for feature, group_col in list(GROUPS.items())[1:]:
        q1, q2 = np.quantile(s[feature].to_numpy(float), [1/3, 2/3], method='linear')
        s[group_col] = np.select([s[feature]<=q1, s[feature]<=q2], ['low_tertile', 'middle_tertile'], default='high_tertile')
        thresholds.append(dict(feature=feature, lower_cut=float(q1), upper_cut=float(q2), quantile_method='linear',
                               lower_closed=True, middle_lower_open=True, middle_upper_closed=True, high_lower_open=True))
    pd.DataFrame(thresholds).to_csv(OUT/'heterogeneity_thresholds.csv', index=False)
    s.to_parquet(OUT/'heterogeneity_origin_features.parquet', index=False)
    emit('thresholds_frozen', thresholds=thresholds,
         core_share_group_sizes=s.groupby('core_share_group').size().to_dict())

    # All outcome/selection data below are existing v3 files, imported after origin cutpoints were fixed.
    detail = pd.read_parquet(V3/'decision_policy_detail.parquet')
    detail = detail[(detail.boundary=='core_newpair') & detail.policy.isin(
        ['unconstrained_top30', 'original_q30', 'original_q30_matched', 'C09_r00'])].copy()
    policy_names = {'unconstrained_top30':'top30', 'original_q30':'q30', 'original_q30_matched':'matched', 'C09_r00':'C9'}
    d = s.copy()
    models = pd.DataFrame({'model':['boosting', 'ridge']})
    d = d.merge(models, how='cross')
    for policy_name, prefix in policy_names.items():
        x = detail[detail.policy==policy_name][KEY+['core_seats', 'novel_core_seats', 'task_T', 'task_U']]
        x = x.rename(columns={c:prefix+'_'+c for c in ['core_seats', 'novel_core_seats', 'task_T', 'task_U']})
        d = d.merge(x, on=KEY, validate='one_to_one')
    d['delta_core_seats'] = d.q30_core_seats-d.top30_core_seats
    assert np.array_equal(d.q30_core_seats.to_numpy(), d.matched_core_seats.to_numpy())
    d['quota_binding'] = d.top30_novel_core_seats<9
    assert (d.q30_novel_core_seats>=9).all()
    for name, left, right in [('naive','q30','top30'), ('capacity','matched','top30'), ('controlled','q30','matched'), ('C9','C9','top30')]:
        d[name+'_task_delta'] = d[left+'_task_T']-d[right+'_task_T']
    d['controlled_novel_task_delta'] = d.q30_task_U-d.matched_task_U
    d['C9_delta_core_seats'] = d.C9_core_seats-d.top30_core_seats
    assert np.array_equal(d.naive_task_delta.to_numpy(), (d.capacity_task_delta+d.controlled_task_delta).to_numpy())
    d['strict_naive_positive_controlled_negative'] = (d.naive_task_delta>0)&(d.controlled_task_delta<0)
    sel = pd.read_parquet(V3/'decision_selected.parquet', columns=KEY+['boundary', 'policy', 'patent_id'],
                          filters=[('boundary','==','core_newpair'), ('policy','in',list(policy_names))])
    maps = {(o, int(y), m, policy_names[pp]):set(g.patent_id) for (o,y,m,pp),g in sel.groupby(KEY+['policy'])}
    exchange = []
    for row in d.itertuples():
        key=(row.organization_id,int(row.year),row.model)
        z=dict(zip(KEY,key))
        for name, left, right in [('naive','q30','top30'), ('capacity','matched','top30'), ('controlled','q30','matched'), ('C9','C9','top30')]:
            aa,bb=maps[*key,left],maps[*key,right]
            added=len(aa-bb); removed=len(bb-aa)
            assert added==removed and len(aa)==len(bb)==30
            z[name+'_exchange_IDs']=added
        exchange.append(z)
    d=d.merge(pd.DataFrame(exchange),on=KEY,validate='one_to_one')
    assert np.array_equal(d.quota_binding.to_numpy(), (d.naive_exchange_IDs>0).to_numpy())
    # Crosscheck every existing v3 task contrast without any change to its lists or scores.
    old=pd.read_parquet(V3/'decision_contrast_detail.parquet')
    old=old[old.boundary=='core_newpair']
    comparison_map={'naive':'original_q30_minus_unconstrained_top30','capacity':'original_q30_matched_minus_unconstrained_top30',
                    'controlled':'original_q30_minus_original_q30_matched','C9':'C09_r00_minus_unconstrained_top30'}
    for name, comparison in comparison_map.items():
        oo=old[old.comparison==comparison].set_index(KEY).sort_index()
        dd=d.set_index(KEY).sort_index()
        assert oo.index.equals(dd.index)
        assert np.array_equal(oo.delta_task_T.to_numpy(),dd[name+'_task_delta'].to_numpy())
    d.to_parquet(OUT/'heterogeneity_decision_detail.parquet',index=False)
    summaries=[]
    for feature,group_col in GROUPS.items():
        for (model,group),g in d.groupby(['model',group_col]):
            z=dict(feature=feature,group=group,model=model,n_situations=len(g),n_organizations=g.organization_id.nunique(),
                   group_value_min=float(g[feature].min()),group_value_max=float(g[feature].max()),
                   mean_top30_core_seats=float(g.top30_core_seats.mean()),mean_q30_core_seats=float(g.q30_core_seats.mean()),
                   mean_delta_core_seats=float(g.delta_core_seats.mean()),
                   mean_top30_task_T=float(g.top30_task_T.mean()),mean_q30_task_T=float(g.q30_task_T.mean()),
                   mean_matched_task_T=float(g.matched_task_T.mean()),mean_controlled_novel_task_delta=float(g.controlled_novel_task_delta.mean()),
                   quota_binding_n=int(g.quota_binding.sum()),quota_binding_fraction=float(g.quota_binding.mean()),
                   strict_reversal_n=int(g.strict_naive_positive_controlled_negative.sum()),
                   strict_reversal_fraction=float(g.strict_naive_positive_controlled_negative.mean()))
            for name in comparison_map:
                vals=g[name+'_task_delta'];ex=g[name+'_exchange_IDs']
                z[name+'_task_delta']=float(vals.mean())
                z[name+'_wins']=int((vals>0).sum());z[name+'_ties']=int((vals==0).sum());z[name+'_losses']=int((vals<0).sum())
                z[name+'_mean_exchange_IDs']=float(ex.mean());z[name+'_changed_situations']=int((ex>0).sum())
                z[name+'_changed_fraction']=float((ex>0).mean())
            z['C9_mean_delta_core_seats']=float(g.C9_delta_core_seats.mean())
            summaries.append(z)
    summary=pd.DataFrame(summaries)
    summary.to_csv(OUT/'heterogeneity_summary.csv',index=False)
    summary[summary.feature=='core_history_fraction'].to_csv(OUT/'heterogeneity_main_core_share.csv',index=False)
    emit('POINTS_READY', main=summary[summary.feature=='core_history_fraction'][[
        'group','model','n_situations','n_organizations','mean_top30_core_seats','mean_delta_core_seats',
        'naive_task_delta','capacity_task_delta','controlled_task_delta','strict_reversal_n']].to_dict('records'))
    boot=[]
    for (model,group),g in d.groupby(['model','core_share_group']):
        point=float(g.controlled_task_delta.mean());no=g.organization_id.nunique()
        row=dict(model=model,group=group,n_situations=len(g),n_organizations=no,point=point,repeats=REPEATS,seed=SEED,
                 method='paired_organization_percentile',lower=np.nan,upper=np.nan,status='descriptive_only_sparse')
        if len(g)>=30 and no>=15:
            stat=g.groupby('organization_id').agg(delta_sum=('controlled_task_delta','sum'),situations=('year','size')).sort_index()
            arr=stat.to_numpy(float);rng=np.random.default_rng(SEED)
            ix=rng.integers(0,len(stat),size=(REPEATS,len(stat)))
            draws=arr[ix].sum(axis=1);dist=draws[:,0]/draws[:,1]
            assert np.isclose(arr[:,0].sum()/arr[:,1].sum(),point,rtol=0,atol=1e-12)
            row.update(lower=float(np.quantile(dist,.025)),upper=float(np.quantile(dist,.975)),status='computed')
        boot.append(row)
    boot=pd.DataFrame(boot);boot.to_csv(OUT/'heterogeneity_core_share_bootstrap.csv',index=False)
    for feature in GROUPS:
        for model in ['boosting','ridge']:
            ss=summary[(summary.feature==feature)&(summary.model==model)]
            assert int(ss.n_situations.sum())==356
            full=d[d.model==model]
            for name in comparison_map:
                assert np.isclose(np.average(ss[name+'_task_delta'],weights=ss.n_situations),full[name+'_task_delta'].mean(),rtol=0,atol=1e-12)
            assert int(ss.strict_reversal_n.sum())==(50 if model=='boosting' else 25)
    crossings={}
    for feature,group_col in GROUPS.items():
        crossings[feature]=int((s.groupby('organization_id')[group_col].nunique()>1).sum())
    audit=dict(status='PASS',n_situations=356,n_unique_raw_organization_keys=114,n_model_situations=len(d),
        complete_history_membership_count_recovery='Exact all356 history_n and core_history_n; classification coverage within1e-12',
        breadth_source='Complete prior-five-year canonical portfolio, distinct union of archived four-character CPC/IPC codes',
        existing_v3_task_contrast_recovery='Exact all four contrasts at each712 model-situations',
        naive_capacity_controlled_identity='Exact per situation',quota_binding_equals_changed_original_list='Exact',
        group_weighted_means='All4 groupings reproduce all full-sample contrast means within1e-12',
        strict_reversal_recovery=dict(boosting=50,ridge=25),organizations_crossing_groups=crossings,
        preserved='No writes to v1-v3 or raw files; no model or grid rerun')
    (OUT/'heterogeneity_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    table=summary[summary.feature=='core_history_fraction'][['group','model','n_situations','n_organizations',
        'mean_top30_core_seats','mean_delta_core_seats','naive_task_delta','capacity_task_delta','controlled_task_delta',
        'controlled_wins','controlled_ties','controlled_losses','strict_reversal_n']].copy()
    text='# V4 organization heterogeneity: executed descriptive analysis\n\n'
    text+='The protocol was locked before producing these subgroup summaries, after the battery outcomes were already known. It is a post-hoc descriptive analysis for Technology Analysis & Strategic Management. All groups use origin variables; no future event selects a threshold or a list. D free space at launch: '+str(protocol['D_free_bytes'])+' bytes.\n\n'
    text+='Core-history share is coded battery-core grants divided by all grants in the focal preceding five complete calendar years. The groups are <2%, 2–5% inclusive, and >5%. Portfolio size and eligible pool size use linear origin-situation tertiles over all356 situations, with low≤q1, middle q1<x≤q2, and high>q2; ties are retained. Historical domain breadth counts the distinct archived four-character CPC/IPC subclass union across that complete history, including core/noncore patents. It describes observed classification coverage, not cognitive distance or absorptive capacity. Shared patents can enter each recorded focal owner portfolio; raw keys do not merge parent groups.\n\n'
    text+='Frozen tertile thresholds:\n\n'+md(pd.DataFrame(thresholds)[['feature','lower_cut','upper_cut']])+'\n\n'
    text+='Core-share results (all three contrasts use the same356 situations in aggregate):\n\n'+md(table)+'\n\n'
    text+='Paired organization-resampling limits for controlled task differences:\n\n'+md(boot)+'\n\n'
    text+='All other tertile group results are retained below; negative and positive results have equal status. These are separate one-variable descriptions, not jointly adjusted moderator estimates.\n\n'
    text+=md(summary[summary.feature!='core_history_fraction'][['feature','group','model','n_situations','n_organizations',
        'mean_top30_core_seats','mean_delta_core_seats','naive_task_delta','capacity_task_delta','controlled_task_delta',
        'strict_reversal_n','quota_binding_fraction','controlled_mean_exchange_IDs']])+'\n\n'
    text+='C9 versus Top30 supporting description:\n\n'+md(summary[['feature','group','model','n_situations','n_organizations',
        'C9_mean_delta_core_seats','C9_task_delta','C9_wins','C9_ties','C9_losses']])+'\n\n'
    text+='The number of unique raw organization keys is not a new independent-validation sample. The same organization may change groups over its historical years: '+json.dumps(crossings)+'. Repeated years and shared patent outcomes persist. Core-share bootstrap resamples organizations within each group, retaining its assigned years and dividing by the sampled situation count; those intervals do not test a difference between groups and do not remove shared-patent dependence. They are historical exploratory organization sensitivities, not causal interaction evidence. Groups below30 situations or15 unique keys receive no interval.\n\n'
    text+='Top30 core composition and actual changed identifiers remain distinct from historical breadth and share. A quota binds exactly when the original Top30 includes fewer than nine recorded-new-pair core patents; an outcome tie does not show a nonbinding quota. The matched lists preserve actual q30 core seats and noncore IDs. Three-way task differences satisfy naive=capacity+controlled per situation. All subgroup means reconcile to the existing v3 results. No claim that higher core share must imply a lower benefit is imposed.\n\n'
    text+='Outputs: scripts/revision_v4_heterogeneity.py; results/revision_v4/heterogeneity_protocol.json, heterogeneity_thresholds.csv, heterogeneity_origin_features.parquet, heterogeneity_decision_detail.parquet, heterogeneity_summary.csv, heterogeneity_main_core_share.csv, heterogeneity_core_share_bootstrap.csv and heterogeneity_audit.json. Full W/T/L, strict reversals, quota binding and all three changed-ID quantities appear in the summary and detail files.\n'
    (ROOT/'research/revision_v4_heterogeneity.md').write_text(text,encoding='utf-8')
    emit('COMPLETE',audit=audit,bootstrap=boot.to_dict('records'))

if __name__=='__main__': main()
