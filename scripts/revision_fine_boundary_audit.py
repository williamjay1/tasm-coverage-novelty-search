"""Fixed-list post-critique audit of native thermal-code history coverage.

No pool, forecast or shortlist is refitted. The clean-history subset is a
measurement diagnostic and is not a new preferred population or policy.
"""
from __future__ import annotations
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import re
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import duckdb

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_v2'
THERMAL=re.compile(r'^H01M10/(6[0-9]|50)')
OLD=re.compile(r'^H01M10/50')
NEW=re.compile(r'^H01M10/6[0-9]')
def code_set(v):
    return {s for s in str(v).split('|') if s and s not in {'nan','None','<NA>'}}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bootstrap-only',action='store_true')
    args=parser.parse_args()
    if args.bootstrap_only:
        paired_core_bootstrap()
        return
    hist=pd.read_parquet(ROOT/'datasets/revision_v2/task_core_history.parquet')
    hist=hist.drop_duplicates(['assignee_id','patent_id']).copy()
    hist['history_grant_year']=pd.to_datetime(hist.date).dt.year
    hist['thermal_cpc']=hist.cpc_at_issue.map(lambda x:bool({c for c in code_set(x) if THERMAL.match(c)}))
    hist['thermal_ipc']=hist.ipc_at_issue.map(lambda x:bool({c for c in code_set(x) if THERMAL.match(c)}))
    hist['old_50_cpc']=hist.cpc_at_issue.map(lambda x:any(OLD.match(c) for c in code_set(x)))
    hist['new_6x_cpc']=hist.cpc_at_issue.map(lambda x:any(NEW.match(c) for c in code_set(x)))
    hist['old_50_any']=hist.cpc_at_issue.fillna('').str.cat(hist.ipc_at_issue.fillna(''),sep='|').map(lambda x:any(OLD.match(c) for c in code_set(x)))
    hist['ipc_only_thermal']=~hist.thermal_cpc & hist.thermal_ipc
    situations=pd.read_parquet(OUT/'taskpool_raw_situations.parquet')
    situations=situations[(situations.relevance=='core_task') & situations.year.between(2018,2021)].copy()
    assert len(situations)==356, len(situations)
    history_rows=[];rows=[]
    for r in situations.itertuples():
        h=hist[(hist.assignee_id==r.organization_id)&(hist.history_grant_year>=r.year-5)&(hist.history_grant_year<r.year)].copy()
        assert len(h)==r.core_history_n, (r.organization_id,r.year,len(h),r.core_history_n)
        h['organization_id']=r.organization_id;h['origin_year']=r.year
        history_rows.append(h)
        n=len(h);n_cpc=int(h.thermal_cpc.sum());nold=int(h.old_50_cpc.sum())
        # Exclude an old thermal code in either native CPC or IPC. This more
        # conservative variant avoids retaining an IPC-era old-code history.
        clean=bool(n_cpc==n and not h.old_50_any.any())
        rows.append({
            'organization_id':r.organization_id,'year':r.year,'core_history_n':n,
            'thermal_cpc_n':n_cpc,'thermal_cpc_coverage':n_cpc/n,
            'ipc_only_thermal_n':int(h.ipc_only_thermal.sum()),
            'ipc_only_thermal_fraction':float(h.ipc_only_thermal.mean()),
            'history_thermal_cpc_coverage_below_80pct':n_cpc/n<.8,
            'old_50_cpc_n':nold,'old_50_any_n':int(h.old_50_any.sum()),
            'new_6x_cpc_n':int(h.new_6x_cpc.sum()),
            'has_old_50_cpc':bool(h.old_50_cpc.any()),
            'has_old_50_any':bool(h.old_50_any.any()),
            'has_old50_new6x_cpc_mix':bool(h.old_50_cpc.any() and h.new_6x_cpc.any()),
            'has_2015_transition_year_grant':bool((h.history_grant_year==2015).any()),
            'has_2015_old50_cpc_grant':bool(((h.history_grant_year==2015)&h.old_50_cpc).any()),
            'has_2015_new6x_cpc_grant':bool(((h.history_grant_year==2015)&h.new_6x_cpc).any()),
            'clean_native_thermal_history':clean,
        })
    a=pd.DataFrame(rows)
    hg=pd.concat(history_rows,ignore_index=True)
    a.to_parquet(OUT/'fine_history_detail.parquet',index=False)
    hg.to_parquet(OUT/'fine_history_grant_rows.parquet',index=False)
    summ=[]
    for year,df in [('all',a),*list(a.groupby('year'))]:
        t=hg if year=='all' else hg[hg.origin_year==year]
        summ.append({
            'year':year,'situations':len(df),'organizations':df.organization_id.nunique(),
            'core_history_grant_events':int(df.core_history_n.sum()),
            'unique_core_history_grants':t.patent_id.nunique(),
            'ipc_only_grant_events':int(df.ipc_only_thermal_n.sum()),
            'ipc_only_grant_event_fraction':float(df.ipc_only_thermal_n.sum()/df.core_history_n.sum()),
            'median_org_history_ipc_only_fraction':float(df.ipc_only_thermal_fraction.median()),
            'coverage_below80_situations':int(df.history_thermal_cpc_coverage_below_80pct.sum()),
            'coverage_below80_fraction':float(df.history_thermal_cpc_coverage_below_80pct.mean()),
            'has_old50_cpc_situations':int(df.has_old_50_cpc.sum()),
            'has_old50_any_situations':int(df.has_old_50_any.sum()),
            'has_old50_new6x_cpc_mix_situations':int(df.has_old50_new6x_cpc_mix.sum()),
            'has_2015_transition_year_grant_situations':int(df.has_2015_transition_year_grant.sum()),
            'has_2015_old50_cpc_situations':int(df.has_2015_old50_cpc_grant.sum()),
            'has_2015_new6x_cpc_situations':int(df.has_2015_new6x_cpc_grant.sum()),
            'clean_situations':int(df.clean_native_thermal_history.sum()),
            'clean_organizations':df.loc[df.clean_native_thermal_history,'organization_id'].nunique(),
        })
    pd.DataFrame(summ).to_csv(OUT/'fine_history_summary.csv',index=False)
    con=duckdb.connect()
    con.execute("SET threads=2; SET memory_limit='3GB'")
    s=con.execute("""SELECT * FROM read_parquet(?)
        WHERE relevance='core_task' AND boundary IN ('core_newgroup','core_newpair')
          AND (q=0 OR q=0.3)""",[str(OUT/'taskpool_raw_selected_*.parquet')]).fetchdf()
    labels=pd.read_parquet(ROOT/'datasets/revision_v2/task_patent_labels.parquet')
    s=s.merge(labels[['patent_id','future_external_signal_2org','future_applicant_signal_2org','future_core_signal_1patent']],on='patent_id',how='left',validate='many_to_one')
    assert not s.future_core_signal_1patent.isna().any()
    s=s.merge(a[['organization_id','year','clean_native_thermal_history']],on=['organization_id','year'],how='left',validate='many_to_one')
    assert not s.clean_native_thermal_history.isna().any()
    details=[]
    keys=['organization_id','year','boundary','model']
    lmap={'general':'future_external_signal_2org','applicant':'future_applicant_signal_2org','core1':'future_core_signal_1patent'}
    for key,g in s.groupby(keys):
        base=g[g.q==0].set_index('patent_id');quota=g[g.q==.3].set_index('patent_id')
        assert len(base)==len(quota)==30
        baseids=set(base.index);qids=set(quota.index);adds=qids-baseids;removed=baseids-qids
        for qval,sel in [(0,base),(.3,quota)]:
            row=dict(zip(keys,key));row.update(q=qval,clean_native_thermal_history=bool(g.clean_native_thermal_history.iloc[0]),changed_n=len(adds) if qval else 0)
            for label,col in lmap.items():
                bt=int(base[col].sum());bu=int((base[col]&base.unfamiliar).sum())
                tt=int(sel[col].sum());uu=int((sel[col]&sel.unfamiliar).sum())
                ad=int(quota.loc[list(adds),col].sum()) if qval and adds else 0
                rm=int(base.loc[list(removed),col].sum()) if qval and removed else 0
                row.update({label+'_T':tt,label+'_U':uu,label+'_base_T':bt,label+'_base_U':bu,label+'_added':ad,label+'_removed':rm})
            details.append(row)
    detail=pd.DataFrame(details)
    detail.to_parquet(OUT/'fine_clean_policy_detail.parquet',index=False)
    options=[]
    for scope,dd in [('all_356',detail),('complete_cpc_no_old50',detail[detail.clean_native_thermal_history])]:
        for year,dy in [('all',dd),*list(dd.groupby('year'))]:
            for (boundary,model,qval),g in dy.groupby(['boundary','model','q']):
                row={'scope':scope,'year':year,'boundary':boundary,'model':model,'q':qval,'situations':len(g),'organizations':g.organization_id.nunique(),'changed_n':g.changed_n.mean()}
                for lname in lmap:
                    bt=g[lname+'_base_T'].sum();rm=g[lname+'_removed'].sum();tt=g[lname+'_T'].sum()
                    row.update({lname+'_T':g[lname+'_T'].mean(),lname+'_U':g[lname+'_U'].mean(),lname+'_delta_T':(g[lname+'_T']-g[lname+'_base_T']).mean(),lname+'_delta_U':(g[lname+'_U']-g[lname+'_base_U']).mean(),lname+'_added':g[lname+'_added'].mean(),lname+'_removed':g[lname+'_removed'].mean(),lname+'_count_ratio':tt/bt if bt else np.nan,lname+'_original_survival':(bt-rm)/bt if bt else np.nan})
                options.append(row)
    options=pd.DataFrame(options)
    options.to_csv(OUT/'fine_clean_options.csv',index=False)
    audit={'n_situations':len(a),'history_n_reconciliation_mismatches':0,'n_clean_situations':int(a.clean_native_thermal_history.sum()),'native_codes':'CPC/IPC at issue; no invented old-to-new finer code map','clean_definition':'Every prior-five-year core grant has a native thermal CPC group and none has an H01M10/50 code in either CPC or IPC','fixed_list_keys':keys,'pool_forecast_selection_refit':False,'q_values':[0,.3],'outcomes':lmap,'interpretation':'Non-random history-coverage subset diagnosis; no stronger external-validity or causal claim','core_newpair_definition':'New pair among full four-character CPC/IPC union subclasses, compared to prior-five-year code-core grants; distinct from fine thermal-group novelty'}
    (OUT/'fine_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    core_slot_comparison(con,s,labels,a)
    paired_core_bootstrap()
    print(pd.DataFrame(summ).to_string(index=False),flush=True)
    print(options[(options.year=='all')&(options.model=='boosting')].to_string(index=False),flush=True)
    con.close()

def core_slot_comparison(con,selected,labels,history):
    """Condition on novelty-list core capacity, without using novelty to rank.

    This is a matched diagnostic. Its capacity is supplied by the novelty list,
    so it is not an independently deployed or empirically optimized rule.
    """
    pool=con.execute("""SELECT organization_id,year,patent_id,is_core,
      core_newgroup,core_newpair FROM read_parquet(?)
      WHERE relevance='core_task'""",[str(OUT/'taskpool_raw_pools_*.parquet')]).fetchdf()
    scores=con.execute("SELECT patent_id,year,score_boosting FROM read_parquet(?) WHERE year>=2018",[str(ROOT/'results/primary_v1/scores_*.parquet')]).fetchdf()
    pool=pool.merge(scores,on=['patent_id','year'],how='left',validate='many_to_one')
    pool=pool.merge(labels[['patent_id','future_external_signal_2org','future_applicant_signal_2org','future_core_signal_1patent']],on='patent_id',how='left',validate='many_to_one')
    assert not pool.score_boosting.isna().any()
    pools={(org,year):g.set_index('patent_id') for (org,year),g in pool.groupby(['organization_id','year'])}
    s=selected[selected.model=='boosting']
    records=[];lists=[]
    lmap={'general':'future_external_signal_2org','applicant':'future_applicant_signal_2org','core1':'future_core_signal_1patent'}
    for (org,year,boundary),g in s.groupby(['organization_id','year','boundary']):
        p=pools[(org,year)]
        base=g[g.q==0].set_index('patent_id')
        novel=g[g.q==.3].set_index('patent_id')
        c=int(novel.is_core.sum())
        noncore=novel[~novel.is_core].index.tolist()
        cp=p[p.is_core].reset_index()
        order=np.lexsort((cp.patent_id.to_numpy(str),-cp.score_boosting.to_numpy(float)))
        blindids=cp.iloc[order[:c]].patent_id.tolist()+noncore
        blind=p.loc[blindids].copy()
        blind['unfamiliar']=blind[boundary]
        assert len(blind)==30 and blind.index.nunique()==30
        assert int(blind.is_core.sum())==c
        assert set(blind[~blind.is_core].index)==set(noncore)
        noveltyids=set(novel.index);blindidset=set(blind.index)
        diff=len(blindidset-noveltyids)
        for name,dd in [('score_only',base),('novelty_quota_30',novel),('matched_core_slots_blind',blind)]:
            row={'organization_id':org,'year':year,'boundary':boundary,'policy':name,
                 'clean_native_thermal_history':bool(g.clean_native_thermal_history.iloc[0]),
                 'core_selected':int(dd.is_core.sum()),'noncore_selected':int((~dd.is_core).sum()),
                 'blind_vs_novel_replaced_core_n':diff,
                 'same_noncore_ids_novel_vs_blind':True,'same_core_count_novel_vs_blind':True}
            for label,col in lmap.items():
                row[label+'_T']=int(dd[col].sum())
                row[label+'_U']=int((dd[col]&dd.unfamiliar).sum())
            records.append(row)
            for pid,r in dd.iterrows():
                lists.append({'organization_id':org,'year':year,'boundary':boundary,'policy':name,
                    'patent_id':pid,'is_core':bool(r.is_core),'unfamiliar':bool(r.unfamiliar),
                    **{label+'_signal':bool(r[col]) for label,col in lmap.items()}})
    detail=pd.DataFrame(records)
    detail.to_parquet(OUT/'fine_core_slot_detail.parquet',index=False)
    pd.DataFrame(lists).to_parquet(OUT/'fine_core_slot_selected.parquet',index=False)
    summaries=[]
    for scope,dd in [('all_356',detail),('complete_cpc_no_old50',detail[detail.clean_native_thermal_history])]:
        for year,dy in [('all',dd),*list(dd.groupby('year'))]:
            for (boundary,policy),g in dy.groupby(['boundary','policy']):
                r={'scope':scope,'year':year,'boundary':boundary,'policy':policy,'situations':len(g),
                   'organizations':g.organization_id.nunique(),'core_selected':g.core_selected.mean(),
                   'noncore_selected':g.noncore_selected.mean(),
                   'blind_vs_novel_replaced_core_n':g.blind_vs_novel_replaced_core_n.mean(),
                   'fraction_blind_and_novel_differ':(g.blind_vs_novel_replaced_core_n>0).mean()}
                for label in lmap:
                    r[label+'_T']=g[label+'_T'].mean();r[label+'_U']=g[label+'_U'].mean()
                summaries.append(r)
    summary=pd.DataFrame(summaries)
    summary.to_csv(OUT/'fine_core_slot_options.csv',index=False)
    contrasts=[]
    for (scope,year,boundary),g in summary.groupby(['scope','year','boundary']):
        g=g.set_index('policy')
        r={'scope':scope,'year':year,'boundary':boundary,'situations':int(g.loc['score_only','situations'])}
        for label in lmap:
            for metric in ['T','U']:
                col=label+'_'+metric
                r[col+'_novel_minus_blind']=g.loc['novelty_quota_30',col]-g.loc['matched_core_slots_blind',col]
                r[col+'_novel_minus_score']=g.loc['novelty_quota_30',col]-g.loc['score_only',col]
                r[col+'_blind_minus_score']=g.loc['matched_core_slots_blind',col]-g.loc['score_only',col]
        contrasts.append(r)
    contrasts=pd.DataFrame(contrasts)
    contrasts.to_csv(OUT/'fine_core_slot_contrasts.csv',index=False)
    (OUT/'fine_core_slot_audit.json').write_text(json.dumps({
        'n_matched_situations_per_boundary':356,'n_core_count_mismatches':0,'n_noncore_set_mismatches':0,
        'ranking':'Original frozen boosting scores, ties by grant ID; no outcome or novelty label used',
        'candidate_pool':'The exact existing origin-specific core-task pool',
        'core_capacity':'Number of core grants in the actual novelty-quota list',
        'noncore_selections':'Exactly fixed to the actual novelty-quota list',
        'design':'Post-critique matched core-capacity diagnostic, not a standalone deployable policy or causal effect',
    },indent=2),encoding='utf-8')
    print('MATCHED_CORE_SLOT_CONTRASTS',flush=True)
    print(contrasts[contrasts.year=='all'].to_string(index=False),flush=True)

def paired_core_bootstrap():
    """Same organization-paired, situation-weighted method as decision agent."""
    detail=pd.read_parquet(OUT/'fine_core_slot_detail.parquet')
    contrasts=pd.read_csv(OUT/'fine_core_slot_contrasts.csv')
    rows=[]
    for boundary,g in detail.groupby('boundary'):
        novel=g[g.policy=='novelty_quota_30'].set_index(['organization_id','year'])
        blind=g[g.policy=='matched_core_slots_blind'].set_index(['organization_id','year'])
        assert novel.index.equals(blind.index)
        assert np.array_equal(novel.core_selected.to_numpy(),blind.core_selected.to_numpy())
        for outcome in ['general','applicant','core1']:
            diff=pd.DataFrame({'delta_T':novel[outcome+'_T']-blind[outcome+'_T'],
                'delta_U':novel[outcome+'_U']-blind[outcome+'_U']}).reset_index()
            stats=diff.groupby('organization_id')[['delta_T','delta_U']].sum().sort_index()
            stats['n']=diff.groupby('organization_id').size().reindex(stats.index)
            rng=np.random.default_rng(20260929)
            ix=rng.integers(0,len(stats),size=(2000,len(stats)))
            draws=stats.to_numpy()[ix].sum(axis=1)
            expected=contrasts[(contrasts.scope=='all_356')&(contrasts.year=='all')&(contrasts.boundary==boundary)].iloc[0]
            row={'boundary':boundary,'outcome':outcome,'comparison':'novelty_quota_30 minus matched_core_slots_blind','n_decisions':len(diff),'n_organizations':len(stats),'repeats':2000,'seed':20260929}
            for j,metric in enumerate(['delta_T','delta_U']):
                point=float(diff[metric].mean())
                expcol=outcome+'_'+('T' if metric=='delta_T' else 'U')+'_novel_minus_blind'
                assert np.isclose(point,float(expected[expcol]),rtol=0,atol=1e-12)
                dist=draws[:,j]/draws[:,2]
                row[metric]=point;row[metric+'_ci_low']=float(np.quantile(dist,.025));row[metric+'_ci_high']=float(np.quantile(dist,.975))
            rows.append(row)
    result=pd.DataFrame(rows)
    result.to_csv(OUT/'fine_core_slot_bootstrap.csv',index=False)
    (OUT/'fine_core_slot_bootstrap_notes.json').write_text(json.dumps({
        'comparisons':6,'repeats':2000,'seed':20260929,'point_audit':'PASS all12 differences reconcile to matched-summary contrasts within1e-12',
        'sampling':'Paired resampling of organizations, with replacement, retaining every selected historical situation of each organization. Differences divided by sampled count of situations. Percentile 2.5%/97.5% limits.',
        'matching':'Identical core slot count and non-core patent IDs in each novelty/blind pair',
        'limits':'Candidate patents and future outcomes are shared across organizations; only four historical environments. Organization resampling does not remove shared-candidate dependence or establish future transportability, real screening behavior, or a causal novelty effect.'
    },indent=2),encoding='utf-8')
    print('MATCHED_CORE_SLOT_PAIRED_BOOTSTRAP',flush=True)
    print(result.to_string(index=False),flush=True)

if __name__=='__main__':main()
