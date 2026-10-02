"""Focused supplementary checks on already exposed frozen archive; no model fitting.

Joint family-wise ranges, paired budget/floor changes, matched random references,
and complete 2018–2019 2/3/5-grant-year outcomes. All writes stay in new v8 outputs.
"""
from __future__ import annotations
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='2'
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'temp')
import argparse,datetime,hashlib,json,shutil,time,sys
from importlib import metadata
import duckdb
import numpy as np
import pandas as pd
from scipy import sparse
from policy_core import stable_order

OUT=ROOT/'results/revision_v8'
TASKS=('battery','electronics');MODELS=('boosting','ridge')
METRICS=('task_linked','novel_document_exposure','general_reach')
SEED=2026100281
KEY=['task','organization_id','year','model']
CONFIGS=[('capacity_absolute',k,9,3) for k in (20,30,50)]+[('capacity_fractional',20,6,2),('capacity_fractional',30,9,3),('capacity_fractional',50,15,5)]+[('floor_at9',30,9,m) for m in (0,3,6,9)]+[('allocation_floor3',30,c,3) for c in (3,9,15)]

def log(event,**v):print(json.dumps({'event':event,**v},ensure_ascii=False),flush=True)
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def ident(axis,k,c,m):return f'{axis}_K{k:02d}_C{c:02d}_m{m:02d}'

def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    spec={'status':'Supplementary post hoc checks on archive and outcomes already examined; no independent confirmation, pre-registration or 2022 analysis',
      'tasks':list(TASKS),'rankers':list(MODELS),'years':[2018,2019,2020,2021],
      'configurations':[{'axis':a,'K':k,'C':c,'m':m} for a,k,c,m in CONFIGS],
      'pairing':'Each configuration has unrestricted U(K), score-only B(K,C), and same-C/same-noncore N(K,C,m). No arbitrary Cartesian grid.',
      'budget_axes':'Fixed C9,m3 across K20/30/50; separately fixed .30 core share and .10 unfamiliar minimum, exact 6/2,9/3,15/5. These estimate distinct changes.',
      'capacity_common_support':'Within every task/ranker/axis, use situations feasible for every listed configuration before comparing the parameter curve. Report individual feasible support as well.',
      'strict_feasibility':'Keep candidate, core, noncore, unfamiliar and m>C failures; never cap strict rules. Existing electronic admission failures remain original exclusions.',
      'existing_allocation_values':'V7 already gives C6/12 at m3 and all C0/3/6/9/12/15/30 m0. New focal allocation comparisons add only C3/15 m3 with C9 anchor.',
      'inference_family':'Exactly four 3-year task-link mean contrasts N(30,9,3)-B(30,9): two tasks by two rankers, all feasible fixed pools',
      'inference':{'draws_each':4000,'seed':SEED,'organization':'Shared global normalized organization keys per draw; all years/tasks/rankers retain shared sampled counts',
        'crossed':'Shared global organization and patent Exp(1) multipliers per draw. Fixed-list signed numerators; complete-pool 1/pool_n denominators.',
        'simultaneous_range':'Centered maximum standardized absolute bootstrap departure over four contrasts; common 95th percentile critical value times each empirical bootstrap SD. No p-values or guarantees of exact nominal coverage.',
        'scope':'Organization ranges are approximate bootstrap simultaneous intervals; crossed counterparts are simultaneous fixed-list dependence sensitivities.'},
      'random_reference':{'K':30,'C':9,'m_min':3,'exact_matching':'Same noncore IDs and same actual unfamiliar-core count as deterministic N9m3; uniform sampling without replacement separately among unfamiliar and familiar core candidates',
        'main':'Analytic exact expected task/general yield under the matched uniform reference',
        'monte_carlo_seeds':100,'interpretation':'Descriptive random reference for ranking within feasible composition, not causal placebo. Seeds add no independent organizations.'},
      'window_check':{'origins':[2018,2019],'grant_year_windows':[2,3,5],'lists':'Fixed old U/B9m0/N9m3/legacy/match lists; identical origin situations for all windows',
        'maturity':'Release ends2024-12-31; 2020/2021 excluded from every horizon comparison including shorter horizons, so all five-year windows complete',
        'filters':'Original known citing-owner, no owner overlap, no same application, future citing-grant dates; original CPC/IPC task flags',
        'mandatory_validation':'New 3-year task/general indicators equal every old label for the included candidate IDs; five-year battery also matches old cached five-year labels'},
      'predictor_fits':0,'new_downloads':0,'new_account_actions':0,'frozen_2022_protocol_mutation':False,'output_limit_bytes':1_000_000_000,'working_drive':'D:'}
    path=OUT/'sensitivity_protocol.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))['specification']!=spec:raise RuntimeError('Frozen v8 specification differs; preserve and amend explicitly')
    else:
        with path.open('x',encoding='utf-8') as f:json.dump({'frozen':True,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'specification':spec},f,indent=2,ensure_ascii=False)
        dump(OUT/'sensitivity_protocol_lock.json',{'sha256':sha(path),'before_new_supplementary_summaries':True})
    return spec

