"""Origin-known intervention burden and boundary analysis on frozen two-task inputs.

All outputs are new v7 derivatives. No training, source downloading, or v6 edits.
"""
from __future__ import annotations
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '2'
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT/'temp')
import argparse, datetime, hashlib, json, shutil, time
import numpy as np
import pandas as pd
from scipy import sparse
from policy_core import stable_order

OUT = ROOT/'results/revision_v7'
TASKS = ('battery','electronics')
MODELS = ('boosting','ridge')
CS = (0,3,6,9,12,15,30)
CONTEXTS = ('low_0_5','middle_6_12','high_13_30')
METRICS = ('task_linked','novel_document_exposure','general_reach')
SEED = 2026100217
KEY = ['task','organization_id','year','model']

def log(event, **values):
    print(json.dumps({'event':event, **values},ensure_ascii=False),flush=True)
def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def context(c):return CONTEXTS[0] if c<=5 else CONTEXTS[1] if c<=12 else CONTEXTS[2]
def name(c,m):return f'B{c:02d}_m{m:02d}'

def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    spec=dict(schema='1.0',scope='Post hoc frozen-list analysis of previously accessible 2018–2021 outcomes, not independent confirmation or 2022 extension',
      tasks=list(TASKS),years=[2018,2019,2020,2021],rankers=list(MODELS),capacity=30,
      initial_coverage_context={'low':[0,5],'middle':[6,12],'high':[13,30]},
      policies=['U',*[name(c,0) for c in CS],name(9,3),name(6,3),name(12,3),'legacy','legacy_matched','task_title_cosine','core_priority_score'],
      legacy={'battery':'Exact recorded original_q30 and its realized-coverage matched selection; old supply-capped rule preserved','electronics':'Recorded fixed_core9_pair3 and fixed_core9; aliases of B09_m03 and B09_m00'},
      invariants=['Exact same identifiers for nonbinding within-C floor','Same noncore identifiers at fixed C','Entering_count=max(0,m-novel_count_B(C)) for feasible floor','All entries unfamiliar core and all removals familiar core at fixed C','Reconstruct all recorded U and legacy+match task/general/novel/core counts'],
      intervention_known_at_origin='r=max(0,m-novel_count_B(C)); outcome not used to define contexts or binding',
      planned_contrasts=['B09_m00 minus U','B09_m03 minus B09_m00','B12_m03 minus B06_m03','legacy minus legacy_matched','Each B(C,m0) minus U'],
      coverage_direction='Sign(C-C0): expansion, unchanged or contraction, keep every predefined C; no independent inference from stacked allocation cells',
      binding_states='all, binding, nonbinding for within-allocation contrasts; all predefined original contexts retained including empty groups',
      ratio='sum(net task/general selected-document gain)/sum(introduced document events), missing when denominator zero; not future benefit per actual hour',
      objectives=list(METRICS),combined_utility=False,
      goal_dominance='Per-situation observed choices only; mean comparison on common support of U,B9m0,B9m3,C6m3,C12m3,legacy,legacy_match,title,priority; not global Pareto or deployed policy',
      feasibility='Exact C and m, no capping. Every rejected cell retains all supply shortages; electronics prior exclusion leaves only existing admitted 1077 pools plus 5 admission failures with no cached pools',
      uncertainty={'draws_each':2000,'seed':SEED,'organization':'paired resampling with all focal organization years together; percentile ranges',
        'crossed':'Fixed lists, independent organization and patent Exp(1) product multipliers. Net gain mean denominator complete pool exposure 1/pool_n; ratio denominator introduced-event indicators',
        'scope':'Overall allocation to9, fixed-C9 novelty, fixed-m3 coverage6to12 and legacy within-match; novelty+legacy also binding-only. Sparse contexts descriptive only',
        'interpretation':'Crossed uncertainty is dependence sensitivity, no established exact coverage claim'},
      predictor_fits=0,new_data_downloads=0,account_actions=0,frozen_2022_protocol_changed=False,
      working_drive='D:',output_budget_bytes=100_000_000)
    p=OUT/'effective_intervention_protocol.json'
    if p.exists():
        old=json.loads(p.read_text(encoding='utf-8'))
        if old['specification']!=spec:raise RuntimeError('Frozen v7 protocol differs; amendment required')
    else:
        record={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'frozen':True,'specification':spec}
        with p.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2,ensure_ascii=False)
        dump(OUT/'effective_intervention_protocol_lock.json',{'file':p.name,'sha256':sha(p),'before_first_point_summary':True})
    return spec