def pools():
    p=pd.read_parquet(ROOT/'results/revision_v7/effective_pools.parquet')
    p['patent_id']=p.patent_id.astype(str)
    assert not p.duplicated(['task','organization_id','year','patent_id']).any()
    assert not p[['score_boosting','score_ridge','task_linked','general_reach','novel_document','is_core']].isna().any().any()
    return p

def exact(score,ids,core,novel,k,c,m):
    reason=[]
    if len(ids)<k:reason.append('candidate_supply')
    if int(core.sum())<c:reason.append('core_supply')
    if int((~core).sum())<k-c:reason.append('noncore_supply')
    if int(novel.sum())<m:reason.append('unfamiliar_core_supply')
    if m>c:reason.append('minimum_exceeds_core_allocation')
    if c>k:reason.append('core_allocation_exceeds_list_budget')
    if reason:return None,reason
    order=stable_order(score,ids);cr=order[core[order]];nr=order[~core[order]];b=cr[:c]
    if int(novel[b].sum())>=m:cc=b
    else:
        cc=list(cr[novel[cr]][:m]);used=set(cc)
        for j in cr:
            if len(cc)>=c:break
            if int(j) not in used:cc.append(int(j));used.add(int(j))
        cc=np.asarray(cc,int)
    return np.r_[cc,nr[:k-c]],[]

def budget(pilot=False):
    start=time.perf_counter();freeze();p=pools();old=pd.read_parquet(ROOT/'results/revision_v7/effective_selected.parquet')
    old=old[old.policy.isin(['U','B09_m00','B09_m03'])]
    oldmap={key:set(g.patent_id.astype(str)) for key,g in old.groupby(KEY+['policy'])}
    rows=[];sels=[];failed=[];checks=[]
    for task in TASKS:
      g=p[p.task==task].groupby(['organization_id','year'],sort=True)
      for gi,((org,y),q) in enumerate(g):
        if pilot and gi>=5:break
        q=q.reset_index(drop=True);ids=q.patent_id.to_numpy(str);core=q.is_core.to_numpy(bool);nov=q.novel_document.to_numpy(bool)
        yy={z:q[z].to_numpy(int) for z in ('task_linked','general_reach')}
        for model in MODELS:
          score=q['score_'+model].to_numpy(float);order=stable_order(score,ids)
          for axis,k,c,m in CONFIGS:
            case=ident(axis,k,c,m);base={'task':task,'organization_id':org,'year':int(y),'model':model,'axis':axis,'configuration':case,'K':k,'C':c,'m':m,'pool_n':len(q),'core_supply':int(core.sum()),'unfamiliar_core_supply':int(nov.sum())}
            b,br=exact(score,ids,core,nov,k,c,0);n,nr=exact(score,ids,core,nov,k,c,m);u=order[:k]
            failed.append({**base,'B_feasible':b is not None,'N_feasible':n is not None,'B_reasons':'|'.join(br) if br else 'ok','N_reasons':'|'.join(nr) if nr else 'ok'})
            def add(policy,ss):
                assert len(ss)==len(set(ss))==k
                row={**base,'policy':policy,'core_selected':int(core[ss].sum()),'novel_document_exposure':int(nov[ss].sum())}
                for z in yy:row[z]=int(yy[z][ss].sum())
                rows.append(row)
                if not pilot:
                    for j in ss:sels.append({**{v:base[v] for v in KEY},'configuration':case,'policy':policy,'patent_id':str(ids[j])})
            add('U',u)
            if b is not None:add('B',b)
            if n is not None:add('N',n)
            if b is not None and n is not None:
                d=max(0,m-int(nov[b].sum()));ent=set(n)-set(b);leave=set(b)-set(n)
                checks.append({**base,'check':'origin_shortfall_and_same_noncore','passed':len(ent)==len(leave)==d and set(n[~core[n]])==set(b[~core[b]]) and all(nov[j] for j in ent) and all(not nov[j] for j in leave),'d':d,'entering':len(ent)})
            if k==30 and c==9 and m==3:
                for pol,ss,v7pol in [('U',u,'U'),('B',b,'B09_m00'),('N',n,'B09_m03')]:
                    checks.append({**base,'check':'K30_original_ID_recovery_'+pol,'passed':ss is not None and set(ids[ss])==oldmap[task,org,y,model,v7pol]})
      log('BUDGET_TASK_READY',task=task,pilot=pilot,rows=len(rows))
    assert all(v['passed'] for v in checks)
    if pilot:
        info={'status':'PASS','pilot_situations_per_task':5,'seconds':time.perf_counter()-start,'checks':len(checks),'predictor_fits':0,'D_free_bytes':shutil.disk_usage(ROOT).free}
        dump(OUT/'sensitivity_pilot.json',info);log('PILOT_PASS',**info);return
    d=pd.DataFrame(rows);s=pd.DataFrame(sels);f=pd.DataFrame(failed)
    d.to_parquet(OUT/'budget_policy_detail.parquet',index=False);s.to_parquet(OUT/'budget_selected.parquet',index=False);f.to_csv(OUT/'budget_feasibility.csv',index=False);pd.DataFrame(checks).to_csv(OUT/'budget_machine_checks.csv',index=False)
    cd=[]
    for key,g in d.groupby(KEY+['configuration'],sort=False):
        by=g.set_index('policy')
        if not {'U','B','N'}<=set(by.index):continue
        u,b,n=by.loc['U'],by.loc['B'],by.loc['N'];r={v:b[v] for v in KEY+['axis','configuration','K','C','m']}
        r.update(d=max(0,int(n.m-b.novel_document_exposure)),binding=int(n.novel_document_exposure)>int(b.novel_document_exposure))
        for z in METRICS:r.update({'U_'+z:int(u[z]),'B_'+z:int(b[z]),'N_'+z:int(n[z]),'allocation_delta_'+z:int(b[z]-u[z]),'within_delta_'+z:int(n[z]-b[z])})
        cd.append(r)
    cdf=pd.DataFrame(cd);cdf.to_parquet(OUT/'budget_contrast_detail.parquet',index=False)
    summary=[]
    for (task,model,axis),g in cdf.groupby(['task','model','axis']):
        cfgs=[ident(a,k,c,m) for a,k,c,m in CONFIGS if a==axis];by={case:q.set_index(['organization_id','year']) for case,q in g.groupby('configuration')}
        common=set.intersection(*(set(by[case].index) if case in by else set() for case in cfgs))
        for case in cfgs:
          gg=by.get(case,pd.DataFrame())
          for support in ('individual_feasible','axis_common'):
            q=gg if support=='individual_feasible' else gg.loc[[i for i in gg.index if i in common]]
            cfg=next(x for x in CONFIGS if ident(*x)==case);_,k,c,m=cfg
            eligible=int(p[p.task==task][['organization_id','year']].drop_duplicates().shape[0])
            r={'task':task,'model':model,'axis':axis,'configuration':case,'K':k,'C':c,'m':m,'support':support,'original_situations':eligible,'n_situations':len(q),'n_organizations':len(set(q.index.get_level_values(0))) if len(q) else 0,'n_binding':int(q.binding.sum()) if len(q) else 0,'introduced_events':int(q.d.sum()) if len(q) else 0}
            for z in METRICS:
                for prefix in ('U_','B_','N_','allocation_delta_','within_delta_'):r['mean_'+prefix+z]=float(q[prefix+z].mean()) if len(q) else None
                v=q['within_delta_'+z] if len(q) else pd.Series(dtype=float);r[z+'_within_wins']=int((v>0).sum());r[z+'_within_ties']=int((v==0).sum());r[z+'_within_losses']=int((v<0).sum())
            summary.append(r)
    pd.DataFrame(summary).to_csv(OUT/'budget_sensitivity.csv',index=False)
    audit={'status':'PASS','seconds':time.perf_counter()-start,'policy_rows':len(d),'selected_events':len(s),'feasibility_rows':len(f),'checks':len(checks),'predictor_fits':0,'new_source_acquisition':0}
    dump(OUT/'budget_runtime.json',audit);log('BUDGET_PASS',**audit)

def joint(draws=4000):
    start=time.perf_counter();freeze();p=pools();c=pd.read_parquet(ROOT/'results/revision_v7/effective_contrast_detail.parquet');c=c[c.comparison=='within_C9_floor3']
    e=pd.read_parquet(ROOT/'results/revision_v7/effective_signed_events.parquet');e=e[e.comparison=='within_C9_floor3']
    orgs=sorted(p.organization_id.unique());pats=sorted(p.patent_id.unique());oi={v:i for i,v in enumerate(orgs)};pi={v:i for i,v in enumerate(pats)};no,npats=len(orgs),len(pats)
    Ds=[];Ns=[];Es={};meta=[];orgD=[]
    for task in TASKS:
        pp=p[p.task==task];rr=pp.organization_id.map(oi).to_numpy();cc=pp.patent_id.map(pi).to_numpy();Es[task]=sparse.csr_matrix((pp.pool_exposure.to_numpy(),(rr,cc)),shape=(no,npats))
        for model in MODELS:
            q=c[(c.task==task)&(c.model==model)];ee=e[(e.task==task)&(e.model==model)]
            rr=ee.organization_id.map(oi).to_numpy();cc=ee.patent_id.map(pi).to_numpy();D=sparse.csr_matrix((ee.sign.to_numpy()*ee.task_linked.to_numpy(),(rr,cc)),shape=(no,npats));N=q.organization_id.map(oi).value_counts().reindex(range(no),fill_value=0).to_numpy(float);od=np.asarray(D.sum(axis=1)).ravel();point=float(od.sum()/len(q))
            assert np.isclose(point,q.delta_task_linked.mean(),atol=1e-12)
            Ds.append(D);Ns.append(N);orgD.append(od);meta.append({'task':task,'model':model,'n_situations':len(q),'n_organizations':q.organization_id.nunique(),'point':point})
    rng=np.random.default_rng(SEED);ov=np.full((draws,4),np.nan);xv=np.full_like(ov,np.nan)
    for b in range(draws):
        count=np.bincount(rng.integers(0,no,no),minlength=no);xo=rng.exponential(size=no);xp=rng.exponential(size=npats)
        xd={task:float(xo@(Es[task]@xp)) for task in TASKS}
        for j,m in enumerate(meta):ov[b,j]=float(count@orgD[j])/float(count@Ns[j]);xv[b,j]=float(xo@(Ds[j]@xp))/xd[m['task']]
        if (b+1)%1000==0:log('JOINT_DRAW',draw=b+1,total=draws)
    out=[];point=np.asarray([r['point'] for r in meta]);critical={}
    for method,v in [('paired_organization',ov),('crossed_org_patent_sensitivity',xv)]:
        assert np.isfinite(v).all();sd=v.std(axis=0,ddof=1);assert (sd>0).all();depart=(v-point[None,:])/sd[None,:];q=float(np.quantile(np.max(np.abs(depart),axis=1),.95));critical[method]=q
        for j,m in enumerate(meta):out.append({**m,'metric':'task_linked','comparison':'N30_C9_m3_minus_B30_C9','method':method,'draws':draws,'family_size':4,'bootstrap_sd':float(sd[j]),'joint_critical':q,'lower':float(point[j]-q*sd[j]),'upper':float(point[j]+q*sd[j]),'bootstrap_mean':float(v[:,j].mean()),'seed':SEED})
    pd.DataFrame(out).to_csv(OUT/'joint_four_contrast_ranges.csv',index=False)
    np.savez_compressed(OUT/'joint_four_contrast_draws.npz',paired_organization=ov,crossed_sensitivity=xv,points=point)
    notes={'status':'PASS','seconds':time.perf_counter()-start,'draws_each':draws,'family_size':4,'global_unique_org_keys':no,'global_unique_patent_keys':npats,'shared_weights_across_all_four':True,'critical_values':critical,'construction':'Bootstrap distribution centered at each observed point; empirical SD standardizes departures; maximum absolute departure over the fixed four-contrast family gives one common 95% critical value. This is approximate fixed-list simultaneous inference, not an exact finite-sample coverage claim.','crossed_caveat':'Crossed ranges retain complete-pool exposure denominators and are dependence sensitivity; they do not establish nominal frequentist coverage.','p_values':'None computed or added. No multiplicity testing of identities, d distributions, descriptive parameter tables or handoff cases.'}
    dump(OUT/'joint_four_contrast_notes.json',notes);log('JOINT_PASS',**notes)