def load(task):
    paths=[]
    def read(path,columns=None):
        paths.append(path);return pd.read_parquet(path,columns=columns)
    if task=='battery':
        p=read(ROOT/'results/revision_v3/decision_pool_exposure.parquet')
        p=p.rename(columns={'core_newpair':'novel_document','exposure':'pool_exposure'})
        ts=[]
        for y in (2018,2019,2020,2021):
            x=read(ROOT/f'results/revision_v2/taskpool_raw_pools_{y}.parquet',columns=['organization_id','year','patent_id','relevance','task_similarity'])
            ts.append(x[x.relevance=='core_task'].drop(columns='relevance'))
        p=p.merge(pd.concat(ts,ignore_index=True),on=['organization_id','year','patent_id'],validate='one_to_one')
        labs=read(ROOT/'datasets/revision_v2/task_patent_labels.parquet',columns=['patent_id','year','future_core_signal_1patent','future_external_signal_2org'])
        labs=labs.rename(columns={'future_core_signal_1patent':'task_linked','future_external_signal_2org':'general_reach'})
        hist=read(ROOT/'results/revision_v2/taskpool_raw_situations.parquet')
        hist=hist[(hist.relevance=='core_task')&hist.year.between(2018,2021)].copy()
        old=read(ROOT/'results/revision_v3/decision_selected.parquet')
        old=old[(old.boundary=='core_newpair')&old.policy.isin(['unconstrained_top30','original_q30','original_q30_matched'])].copy()
        old=old.rename(columns={'recorded_novel':'novel_document','task_signal':'task_linked','general_signal':'general_reach'})
        old['policy']=old.policy.map({'unconstrained_top30':'U','original_q30':'legacy','original_q30_matched':'legacy_matched'})
        expected=356
    else:
        p=read(ROOT/'results/revision_v3/validation_pools.parquet')
        p=p.rename(columns={'electronics_core':'is_core','newpair':'novel_document'})
        p['pool_n']=p.groupby(['organization_id','year']).patent_id.transform('size')
        p['pool_exposure']=1/p.pool_n
        labs=read(ROOT/'datasets/revision_v3/validation_labels.parquet',columns=['patent_id','year','task','general'])
        labs=labs.rename(columns={'task':'task_linked','general':'general_reach'})
        hist=read(ROOT/'results/revision_v3/validation_situations.parquet')
        old=read(ROOT/'results/revision_v3/validation_selected.parquet')
        old=old.rename(columns={'electronics_core':'is_core','newpair':'novel_document'})
        old=old.merge(labs,on=['patent_id','year'],validate='many_to_one')
        old['policy']=old.policy.map({'forecast_top30':'U','fixed_core9':'legacy_matched','fixed_core9_pair3':'legacy'})
        expected=1077
    for x in (p,labs,old):x['patent_id']=x.patent_id.astype(str)
    scoreparts=[]
    for y in (2018,2019,2020,2021):
        s=read(ROOT/f'results/primary_v1/scores_{y}.parquet',columns=['patent_id','score_boosting','score_ridge'])
        s['patent_id']=s.patent_id.astype(str);s['year']=y;scoreparts.append(s)
    scores=pd.concat(scoreparts,ignore_index=True)
    assert not scores.duplicated(['patent_id','year']).any()
    assert not labs.duplicated(['patent_id','year']).any()
    p=p.merge(scores,on=['patent_id','year'],validate='many_to_one').merge(labs,on=['patent_id','year'],validate='many_to_one')
    assert not p[['task_linked','general_reach','score_boosting','score_ridge','task_similarity','novel_document']].isna().any().any()
    assert not p.duplicated(['organization_id','year','patent_id']).any()
    assert not (p.novel_document&~p.is_core).any()
    assert len(p[['organization_id','year']].drop_duplicates())==expected
    p['task']=task;old['task']=task
    return p,hist,old,paths

def exact(score,ids,core,novel,c,m):
    reasons=[]
    if int(core.sum())<c:reasons.append('core_supply')
    if int((~core).sum())<30-c:reasons.append('noncore_supply')
    if int(novel.sum())<m:reasons.append('novel_core_supply')
    if c<m:reasons.append('floor_exceeds_core_capacity')
    if reasons:return None,reasons
    order=stable_order(score,ids);cr=order[core[order]];nr=order[~core[order]]
    blind=cr[:c]
    if int(novel[blind].sum())>=m:chosen=blind
    else:
        chosen=list(cr[novel[cr]][:m]);used=set(chosen)
        for j in cr:
            if len(chosen)>=c:break
            if int(j) not in used:chosen.append(int(j));used.add(int(j))
        chosen=np.asarray(chosen,int)
    return np.r_[chosen,nr[:30-c]],[]