def random_reference(seeds=100):
    start=time.perf_counter();freeze();p=pools();s=pd.read_parquet(ROOT/'results/revision_v7/effective_selected.parquet');s=s[s.policy=='B09_m03'];sm={key:list(q.patent_id.astype(str)) for key,q in s.groupby(KEY)}
    refs=[];prepared=[]
    for (task,org,y),q in p.groupby(['task','organization_id','year'],sort=True):
        q=q.reset_index(drop=True);ids=q.patent_id.to_numpy(str);lookup={v:i for i,v in enumerate(ids)};core=q.is_core.to_numpy(bool);nov=q.novel_document.to_numpy(bool);nc=np.flatnonzero(nov);fc=np.flatnonzero(core&~nov)
        yy=np.vstack([q[z].to_numpy(float) for z in ('task_linked','general_reach')])
        for model in MODELS:
            ss=np.asarray([lookup[v] for v in sm[task,org,y,model]],int);nn=int(nov[ss].sum());nf=9-nn;non=ss[~core[ss]]
            assert len(ss)==30 and int(core[ss].sum())==9 and len(non)==21 and nn>=3 and nn<=len(nc) and nf<=len(fc)
            fixed=yy[:,non].sum(axis=1);det=yy[:,ss].sum(axis=1);ex=fixed.copy()
            if nn:ex+=nn*yy[:,nc].mean(axis=1)
            if nf:ex+=nf*yy[:,fc].mean(axis=1)
            refs.append({'task':task,'organization_id':org,'year':int(y),'model':model,'core_positions':9,'unfamiliar_positions':nn,'fixed_noncore_documents':21,'unfamiliar_supply':len(nc),'familiar_supply':len(fc),'det_task_linked':int(det[0]),'uniform_expected_task_linked':float(ex[0]),'task_rank_minus_uniform':float(det[0]-ex[0]),'det_general_reach':int(det[1]),'uniform_expected_general_reach':float(ex[1]),'general_rank_minus_uniform':float(det[1]-ex[1])})
            prepared.append((task,model,nc,fc,nn,nf,yy,fixed,det))
    df=pd.DataFrame(refs);df.to_parquet(OUT/'random_reference_expected_detail.parquet',index=False)
    df.groupby(['task','model']).agg(n_situations=('year','size'),n_organizations=('organization_id','nunique'),mean_matched_unfamiliar=('unfamiliar_positions','mean'),mean_deterministic_task=('det_task_linked','mean'),mean_uniform_expected_task=('uniform_expected_task_linked','mean'),mean_task_rank_increment=('task_rank_minus_uniform','mean'),mean_deterministic_general=('det_general_reach','mean'),mean_uniform_expected_general=('uniform_expected_general_reach','mean'),mean_general_rank_increment=('general_rank_minus_uniform','mean')).reset_index().to_csv(OUT/'random_reference_expected_summary.csv',index=False)
    draws=[];validation_checks=0
    for seed in range(seeds):
        rng=np.random.default_rng(SEED+10000+seed);sums={(t,m):np.zeros(4,float) for t in TASKS for m in MODELS};counts={(t,m):0 for t in TASKS for m in MODELS}
        for task,model,nc,fc,nn,nf,yy,fixed,det in prepared:
            chosen=np.r_[rng.choice(nc,nn,replace=False),rng.choice(fc,nf,replace=False)]
            assert len(set(chosen))==9;assert int(np.isin(chosen,nc).sum())==nn;validation_checks+=1
            val=fixed+yy[:,chosen].sum(axis=1);sums[task,model]+=np.r_[val,det-val];counts[task,model]+=1
        for (task,model),v in sums.items():draws.append({'task':task,'model':model,'seed_index':seed,'seed':SEED+10000+seed,'n_situations':counts[task,model],'mean_uniform_task':float(v[0]/counts[task,model]),'mean_uniform_general':float(v[1]/counts[task,model]),'mean_task_rank_increment':float(v[2]/counts[task,model]),'mean_general_rank_increment':float(v[3]/counts[task,model])})
    pd.DataFrame(draws).to_csv(OUT/'random_reference_monte_carlo.csv',index=False)
    notes={'status':'PASS','seconds':time.perf_counter()-start,'seeds':seeds,'strata_checks':validation_checks,'n_situations_each_seed':df.groupby(['task','model']).size().to_dict().__str__(),'main_estimate':'Exact finite-pool conditional expectation, not seed-average estimate','matched_dimensions':'30 total,9 core,exact actual unfamiliar count of N9m3,identical21 noncore IDs','uniform_scheme':'Without replacement within unfamiliar core and familiar core strata independently','meaning':'Tests ranking-specific selection against arbitrary selection at the identical observed composition. It does not estimate a causal organizational effect or provide a novelty placebo.','seed_uncertainty':'Between-seed variation is Monte Carlo selection variation; 100 seeds do not add independent organizations.'}
    dump(OUT/'random_reference_notes.json',notes);log('RANDOM_PASS',**notes)

def qpath(p):return "'"+str(p).replace('\\','/').replace("'","''")+"'"

def windows():
    start=time.perf_counter();freeze();p=pools();p=p[p.year.isin([2018,2019])];keys=p[['task','patent_id','year']].drop_duplicates();keys['patent_id']=keys.patent_id.astype(str)
    conn=duckdb.connect(':memory:');conn.execute("SET threads=2; SET memory_limit='2GB'");conn.execute('SET temp_directory='+qpath(OUT/'window_temp'))
    conn.execute('ATTACH '+qpath(ROOT/'datasets/canonical_v1/labels.duckdb')+' AS canonical (READ_ONLY)')
    labels=[];edge_counts=[]
    for task in TASKS:
        kk=keys[keys.task==task][['patent_id','year']];conn.register('included_candidates',kk)
        if task=='battery':
            sql='SELECT e.patent_id,e.year,e.citing_id,e.citing_date,e.citing_assignee_id,e.citing_is_core AS task_core FROM read_parquet('+qpath(ROOT/'datasets/revision_v2/task_five_year_edges.parquet')+')e JOIN included_candidates k USING(patent_id,year)'
        else:
            sql="""SELECT e.cited_id AS patent_id,e.year,e.citing_id,e.citing_date,e.citing_assignee_id,coalesce(g.electronics_core,false) AND NOT coalesce(g.battery_core,false) AS task_core
              FROM canonical.edges e JOIN included_candidates k ON e.cited_id=k.patent_id AND e.year=k.year
              LEFT JOIN read_parquet("""+qpath(ROOT/'datasets/revision_v3/validation_electronics_grants.parquet')+""")g ON e.citing_id=g.patent_id
              WHERE e.known_citing_owner AND NOT e.overlapping_raw_owners AND NOT coalesce(e.same_application,false)
              AND e.citing_date>=make_date(e.year+1,1,1) AND e.citing_date<=make_date(e.year+5,12,31) AND e.citing_date>=e.cited_date"""
        conn.execute('CREATE OR REPLACE TEMP TABLE fixed_window_edges AS '+sql)
        edge_counts.append({'task':task,'included_candidates':len(kk),'complete_five_year_filtered_edges':conn.execute('SELECT count(*) FROM fixed_window_edges').fetchone()[0]})
        frame=conn.execute("""SELECT k.patent_id,k.year,w.horizon,
            count(DISTINCT e.citing_id) FILTER(WHERE e.task_core AND e.citing_date<=make_date(k.year+w.horizon,12,31))>=1 AS task_linked,
            count(DISTINCT owner) FILTER(WHERE nullif(owner,'') IS NOT NULL AND e.citing_date<=make_date(k.year+w.horizon,12,31))>=2 AS general_reach
            FROM included_candidates k CROSS JOIN (VALUES(2),(3),(5))w(horizon)
            LEFT JOIN fixed_window_edges e ON k.patent_id=e.patent_id AND k.year=e.year
            LEFT JOIN LATERAL unnest(string_split(coalesce(e.citing_assignee_id,''),'|'))u(owner) ON true
            GROUP BY k.patent_id,k.year,w.horizon ORDER BY k.year,k.patent_id,w.horizon""").fetchdf()
        frame['task']=task;labels.append(frame)
    conn.close();labs=pd.concat(labels,ignore_index=True);labs['patent_id']=labs.patent_id.astype(str)
    assert not labs.duplicated(['task','patent_id','year','horizon']).any()
    rec=labs[labs.horizon==3].merge(p[['task','patent_id','year','task_linked','general_reach']].drop_duplicates(),on=['task','patent_id','year'],suffixes=('_new','_old'),validate='one_to_one')
    check=[]
    for task in TASKS:
      q=rec[rec.task==task]
      for z in ('task_linked','general_reach'):
        nbad=int((q[z+'_new']!=q[z+'_old']).sum());check.append({'task':task,'check':'three_year_rebuild_'+z,'candidate_ids':len(q),'mismatches':nbad});assert nbad==0
    old5=pd.read_parquet(ROOT/'datasets/revision_v2/task_patent_labels.parquet',columns=['patent_id','year','five_year_core_signal_1patent','five_year_external_signal_2org']);old5['patent_id']=old5.patent_id.astype(str)
    xx=labs[(labs.task=='battery')&(labs.horizon==5)].merge(old5,on=['patent_id','year'],validate='one_to_one')
    for z,oldz in [('task_linked','five_year_core_signal_1patent'),('general_reach','five_year_external_signal_2org')]:
        nbad=int((xx[z]!=xx[oldz]).sum());check.append({'task':'battery','check':'five_year_old_cache_'+z,'candidate_ids':len(xx),'mismatches':nbad});assert nbad==0
    # Longer windows cannot remove an existing candidate-level signal.
    for z in ('task_linked','general_reach'):
        pivot=labs.pivot(index=['task','patent_id','year'],columns='horizon',values=z);ok=bool(((pivot[2].astype(int)<=pivot[3].astype(int))&(pivot[3].astype(int)<=pivot[5].astype(int))).all());check.append({'check':'window_monotonicity_'+z,'passed':ok});assert ok
    labs.to_parquet(OUT/'mature_window_candidate_labels.parquet',index=False)
    pd.DataFrame(check).to_json(OUT/'window_label_checks.json',orient='records',indent=2)
    nsel=window_summaries(labs)
    audit={'status':'PASS','seconds':time.perf_counter()-start,'origins':[2018,2019],'horizons':[2,3,5],'candidate_label_rows':len(labs),'selected_events_per_window':nsel,'sources':edge_counts,'checks':check,'scope':'Identical2018–2019 origin situations/lists for2/3/5 windows; 2020/2021 never labeled as complete five-year observations','three_year_values_all_recovered':True,'new_raw_scans':0}
    dump(OUT/'mature_window_audit.json',audit);log('WINDOW_PASS',**audit)