def points(pilot=False):
    started=time.perf_counter();freeze();sources={};rows=[];selected=[];feas=[];checks=[];poolparts=[];admission=[];timing=[]
    policydefs=[(c,0) for c in CS]+[(9,3),(6,3),(12,3)]
    for task in TASKS:
        lt=time.perf_counter();pool,hist,old,paths=load(task)
        for path in set(paths):sources[str(path.relative_to(ROOT))]={'bytes':path.stat().st_size,'sha256':sha(path)}
        oldmaps={(o,y,m,k):g for (o,y,m,k),g in old.groupby(['organization_id','year','model','policy'],sort=False)}
        if task=='electronics':
            for r in hist.itertuples(index=False):
                if r.status!='feasible':admission.append({'task':task,'organization_id':r.organization_id,'year':r.year,'status':r.status,'pool_n':r.pool_n,'core_pool_n':r.core_pool_n,'novel_core_supply':r.newpair_core_pool_n,'not_reconstructed':True})
        groups=pool.groupby(['organization_id','year'],sort=True)
        for gi,((org,y),p) in enumerate(groups):
            if pilot and gi>=5:break
            p=p.reset_index(drop=True);ids=p.patent_id.to_numpy(str);core=p.is_core.to_numpy(bool);novel=p.novel_document.to_numpy(bool)
            pdict={v:i for i,v in enumerate(ids)}
            for model in MODELS:
                score=p['score_'+model].to_numpy(float);order=stable_order(score,ids);u=order[:30]
                c0=int(core[u].sum());ctx=context(c0)
                base={'task':task,'organization_id':str(org),'year':int(y),'model':model,'baseline_C0':c0,'core_context':ctx,'pool_n':len(p),'core_supply':int(core.sum()),'novel_core_supply':int(novel.sum())}
                sels={}
                def add(k,ss,c=-1,m=0):
                    assert len(ss)==len(set(ss))==30
                    ss=np.asarray(ss,int);sels[k]=ss
                    z={**base,'policy':k,'requested_C':c,'requested_m':m,'core_selected':int(core[ss].sum()),'novel_document_exposure':int(novel[ss].sum()),'task_linked':int(p.task_linked.to_numpy(bool)[ss].sum()),'general_reach':int(p.general_reach.to_numpy(bool)[ss].sum())}
                    rows.append(z)
                    for j in ss:selected.append({'task':task,'organization_id':str(org),'year':int(y),'model':model,'policy':k,'patent_id':str(ids[j])})
                add('U',u)
                for c,m in policydefs:
                    ss,reasons=exact(score,ids,core,novel,c,m)
                    feas.append({**base,'policy':name(c,m),'requested_C':c,'requested_m':m,'feasible':not reasons,'reasons':'|'.join(reasons) if reasons else 'ok'})
                    if ss is not None:add(name(c,m),ss,c,m)
                add('task_title_cosine',stable_order(p.task_similarity.to_numpy(float),ids)[:30])
                cr=order[core[order]];nr=order[~core[order]];nc=min(30,len(cr))
                add('core_priority_score',np.r_[cr[:nc],nr[:30-nc]])
                for k in ('legacy','legacy_matched'):
                    og=oldmaps[org,y,model,k];ss=np.asarray([pdict[str(v)] for v in og.patent_id],int);add(k,ss)
                # Actual archived counts and identifiers, not merely aggregate arithmetic.
                for k in ('U','legacy','legacy_matched'):
                    og=oldmaps[org,y,model,k];ss=sels[k]
                    checks.append({**base,'check':'archived_selection_and_counts','policy':k,'passed':set(ids[ss])==set(og.patent_id) and int(core[ss].sum())==int(og.is_core.sum()) and int(novel[ss].sum())==int(og.novel_document.sum()) and int(p.task_linked.to_numpy(bool)[ss].sum())==int(og.task_linked.sum()) and int(p.general_reach.to_numpy(bool)[ss].sum())==int(og.general_reach.sum())})
                for c,m in ((9,3),(6,3),(12,3)):
                    nk,bk=name(c,m),name(c,0)
                    if nk not in sels or bk not in sels:continue
                    a,b=sels[nk],sels[bk];enter=set(a)-set(b);leave=set(b)-set(a);r=max(0,m-int(novel[b].sum()))
                    invariant=(len(enter)==len(leave)==r and set(a[~core[a]])==set(b[~core[b]]) and all(novel[j] for j in enter) and all(not novel[j] for j in leave) and (r>0 or set(a)==set(b)))
                    checks.append({**base,'check':'within_C_origin_burden','policy':nk,'r_at_origin':r,'entering_count':len(enter),'nonbinding':r==0,'passed':invariant})
                if task=='electronics':
                    for new,prior in ((name(9,0),'legacy_matched'),(name(9,3),'legacy')):
                        checks.append({**base,'check':'electronics_current_rule_recovery','policy':new,'passed':set(sels[new])==set(sels[prior])})
                else:
                    a,b=sels['legacy'],sels['legacy_matched']
                    checks.append({**base,'check':'authentic_realized_coverage_match','policy':'legacy','passed':int(core[a].sum())==int(core[b].sum()) and set(a[~core[a]])==set(b[~core[b]])})
            poolparts.append(p[['task','organization_id','year','patent_id','is_core','novel_document','task_similarity','score_boosting','score_ridge','task_linked','general_reach','pool_exposure']])
        timing.append({'task':task,'load_and_point_seconds':time.perf_counter()-lt,'processed_situations':min(5,groups.ngroups) if pilot else groups.ngroups})
        log('TASK_POINTS',task=task,policy_rows=len(rows),pilot=pilot)
    assert all(r['passed'] for r in checks)
    if pilot:
        audit={'pilot':True,'situations_per_task':5,'seconds':time.perf_counter()-started,'checks':len(checks),'checks_passed':True,'D_free_bytes':shutil.disk_usage(ROOT).free,'predictor_fits':0}
        dump(OUT/'effective_intervention_pilot.json',audit);log('PILOT_PASS',**audit);return
    detail=pd.DataFrame(rows);sels=pd.DataFrame(selected);pools=pd.concat(poolparts,ignore_index=True)
    detail.to_parquet(OUT/'effective_policy_detail.parquet',index=False)
    sels.to_parquet(OUT/'effective_selected.parquet',index=False)
    pools.to_parquet(OUT/'effective_pools.parquet',index=False)
    pd.DataFrame(feas).to_csv(OUT/'effective_feasibility.csv',index=False)
    pd.DataFrame(checks).to_csv(OUT/'effective_recovery_checks.csv',index=False)
    pd.DataFrame(admission).to_csv(OUT/'effective_existing_admission_failures.csv',index=False)
    dump(OUT/'effective_source_manifest.json',sources)
    audit={'status':'PASS','predictor_fits':0,'new_downloads':0,'policy_rows':len(detail),'selected_events':len(sels),'pool_exposures':len(pools),'task_situations':detail[detail.policy=='U'].groupby('task').size().div(2).astype(int).to_dict(),'checks':len(checks),'timing':timing,'point_seconds':time.perf_counter()-started,'D_free_bytes':shutil.disk_usage(ROOT).free,'2022_protocol_unchanged':True}
    dump(OUT/'effective_point_audit.json',audit);log('POINT_PASS',**audit)
    summarize()