def window_summaries(labs):
    """Replay fixed-list outcome summaries from already reconstructed labels only."""
    sel=pd.read_parquet(ROOT/'results/revision_v7/effective_selected.parquet');sel=sel[sel.year.isin([2018,2019])&sel.policy.isin(['U','B09_m00','B09_m03','legacy','legacy_matched'])]
    selected=sel.merge(labs,on=['task','patent_id','year'],validate='many_to_many')
    assert len(selected)==3*len(sel)
    counts=selected.groupby(KEY+['horizon','policy']).agg(task_linked=('task_linked','sum'),general_reach=('general_reach','sum')).reset_index()
    counts.to_parquet(OUT/'mature_window_policy_detail.parquet',index=False)
    contrasts=[]
    for key,x in counts.groupby(KEY+['horizon']):
        b=x.set_index('policy');row=dict(zip(KEY+['horizon'],key));row.update({z+'_delta_allocation':int(b.loc['B09_m00',z]-b.loc['U',z]) for z in ('task_linked','general_reach')});row.update({z+'_delta_C9m3':int(b.loc['B09_m03',z]-b.loc['B09_m00',z]) for z in ('task_linked','general_reach')});row.update({z+'_delta_legacy':int(b.loc['legacy',z]-b.loc['legacy_matched',z]) for z in ('task_linked','general_reach')});contrasts.append(row)
    cc=pd.DataFrame(contrasts);cc.to_parquet(OUT/'mature_window_contrast_detail.parquet',index=False)
    cc.groupby(['task','model','horizon']).agg(n_situations=('year','size'),n_organizations=('organization_id','nunique'),**{z:(z,'mean') for z in cc.columns if z.endswith(('delta_allocation','delta_C9m3','delta_legacy'))}).reset_index().to_csv(OUT/'mature_window_sensitivity.csv',index=False)
    return len(sel)