def summarize():
    d=pd.read_parquet(OUT/'effective_policy_detail.parquet');s=pd.read_parquet(OUT/'effective_selected.parquet');p=pd.read_parquet(OUT/'effective_pools.parquet')
    label=p.set_index(['task','organization_id','year','patent_id'])
    s=s.merge(p[['task','organization_id','year','patent_id',*METRICS[:1],'general_reach','novel_document']],on=['task','organization_id','year','patent_id'],validate='many_to_one')
    defs=[('coverage_to9',name(9,0),'U'),('within_C9_floor3',name(9,3),name(9,0)),('coverage6_to12_fixed_floor3',name(12,3),name(6,3)),('legacy_within_match','legacy','legacy_matched')]+[(f'coverage_to_C{c:02d}',name(c,0),'U') for c in CS]
    contrast=[];events=[];selection_groups={key:q for key,q in s.groupby(KEY,sort=False)}
    for (task,org,y,model),q in d.groupby(KEY,sort=False):
        by=q.set_index('policy');sx=selection_groups[(task,org,y,model)]
        sm={k:g.set_index('patent_id') for k,g in sx.groupby('policy',sort=False)}
        for comp,a,b in defs:
            if a not in by.index or b not in by.index:continue
            aa,bb=by.loc[a],by.loc[b];ia,ib=set(sm[a].index),set(sm[b].index);ent,lv=ia-ib,ib-ia
            r=len(ent);same=int(aa.core_selected)==int(bb.core_selected)
            originr=max(0,3-int(bb.novel_document_exposure)) if comp=='within_C9_floor3' else r
            cr=int(aa.core_selected-bb.core_selected)
            z={'task':task,'organization_id':org,'year':y,'model':model,'comparison':comp,'alternative':a,'reference':b,'baseline_C0':int(aa.baseline_C0),'core_context':aa.core_context,'delta_core_positions':cr,'coverage_direction':'expansion' if cr>0 else 'contraction' if cr<0 else 'unchanged','entering_count':r,'leaving_count':len(lv),'origin_r':originr,'binding':bool(r),'fixed_coverage':same,'reference_unfamiliar_documents':int(bb.novel_document_exposure)}
            for m in METRICS:z['delta_'+m]=int(aa[m]-bb[m])
            if comp=='within_C9_floor3':assert r==originr
            if comp in ('within_C9_floor3','legacy_within_match'):
                assert same and ia.symmetric_difference(ib)==ent|lv
                assert int(aa.novel_document_exposure-bb.novel_document_exposure)==r
            contrast.append(z)
            for sign,ids in ((1,ent),(-1,lv)):
                for pid in ids:
                    row=label.loc[(task,org,y,pid)]
                    events.append({'task':task,'organization_id':org,'year':y,'model':model,'comparison':comp,'patent_id':pid,'sign':sign,'task_linked':int(row.task_linked),'general_reach':int(row.general_reach),'introduced':int(sign==1)})
    cd=pd.DataFrame(contrast);ev=pd.DataFrame(events)
    cd.to_parquet(OUT/'effective_contrast_detail.parquet',index=False)
    ev.to_parquet(OUT/'effective_signed_events.parquet',index=False)
    summaries=[]
    wanted=['coverage_to9','within_C9_floor3','coverage6_to12_fixed_floor3','legacy_within_match']
    for task in TASKS:
      for model in MODELS:
        for comp in wanted:
          for ctx in ('all',*CONTEXTS):
            for state in ('all','binding','nonbinding') if comp in ('within_C9_floor3','legacy_within_match') else ('all',):
                q=cd[(cd.task==task)&(cd.model==model)&(cd.comparison==comp)]
                if ctx!='all':q=q[q.core_context==ctx]
                if state!='all':q=q[q.binding==(state=='binding')]
                out={'task':task,'model':model,'comparison':comp,'core_context':ctx,'state':state,'n_situations':len(q),'n_organizations':q.organization_id.nunique(),'n_changed':int(q.binding.sum()),'n_binding':int(q.binding.sum()) if comp in ('within_C9_floor3','legacy_within_match') else None,'total_entering_events':int(q.entering_count.sum()),'mean_entering':float(q.entering_count.mean()) if len(q) else None}
                for m in METRICS:
                    v=q['delta_'+m];out.update({f'mean_delta_{m}':float(v.mean()) if len(q) else None,f'total_delta_{m}':int(v.sum()),f'{m}_wins':int((v>0).sum()),f'{m}_ties':int((v==0).sum()),f'{m}_losses':int((v<0).sum()),f'{m}_net_gain_per_entered_document':float(v.sum()/q.entering_count.sum()) if q.entering_count.sum() else None})
                summaries.append(out)
    pd.DataFrame(summaries).to_csv(OUT/'effective_contrasts.csv',index=False)
    ps=d.groupby(['task','model','policy']).agg(n_situations=('year','size'),n_organizations=('organization_id','nunique'),mean_core=('core_selected','mean'),**{'mean_'+m:(m,'mean') for m in METRICS}).reset_index()
    ps.to_csv(OUT/'effective_policy_summary.csv',index=False)
    dx=[]
    coverage=cd[cd.comparison.str.startswith('coverage_to_C')]
    for task in TASKS:
      for model in MODELS:
        for c in CS:
          for direction in ('expansion','unchanged','contraction'):
            q=coverage[(coverage.task==task)&(coverage.model==model)&(coverage.comparison==f'coverage_to_C{c:02d}')&(coverage.coverage_direction==direction)]
            z={'task':task,'model':model,'C':c,'direction':direction,'n_situations':len(q),'n_organizations':q.organization_id.nunique()}
            for m in METRICS:
                v=q['delta_'+m];z.update({'mean_delta_'+m:float(v.mean()) if len(q) else None,m+'_wins':int((v>0).sum()),m+'_ties':int((v==0).sum()),m+'_losses':int((v<0).sum())})
            dx.append(z)
    pd.DataFrame(dx).to_csv(OUT/'effective_coverage_directions.csv',index=False)
    # Dependence-aware reading: repeated C values are not independent observations.
    pooled=[]
    for (task,model,direction),q in coverage.groupby(['task','model','coverage_direction']):
        pooled.append({'task':task,'model':model,'direction':direction,'repeated_allocation_cells':len(q),'distinct_situations':len(q[['organization_id','year']].drop_duplicates()),'organizations':q.organization_id.nunique(),**{'mean_delta_'+m:float(q['delta_'+m].mean()) for m in METRICS}})
    pd.DataFrame(pooled).to_csv(OUT/'effective_coverage_directions_pooled_descriptive.csv',index=False)
    gs=['U',name(9,0),name(9,3),name(6,3),name(12,3),'legacy','legacy_matched','task_title_cosine','core_priority_score']
    gr=[];cm=[]
    for (task,model),q in d.groupby(['task','model'],sort=False):
        common=[]
        for (org,y),x in q.groupby(['organization_id','year'],sort=False):
            xx=x[x.policy.isin(gs)]
            v=xx[list(METRICS)].to_numpy()
            for j,row in enumerate(xx.itertuples(index=False)):
                dominated=np.any(np.all(v>=v[j],axis=1)&np.any(v>v[j],axis=1))
                gr.append({'task':task,'organization_id':org,'year':y,'model':model,'policy':row.policy,'available_policy_count':len(xx),'dominated_by_available_observed_choice':bool(dominated)})
            if set(gs)<=set(xx.policy):common.append(xx)
        if common:
            cc=pd.concat(common,ignore_index=True)
            means=cc.groupby('policy')[list(METRICS)].mean().reindex(gs)
            v=means.to_numpy()
            for j,k in enumerate(gs):
                cm.append({'task':task,'model':model,'policy':k,'common_situations':len(cc)//len(gs),'common_organizations':cc.organization_id.nunique(),'dominated_mean_on_common_support':bool(np.any(np.all(v>=v[j],axis=1)&np.any(v>v[j],axis=1))),**{'mean_'+m:float(means.loc[k,m]) for m in METRICS}})
    pd.DataFrame(gr).to_csv(OUT/'effective_observed_goal_dominance.csv',index=False)
    pd.DataFrame(cm).to_csv(OUT/'effective_common_support_goals.csv',index=False)
    verify()
    x=pd.read_csv(OUT/'effective_contrasts.csv');log('CORE_SUMMARIES',values=x[(x.core_context=='all')&x.comparison.isin(['coverage_to9','within_C9_floor3'])].to_dict('records'))

def verify():
    d=pd.read_parquet(OUT/'effective_policy_detail.parquet');s=pd.read_parquet(OUT/'effective_selected.parquet');p=pd.read_parquet(OUT/'effective_pools.parquet');c=pd.read_parquet(OUT/'effective_contrast_detail.parquet');e=pd.read_parquet(OUT/'effective_signed_events.parquet')
    checks=[]
    def ck(k,ok,detail=None):
        checks.append({'check':k,'passed':bool(ok),'detail':detail})
        if not ok:raise AssertionError(k)
    ck('unique_policy_rows',not d.duplicated(KEY+['policy']).any())
    ck('unique_selected_rows',not s.duplicated(KEY+['policy','patent_id']).any())
    cnt=s.groupby(KEY+['policy']).size();ck('thirty_documents_every_policy',bool((cnt==30).all()))
    joined=s.merge(p[['task','organization_id','year','patent_id','task_linked','general_reach','novel_document','is_core']],on=['task','organization_id','year','patent_id'],validate='many_to_one')
    sums=joined.groupby(KEY+['policy']).agg(task_linked=('task_linked','sum'),general_reach=('general_reach','sum'),novel_document_exposure=('novel_document','sum'),core_selected=('is_core','sum'))
    ref=d.set_index(KEY+['policy']).loc[sums.index]
    for z in (*METRICS,'core_selected'):ck('selected_sum_recovery_'+z,np.array_equal(ref[z].to_numpy(),sums[z].to_numpy()))
    for (task,model,comp),q in c.groupby(['task','model','comparison']):
        ev=e[(e.task==task)&(e.model==model)&(e.comparison==comp)]
        for z in ('task_linked','general_reach'):ck(f'signed_event_recovery_{task}_{model}_{comp}_{z}',int((ev.sign*ev[z]).sum())==int(q['delta_'+z].sum()))
        ck(f'entering_event_recovery_{task}_{model}_{comp}',int(ev.introduced.sum())==int(q.entering_count.sum()))
    nc=c[(c.comparison=='within_C9_floor3')&~c.binding]
    ck('nonbinding_exact_identical_selection',bool((nc.entering_count==0).all()))
    ck('nonbinding_all_three_zero',bool((nc[['delta_'+m for m in METRICS]]==0).all().all()))
    bc=c[c.comparison=='within_C9_floor3'];ck('origin_r_equals_entering',np.array_equal(bc.origin_r,bc.entering_count))
    ck('within_C9_exposure_gain_equals_interventions',np.array_equal(bc.delta_novel_document_exposure,bc.entering_count))
    for task,n in [('battery',356),('electronics',1077)]:
      for model in MODELS:ck('baseline_count_'+task+'_'+model,len(d[(d.task==task)&(d.model==model)&(d.policy=='U')])==n)
    old=pd.read_csv(OUT/'effective_recovery_checks.csv');ck('archived_recovery_all',bool(old.passed.all()),len(old))
    # Historical paper numerators explicitly recovered without converting events to inventions.
    sums=d[(d.task=='battery')&d.policy.isin(['U','legacy','legacy_matched'])].groupby(['model','policy']).task_linked.sum()
    for model,expected in [('boosting',(921,1436,1418)),('ridge',(1050,1544,1462))]:
      for k,v in zip(['U','legacy','legacy_matched'],expected):ck('original_task_numerator_'+model+'_'+k,int(sums.loc[model,k])==v)
    dump(OUT/'effective_machine_checks.json',{'status':'PASS','checks_passed':len(checks),'checks':checks,'recovery_row_count':len(old),'scope':'Exact old selections and new signed contributions; no independent new outcome evidence'})
    log('MACHINE_CHECKS_PASS',checks=len(checks),archived_and_invariant_rows=len(old))

def bootstrap(repeats=2000):
    started=time.perf_counter();c=pd.read_parquet(OUT/'effective_contrast_detail.parquet');e=pd.read_parquet(OUT/'effective_signed_events.parquet');p=pd.read_parquet(OUT/'effective_pools.parquet')
    wanted=['coverage_to9','within_C9_floor3','coverage6_to12_fixed_floor3','legacy_within_match'];rows=[];actual=[]
    for task in TASKS:
        pp=p[p.task==task];orgs=sorted(pp.organization_id.unique());pats=sorted(pp.patent_id.unique());oi={v:i for i,v in enumerate(orgs)};pi={v:i for i,v in enumerate(pats)};no,npats=len(orgs),len(pats)
        descriptors=[];exposures=[];exposure_cache={}
        for model in MODELS:
          for comp in wanted:
            for state in ('all','binding') if comp in ('within_C9_floor3','legacy_within_match') else ('all',):
                q=c[(c.task==task)&(c.model==model)&(c.comparison==comp)]
                if state=='binding':q=q[q.binding]
                if not len(q):continue
                keys=q[['organization_id','year']].drop_duplicates();keysig=tuple(sorted(map(tuple,keys.to_numpy())))
                ee=e[(e.task==task)&(e.model==model)&(e.comparison==comp)].merge(keys,on=['organization_id','year'],validate='many_to_one')
                rr=ee.organization_id.map(oi).to_numpy();cc=ee.patent_id.map(pi).to_numpy();sig=ee.sign.to_numpy(float)
                D=[sparse.csr_matrix((sig*ee[z].to_numpy(float),(rr,cc)),shape=(no,npats)) for z in ('task_linked','general_reach')]
                R=sparse.csr_matrix((ee.introduced.to_numpy(float),(rr,cc)),shape=(no,npats))
                N=keys.organization_id.map(oi).value_counts().reindex(range(no),fill_value=0).to_numpy(float)
                od=np.vstack([np.asarray(dm.sum(axis=1)).ravel() for dm in D]);oring=np.asarray(R.sum(axis=1)).ravel()
                if keysig not in exposure_cache:
                    px=pp.merge(keys,on=['organization_id','year'],validate='many_to_one');er=px.organization_id.map(oi).to_numpy();ec=px.patent_id.map(pi).to_numpy()
                    exposure_cache[keysig]=len(exposures);exposures.append(sparse.csr_matrix((px.pool_exposure.to_numpy(float),(er,ec)),shape=(no,npats)))
                ix=exposure_cache[keysig]
                for j,z in enumerate(('task_linked','general_reach')):assert np.isclose(od[j].sum()/len(keys),q['delta_'+z].mean(),atol=1e-12)
                descriptors.append(dict(task=task,model=model,comparison=comp,state=state,n_situations=len(keys),n_organizations=int((N>0).sum()),n_entering=int(oring.sum()),D=D,R=R,N=N,od=od,oring=oring,exposure_index=ix,point=od.sum(axis=1)/len(keys)))
        rng=np.random.default_rng(SEED+(0 if task=='battery' else 1));nd=len(descriptors)
        orgvals=np.full((repeats,nd,2),np.nan);crossvals=np.full_like(orgvals,np.nan);org_ratios=np.full_like(orgvals,np.nan);cross_ratios=np.full_like(orgvals,np.nan)
        for b in range(repeats):
            wo=np.bincount(rng.integers(0,no,no),minlength=no);xo=rng.exponential(size=no);xp=rng.exponential(size=npats)
            dens=[float(xo@(ee@xp)) for ee in exposures]
            for j,v in enumerate(descriptors):
                dn=float(wo@v['N']);num=v['od']@wo
                if dn>0:orgvals[b,j]=num/dn
                cxnum=np.asarray([float(xo@(dm@xp)) for dm in v['D']]);crossvals[b,j]=cxnum/dens[v['exposure_index']]
                rd=float(wo@v['oring']);xr=float(xo@(v['R']@xp))
                if rd>0:org_ratios[b,j]=num/rd
                if xr>0:cross_ratios[b,j]=cxnum/xr
            if (b+1)%500==0:log('BOOTSTRAP_PROGRESS',task=task,draws=b+1,total=repeats)
        for j,v in enumerate(descriptors):
          for zi,z in enumerate(('task_linked','general_reach')):
            for method,vals in [('paired_organization_percentile',orgvals[:,j,zi]),('crossed_org_patent_fixed_list_sensitivity',crossvals[:,j,zi])]:
                lo,hi=np.nanquantile(vals,[.025,.975]);rows.append({k:v[k] for k in ('task','model','comparison','state','n_situations','n_organizations','n_entering')}|{'estimand':'mean_net_gain_per_list','metric':z,'method':method,'point':float(v['point'][zi]),'lower':float(lo),'upper':float(hi),'finite_draws':int(np.isfinite(vals).sum()),'draws':repeats,'seed':SEED+(0 if task=='battery' else 1)})
            if v['n_entering'] and v['comparison'] in ('within_C9_floor3','legacy_within_match'):
              for method,vals in [('paired_organization_percentile',org_ratios[:,j,zi]),('crossed_org_patent_fixed_list_sensitivity',cross_ratios[:,j,zi])]:
                lo,hi=np.nanquantile(vals,[.025,.975]);rows.append({k:v[k] for k in ('task','model','comparison','state','n_situations','n_organizations','n_entering')}|{'estimand':'net_gain_per_introduced_document_event','metric':z,'method':method,'point':float(v['od'][zi].sum()/v['n_entering']),'lower':float(lo),'upper':float(hi),'finite_draws':int(np.isfinite(vals).sum()),'draws':repeats,'seed':SEED+(0 if task=='battery' else 1)})
        actual.append({'task':task,'descriptors':nd,'unique_pool_exposure_denominators':len(exposures),'organizations':no,'unique_patents':npats})
    pd.DataFrame(rows).to_csv(OUT/'effective_uncertainty.csv',index=False)
    dump(OUT/'effective_uncertainty_notes.json',{'methods':['paired organization resampling','independent organization×patent Exp(1) product multiplier sensitivity'],'draws_each':repeats,'mean_denominator':'sum origin-organization weight × patent weight × complete-pool exposure 1/pool_n for included fixed situations','ratio_denominator':'sum origin-organization weight × patent weight × introduced-document-event indicator; numerator includes both entering and removed signed links','ratio_interpretation':'Signed net-yield ratio, not probability. Crossed weights differ for introduced and removed patent identities, so sensitivity endpoints may exceed -1 or 1.','fixed_binding_groups':'Origin-known B(C) unfamiliar counts and fixed list exchange only; no outcome-selected subgroup','ratio_zero_draws':'Excluded only when bootstrap introduced-event denominator is zero; finite counts retained','ranges':'Crossed ranges are fixed-list dependence sensitivities, not validated exact nominal confidence intervals; no causal or new-sample claim','runtime_seconds':time.perf_counter()-started,'actual':actual})
    log('BOOTSTRAP_PASS',seconds=time.perf_counter()-started,rows=len(rows))

def md(df):
    def fmt(v):
        if pd.isna(v):return '—'
        if isinstance(v,(float,np.floating)):return f'{v:.6f}'
        return str(v).replace('|','\\|')
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))

def report():
    a=json.loads((OUT/'effective_point_audit.json').read_text(encoding='utf-8'));d=pd.read_parquet(OUT/'effective_policy_detail.parquet');c=pd.read_csv(OUT/'effective_contrasts.csv');f=pd.read_csv(OUT/'effective_feasibility.csv');ch=pd.read_csv(OUT/'effective_recovery_checks.csv')
    t='# v7 Origin-known intervention burden and boundary evidence\n\n'
    t+='Route: SSCI technology-management empirical decision-rule evaluation. Primary standard: observable contribution to assessing a combined algorithmic recommendation. No strict corporate causal identification or algorithm leaderboard is claimed.\n\n'
    t+='本轮只重排已有2018–2021两任务池及冻结排序；所有结局此前可访问并已在旧分析中使用。分析协议在本轮summary前固定，但该工作是事后探索，不能称独立检验、预注册验证或已执行2022方案。旧2022协议完全不修改。\n\n'
    t+='## Actual execution\n\n'+json.dumps(a,indent=2,ensure_ascii=False)+'\n\n'
    t+='全部U的core、unfamiliar、task、general值及identifier与旧选中记录精确复现；battery另精确恢复实际supply-capped旧规则及其realized-coverage match，electronics旧规则为固定C9m3。\n\n'
    counts=d[d.policy=='U'].groupby(['task','model','core_context']).agg(n=('year','size'),organizations=('organization_id','nunique'),mean_C0=('baseline_C0','mean')).reset_index()
    t+='## Original coverage contexts\n\n'+md(counts)+'\n\n'
    cols=['task','model','comparison','state','n_situations','n_organizations','n_binding','total_entering_events','mean_delta_task_linked','task_linked_wins','task_linked_ties','task_linked_losses','task_linked_net_gain_per_entered_document','mean_delta_general_reach','general_reach_net_gain_per_entered_document','mean_delta_novel_document_exposure']
    t+='## Overall and binding-only contrasts\n\n'+md(c[c.core_context=='all'][cols])+'\n\n'
    grp=['task','model','comparison','core_context','state','n_situations','n_organizations','mean_delta_task_linked','task_linked_wins','task_linked_ties','task_linked_losses','mean_delta_general_reach','mean_delta_novel_document_exposure']
    t+='## Every initial coverage context\n\n'+md(c[(c.core_context!='all')&c.comparison.isin(['coverage_to9','within_C9_floor3'])][grp])+'\n\n'
    t+='## Feasibility and implementation\n\n'+md(f.groupby(['task','model','policy']).agg(eligible_cell_count=('feasible','size'),feasible=('feasible','sum')).reset_index())+'\n\n'
    t+=f"{len(ch)} exact archived/invariant rows passed. For N(C,m), r=max(0,m−unfamiliar_count_B(C)) equals entering_count. At fixed C, same noncore IDs remain, introduced documents are unfamiliar core and removed documents are familiar core. Nonbinding interventions keep exact IDs and all objective values. Their zero effect is mechanical; outcomes for binding exchanges are empirical.\n\n"
    t+='净gain/introduced_document_event是所有进入事件上task/general净改变量，分子含进入与移除的文档；不是新增条目自身成功率，不是独立发明，更不是阅读小时收益。无进入时不报ratio。Crossed权重对进入和移除的不同专利分别赋权，该带符号净yield比值的敏感性区间可以超出±1，不能将其解释为概率区间。n_binding只用于固定覆盖的新颖交换；coverage行仅报告n_changed而不称新颖floor binding。\n\n'
    t+='## Predetermined allocation levels and direction\n\n'+md(pd.read_csv(OUT/'effective_coverage_directions_pooled_descriptive.csv'))+'\n\n'
    t+='所有C=0/3/6/9/12/15/30、m=0的逐C方向组及空组保留effective_coverage_directions.csv。同一情景在各C重复，pooled cell数不是独立案例；不按结果挑C。C6→12固定m3始终增加6核心位置，不因baseline C0高而预测负号。P1/P2检验用B9−U的原C0组，不能把group定义写成结局改善与否。\n\n'
    t+='## Separate goals and observed-choice domination\n\n'+md(pd.read_csv(OUT/'effective_common_support_goals.csv'))+'\n\n'
    t+='effective_observed_goal_dominance.csv为每个情景可行的预定政策集合之内的三目标支配。共同比较的均值只用所有九种预定policy都可行的共同情景，避免different support伪造支配。此有限选择集合不证明全局Pareto前沿、最佳部署或商业价值。\n\n'
    if (OUT/'effective_uncertainty.csv').exists():
        t+='## Paired and crossed uncertainty\n\n'+md(pd.read_csv(OUT/'effective_uncertainty.csv'))+'\n\n'+(OUT/'effective_uncertainty_notes.json').read_text(encoding='utf-8')+'\n\n'
    t+='组织跨年保留为一组；共享专利用固定list的organization×patent product multiplier敏感性。binding-only样本根据origin数据定义，不依据结局。Sparse context只描述，没有验证因果moderation，也没有替代新样本边界评价。\n'
    (ROOT/'research/revision_v7_effective_intervention.md').write_text(t,encoding='utf-8');log('REPORT_READY',path=str(ROOT/'research/revision_v7_effective_intervention.md'))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--points',action='store_true');ap.add_argument('--bootstrap',action='store_true');ap.add_argument('--report',action='store_true');args=ap.parse_args()
    if args.pilot:points(True)
    elif args.points:points(False);report()
    elif args.bootstrap:bootstrap();report()
    elif args.report:report()
    else:points(False);bootstrap();report()