def window_summary_replay():
    start=time.perf_counter();freeze();path=OUT/'mature_window_candidate_labels.parquet';labs=pd.read_parquet(path);labs['patent_id']=labs.patent_id.astype(str)
    assert set(labs.horizon.unique())=={2,3,5} and set(labs.year.unique())=={2018,2019}
    assert not labs.duplicated(['task','patent_id','year','horizon']).any()
    p=pools();p=p[p.year.isin([2018,2019])]
    rec=labs[labs.horizon==3].merge(p[['task','patent_id','year','task_linked','general_reach']].drop_duplicates(),on=['task','patent_id','year'],suffixes=('_cached','_v7'),validate='one_to_one')
    assert len(rec)==p[['task','patent_id','year']].drop_duplicates().shape[0]
    for z in ('task_linked','general_reach'):assert bool((rec[z+'_cached']==rec[z+'_v7']).all())
    nsel=window_summaries(labs)
    audit={'status':'PASS','seconds':time.perf_counter()-start,'candidate_label_rows':len(labs),'selected_events_per_window':nsel,'label_source':str(path.relative_to(ROOT)),'label_sha256':sha(path),'scope':'Reproduces fixed-list 2/3/5-year statistics from archived candidate labels. Does not reconstruct citation edges, task code flags or five-year validity from raw source tables.','old_three_year_indicator_mismatches':0,'raw_edge_dependencies_used':False}
    dump(OUT/'mature_window_summary_replay_audit.json',audit);log('WINDOW_SUMMARY_REPLAY_PASS',**audit)

def source_record():
    paths=['scripts/revision_v8_sensitivity_analysis.py','scripts/policy_core.py','results/revision_v8/sensitivity_protocol.json','results/revision_v8/sensitivity_protocol_lock.json','results/revision_v8/mature_window_candidate_labels.parquet','results/revision_v7/effective_pools.parquet','results/revision_v7/effective_selected.parquet','results/revision_v7/effective_contrast_detail.parquet','results/revision_v7/effective_signed_events.parquet','datasets/revision_v2/task_five_year_edges.parquet','datasets/revision_v2/task_patent_labels.parquet','datasets/revision_v3/validation_electronics_grants.parquet','datasets/canonical_v1/labels.duckdb','research/revision_v6_protocol_2022_final.json','research/revision_v6_protocol_2022_final_lock.json']
    dump(OUT/'sensitivity_source_manifest.json',{v:{'bytes':(ROOT/v).stat().st_size,'sha256':sha(ROOT/v)} for v in paths})

def md(df):
    def f(v):
        if pd.isna(v):return '—'
        if isinstance(v,(float,np.floating)):return f'{v:.6f}'
        return str(v).replace('|','\\|')
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f(v) for v in r)+' |' for r in df.itertuples(index=False,name=None))

def report():
    text='# v8 Focused sensitivity and four-contrast joint inference\n\nRoute: SSCI technology-management archival replay. These are supplementary analyses of already examined outcomes, not an independent extension or organizational-use validation. No prediction training, source download, account access or2022 evaluation.\n\n'
    for name,heading in [('budget_runtime.json','Actual budget execution'),('joint_four_contrast_notes.json','Joint family inference'),('random_reference_notes.json','Matched random reference'),('mature_window_audit.json','Complete-window cohort')]:
        if (OUT/name).exists():text+='## '+heading+'\n\n'+(OUT/name).read_text(encoding='utf-8')+'\n\n'
    if (OUT/'joint_four_contrast_ranges.csv').exists():
        text+='## Four simultaneous task-link ranges\n\n'+md(pd.read_csv(OUT/'joint_four_contrast_ranges.csv'))+'\n\nThe inferential family comprises only four fixed C9m3−B9 task-link contrasts; identities and descriptive parameter summaries are not hypothesis tests. Global organization and patent weights are shared within each draw across both tasks/rankers. Centered maximum standardized departures give one family critical value. Organization ranges are approximate bootstrap intervals; crossed ranges are dependence sensitivities rather than established exact-coverage confidence intervals. No additional p-values.\n\n'
    if (OUT/'budget_sensitivity.csv').exists():
        b=pd.read_csv(OUT/'budget_sensitivity.csv');cols=['task','model','axis','K','C','m','support','original_situations','n_situations','n_organizations','n_binding','introduced_events','mean_allocation_delta_task_linked','mean_within_delta_task_linked','mean_within_delta_general_reach','mean_within_delta_novel_document_exposure']
        text+='## Complete paired budget/floor/allocation summaries\n\n'+md(b[cols])+'\n\nCompare K changes only within an axis and its common origin support. Fixed C9/m3 changes other capacity, whereas the fractional axis changes C/m with K; their meanings differ. On the fixed C9/m3 axis, B and N select the same core IDs at every K, and within each K the same noncore IDs cancel from N−B. Therefore identical within-allocation residuals across K20/30/50 are a design identity on common support, not new empirical robustness evidence. The allocation-versus-U contrast does change because U and the number of noncore positions change. The fractional axis instead changes the core selection/floor, allowing non-identical within-allocation outcomes. Every individual shortage remains in budget_feasibility.csv. The new fixed-m allocation endpoints C3/15 complement the existing v7 C6/12 results; this is not an outcome-chosen grid. All negative/zero returns retained.\n\n'
    if (OUT/'random_reference_expected_summary.csv').exists():text+='## Exact matched-uniform expectation\n\n'+md(pd.read_csv(OUT/'random_reference_expected_summary.csv'))+'\n\nRandom selection preserves each deterministic list’s core count, actual unfamiliar count and every noncore identifier. Expected values use finite-pool stratum label means; no Monte Carlo accuracy claim is needed for the main estimate.100 seeds are computational checks and selection variability, not independent organizations or causal placebo observations. This comparison assesses ranking within a fixed composition; it does not isolate a cognitive novelty effect.\n\n'
    if (OUT/'mature_window_sensitivity.csv').exists():text+='##2/3/5grant-year windows on identical2018–2019 situations\n\n'+md(pd.read_csv(OUT/'mature_window_sensitivity.csv'))+'\n\n2020/2021 are excluded from every row, including2/3year comparisons, so the5year horizon is complete through2024. The denominator difference from the356/1077 full period is explicit. Reconstructed3year candidate indicators match every original included label, and the5year battery indicators additionally match the old5year cache. These are archival citing-grant windows, not times of adoption or engineering use.\n\n'
    text+='## Local replay and dependencies\n\nThere are two different reproduction layers. A compact local statistical replay package needs this script, `policy_core.py`, the four frozen v7 Parquets (`effective_pools`, `effective_selected`, `effective_contrast_detail`, `effective_signed_events`), the v8 protocol/lock, and `mature_window_candidate_labels.parquet`. Preserve the project-relative layout. Run `python -B scripts/revision_v8_sensitivity_analysis.py --pilot`, and then the individual `--budget`, `--joint`, `--random` commands. `--window-summary-replay` rebuilds all fixed-list 2/3/5-year statistical summaries from the cached mature candidate labels and verifies their three-year indicators against v7 pools; it does not reconstruct citation edges or re-establish maturity from source data. No source DuckDB is needed for this compact replay.\n\nThe full source-label reconstruction layer uses `--windows` or the no-flag full run and additionally requires the cached battery five-year edges/labels, electronics grants and the read-only canonical labels DuckDB with its `edges` table. It checks the original candidate-level three-year indicators and old battery five-year cache. No original source TSV scan is needed, but these source dependencies are not claimed to be inside the compact package. `--report` updates the report and complete local dependency hashes; it requires the source dependencies to be present. All dependency sizes/SHA values are enumerated in `sensitivity_source_manifest.json`. The 2022 protocol and lock are audited for preservation only and never used for new 2022 results.\n\nActual environment: Python '+sys.version.split()[0]+', '+', '.join(name+'=='+metadata.version(name) for name in ('numpy','pandas','scipy','duckdb','pyarrow'))+'. These are the replay dependencies; no scikit-learn or predictor training is required.\n\n'
    size=sum(x.stat().st_size for x in OUT.rglob('*') if x.is_file());text+=f'## Storage and boundaries\n\nNew v8 outputs total {size:,} bytes, below the1GB cap. All sources remain on their original drives and are read-only inputs. Sparse or supply-limited cells are disclosed; supplementary designs do not provide new causal identification, independent cases from repeated selections, or new-sample confirmation. Source sizes/SHA values are recorded separately.\n'
    (ROOT/'research/revision_v8_sensitivity_report.md').write_text(text,encoding='utf-8');log('REPORT_READY',bytes=size,path=str(ROOT/'research/revision_v8_sensitivity_report.md'))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--budget',action='store_true');ap.add_argument('--joint',action='store_true');ap.add_argument('--random',action='store_true');ap.add_argument('--windows',action='store_true');ap.add_argument('--window-summary-replay',action='store_true');ap.add_argument('--report',action='store_true');args=ap.parse_args()
    if args.pilot:budget(True)
    elif args.budget:budget();report()
    elif args.joint:joint();report()
    elif args.random:random_reference();report()
    elif args.windows:windows();report()
    elif args.window_summary_replay:window_summary_replay();report()
    elif args.report:source_record();report()
    else:budget();joint();random_reference();windows();source_record();report()
