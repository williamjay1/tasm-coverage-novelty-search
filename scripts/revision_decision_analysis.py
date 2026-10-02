"""Post-critique decision analysis of unchanged v1 pools, scores, and rules.

No outcome enters selection. Rebuilds and audits historical K=30 options,
matched random replacements, pairwise title redundancy, and transparent
preference/document-cost scenarios. Outputs remain under decision_* in v2.
"""
from __future__ import annotations
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[name]='2'
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from policy_core import quota_select, mmr_select, stable_order

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'results/primary_v1'
OUT=ROOT/'results/revision_v2'
INPUT_REV=ROOT/'results/revision_v2'
SEED=20260930
K=30

def codes(v):
    return {s[:4] for s in str(v).split('|') if len(s)>=4 and s!='nan'}

def emit(event, **kwargs):
    print(json.dumps({'event':event,**kwargs}),flush=True)

def metrics(chosen,base,high,far):
    chosen=np.asarray(chosen,int); base=np.asarray(base,int)
    added=np.setdiff1d(chosen,base); removed=np.setdiff1d(base,chosen)
    return {'T':int(high[chosen].sum()),'U':int((high[chosen]&far[chosen]).sum()),
            'n_selected':len(chosen),'far_selected':int(far[chosen].sum()),
            'base_T':int(high[base].sum()),'base_U':int((high[base]&far[base]).sum()),
            'added_n':len(added),'removed_n':len(removed),
            'added_T':int(high[added].sum()),'removed_T':int(high[removed].sum()),
            'added_U':int((high[added]&far[added]).sum()),'removed_U':int((high[removed]&far[removed]).sum()),
            'original_T_surviving':int(high[np.intersect1d(chosen,base)].sum())}

def summarize(frame,keys):
    values=['T','U','n_selected','far_selected','base_T','base_U','added_n','removed_n',
            'added_T','removed_T','added_U','removed_U','original_T_surviving']
    rows=[]
    for key,g in frame.groupby(keys,dropna=False):
        key=(key,) if not isinstance(key,tuple) else key
        row=dict(zip(keys,key)); row.update(n_decisions=len(g),n_organizations=g.organization_id.nunique())
        row.update({v:float(g[v].mean()) for v in values})
        row.update(count_ratio=g['T'].sum()/g.base_T.sum() if g.base_T.sum() else np.nan,
            original_signal_survival=g.original_T_surviving.sum()/g.base_T.sum() if g.base_T.sum() else np.nan,
            delta_T=float((g['T']-g.base_T).mean()),delta_U=float((g['U']-g.base_U).mean()),
            fraction_total_loss=float((g['T']<g.base_T).mean()),
            fraction_unfamiliar_gain=float((g['U']>g.base_U).mean()))
        row['break_even_lambda']=1-row['delta_T']/row['delta_U'] if row['delta_U']>0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)

def analyse(repeats):
    OUT.mkdir(exist_ok=True,parents=True)
    existing=OUT/'decision_selected.parquet'
    if existing.exists(): raise FileExistsError('Do not overwrite a completed decision reconstruction')
    original=pd.read_parquet(RUN/'heldout_policy_results.parquet')
    original=original.loc[original.k.eq(K)]
    base_context=original.loc[original.model.eq('boosting')&original.policy.eq('topk')]
    rules=pd.read_csv(RUN/'development_allocation_rules.csv')
    rules=rules.loc[rules.k.eq(K)]
    rule={(r.model,r.context,r.minimum_retention):float(r.share) for r in rules.itertuples()}
    study=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet')
    study['year']=pd.to_datetime(study.patent_date).dt.year
    study=study.sort_values(['year','patent_id']).reset_index(drop=True)
    portfolios=pd.read_parquet(ROOT/'datasets/canonical_v1/study_portfolios.parquet')
    portfolios['year']=pd.to_datetime(portfolios.patent_date).dt.year
    portfolios=portfolios.sort_values(['year','patent_id']).reset_index(drop=True)
    all_decisions=[]; all_selections=[]; all_pools=[]; random_decisions=[]; random_seed_rows=[]
    redundancy=[]; tail_rows=[]; opportunity_rows=[]; citation_gross=[]; cost_rows=[]; audit=[]
    for year in [2018,2019,2020,2021]:
        current=pd.read_parquet(RUN/f'scores_{year}.parquet').sort_values('patent_id').reset_index(drop=True)
        train=study.loc[study.year.between(2010,year-3)]
        hist=portfolios.loc[portfolios.year.between(year-5,year-1)].reset_index(drop=True)
        vectorizer=TfidfVectorizer(max_features=20000,min_df=2,max_df=.98,ngram_range=(1,2),
            stop_words='english',dtype=np.float32,sublinear_tf=True)
        vectorizer.fit(train.patent_title.fillna(''))
        xhist=vectorizer.transform(hist.patent_title.fillna(''))
        xcurrent=vectorizer.transform(current.patent_title.fillna(''))
        ids=current.patent_id.astype(str).to_numpy()
        current_codes=current.cpc_codes.map(codes).tolist()
        current_owners=current.assignee_id.fillna('').str.split('|').map(set).tolist()
        hist_codes=hist.cpc_codes.map(codes).tolist()
        orgs=base_context.loc[base_context.year.eq(year)].organization_id.tolist()
        org_index={org:[] for org in orgs}
        for index,owners in enumerate(hist.assignee_id.fillna('').str.split('|')):
            for org in owners:
                if org in org_index: org_index[org].append(index)
        saved=pd.read_parquet(RUN/f'selected_primary_{year}.parquet')
        saved=saved.loc[saved.k.eq(K)]
        saved_sets={(org,policy):set(g.patent_id.astype(str)) for (org,policy),g in saved.groupby(['organization_id','policy'])}
        seed_sums={model:np.zeros((repeats,3)) for model in ['boosting','ridge','popularity','similarity']}
        for org in orgs:
            hi=np.asarray(org_index[org],int)
            centroid=normalize(sparse.csr_matrix(np.asarray(xhist[hi].mean(axis=0))))
            sim=(xcurrent@centroid.T).toarray().ravel()
            pool=np.flatnonzero((sim>=.03)&np.asarray([org not in x for x in current_owners])&np.asarray([bool(x) for x in current_codes]))
            historical=set().union(*(hist_codes[i] for i in hi))
            far=np.asarray([not bool(current_codes[i]&historical) for i in pool])
            core=current.iloc[pool].is_core.to_numpy(bool)
            high=current.iloc[pool].future_external_attention.ge(2).to_numpy()
            app=current.iloc[pool].future_applicant_attention.ge(2).to_numpy()
            context=base_context.loc[base_context.year.eq(year)&base_context.organization_id.eq(org),'context'].iloc[0]
            poolframe=pd.DataFrame({'organization_id':org,'year':year,'patent_id':ids[pool],
                'distant':far,'is_core':core,'similarity':sim[pool],
                'all_high':high,'applicant_high':app})
            for model in ['boosting','ridge','popularity','similarity']:
                scores=sim[pool] if model=='similarity' else current.iloc[pool]['score_'+model].to_numpy()
                ranking=stable_order(scores,ids[pool])
                ordinal=np.empty(len(pool),int); ordinal[ranking]=np.arange(1,len(pool)+1)
                poolframe['rank_'+model]=ordinal
                base=quota_select(scores,ids[pool],far,K,0)
                policies={'topk':base}
                for q in [.1,.2,.3,.4]: policies[f'quota_{q:.1f}']=quota_select(scores,ids[pool],far,K,q)
                for retention in [.9,1.]:
                    q=rule.get((model,context,retention),0.)
                    policies[f'context_rule_retention_{retention:.1f}']=policies['topk' if q==0 else f'quota_{q:.1f}']
                if model=='boosting':
                    for weight in [.5,.7,.9]:policies[f'mmr_{weight:.1f}']=mmr_select(scores,ids[pool],xcurrent[pool],K,weight)
                for policy,selected in policies.items():
                    observed=original.loc[original.year.eq(year)&original.organization_id.eq(org)&original.model.eq(model)&original.policy.eq(policy)]
                    if len(observed)!=1:raise AssertionError('Missing original policy row')
                    old=observed.iloc[0]
                    m=metrics(selected,base,high,far)
                    if m['T']!=old.high_attention_hits or m['U']!=old.distant_high_attention_hits or len(pool)!=old.pool_n:
                        raise AssertionError(f'Reconstruction mismatch {year} {org} {model} {policy}')
                    if model=='boosting' and not policy.startswith('context_'):
                        if set(ids[pool[selected]])!=saved_sets[(org,policy)]:raise AssertionError('Saved list mismatch')
                    common={'organization_id':org,'year':year,'context':context,'model':model,'policy':policy}
                    all_decisions.append({**common,**m})
                    all_selections.append(pd.DataFrame({**common,'rank':np.arange(1,K+1),'patent_id':ids[pool[selected]],'distant':far[selected],'is_core':core[selected]}))
                    for label,values in [('all_citations',high),('applicant_citations',app)]:
                        added=np.setdiff1d(selected,base); removed=np.setdiff1d(base,selected)
                        citation_gross.append({**common,'label':label,**metrics(selected,base,values,far),
                            'added_all_only':int((high[added]&~app[added]).sum()),'removed_all_only':int((high[removed]&~app[removed]).sum()),
                            'added_both':int((high[added]&app[added]).sum()),'removed_both':int((high[removed]&app[removed]).sum())})
                    # Existing selection order is reservation-first for quotas,
                    # score order for topk, and greedy order for MMR. No outcome sorting.
                    for cost in [1.,1.5,2.]:
                        costs=np.where(far[selected],cost,1.)
                        prefix=selected[np.cumsum(costs)<=30.+1e-10]
                        cost_rows.append({**common,'unfamiliar_document_cost':cost,'budget':30.,
                            'spent_cost':float(np.where(far[prefix],cost,1.).sum()),**metrics(prefix,base,high,far)})
                    if model=='boosting' and policy in ['topk','quota_0.3','mmr_0.5','mmr_0.7','mmr_0.9']:
                        cosine=(xcurrent[pool[selected]]@xcurrent[pool[selected]].T).toarray()
                        pairs=cosine[np.triu_indices(K,1)]
                        np.fill_diagonal(cosine,-np.inf)
                        redundancy.append({**common,'mean_pairwise_title_cosine':float(pairs.mean()),
                            'mean_nearest_selected_title_cosine':float(cosine.max(axis=1).mean()),
                            'max_pairwise_title_cosine':float(pairs.max())})
                qchosen=policies['quota_0.3']
                added=np.setdiff1d(qchosen,base); removed=np.setdiff1d(base,qchosen)
                retained=np.setdiff1d(base,removed)
                faroutside=np.flatnonzero(far&~np.isin(np.arange(len(pool)),base))
                if not far[added].all() or far[removed].any():raise AssertionError('Quota monotonicity mismatch')
                digest=int(hashlib.sha256(f'{year}|{org}|{model}'.encode()).hexdigest()[:12],16)
                rng=np.random.default_rng(SEED+digest)
                random_add=np.empty((repeats,len(added)),int)
                for s in range(repeats):random_add[s]=rng.choice(faroutside,size=len(added),replace=False)
                addedhits=high[random_add].sum(axis=1) if len(added) else np.zeros(repeats)
                totals=high[retained].sum()+addedhits
                unfamiliar=(high[retained]&far[retained]).sum()+addedhits
                seed_sums[model][:,0]+=totals;seed_sums[model][:,1]+=unfamiliar;seed_sums[model][:,2]+=addedhits
                random_decisions.append({'organization_id':org,'year':year,'model':model,'repeats':repeats,
                    'replacement_n':len(added),'retained_original_far_n':int(far[retained].sum()),
                    'matched_removed_T':int(high[removed].sum()),'deterministic_added_T':int(high[added].sum()),
                    'random_added_T_mean':float(addedhits.mean()),'random_T_mean':float(totals.mean()),
                    'random_U_mean':float(unfamiliar.mean()),'random_added_T_sd':float(addedhits.std(ddof=1)),
                    'available_nonbase_far_n':len(faroutside),
                    'analytic_expected_added_T':len(added)*float(high[faroutside].mean()) if len(faroutside) else 0.})
                opportunity_rows.append({'organization_id':org,'year':year,'model':model,'pool_n':len(pool),
                    'far_pool_n':int(far.sum()),'far_pool_high':int((far&high).sum()),
                    'base_far_high':int((high[base]&far[base]).sum()),
                    'missed_far_high':int((far&high).sum()-(high[base]&far[base]).sum()),
                    'base_far_n':int(far[base].sum()),'far_yield':float(high[far].mean()) if far.any() else np.nan,
                    'nonfar_yield':float(high[~far].mean()) if (~far).any() else np.nan})
                for band,mask in [('rank_1_30',ordinal<=30),('rank_31_100',(ordinal>30)&(ordinal<=100)),
                                  ('rank_101_500',(ordinal>100)&(ordinal<=500)),('rank_501_plus',ordinal>500)]:
                    for boundary,sub in [('far',far),('nonfar',~far)]:
                        ix=mask&sub
                        tail_rows.append({'organization_id':org,'year':year,'model':model,'band':band,'boundary':boundary,
                            'candidate_n':int(ix.sum()),'all_high_n':int(high[ix].sum()),'applicant_high_n':int(app[ix].sum())})
            all_pools.append(poolframe)
        for model,total in seed_sums.items():
            for seed in range(repeats):
                random_seed_rows.append({'year':year,'model':model,'seed':seed,'n_decisions':len(orgs),
                    'sum_T':total[seed,0],'sum_U':total[seed,1],'sum_added_T':total[seed,2]})
        audit.append({'year':year,'decisions':len(orgs),'title_vocabulary':len(vectorizer.vocabulary_),
                      'training_max_year':int(train.year.max()),'checked_policy_rows':len(orgs)*31})
        emit('decision_year_reconstructed',year=year,n_decisions=len(orgs))
        del xhist,xcurrent,hist,org_index
    decisions=pd.DataFrame(all_decisions)
    decisions.to_parquet(OUT/'decision_detail.parquet',index=False)
    selected=pd.concat(all_selections,ignore_index=True)
    selected.to_parquet(OUT/'decision_selected.parquet',index=False)
    pools=pd.concat(all_pools,ignore_index=True)
    pools.to_parquet(OUT/'decision_pools.parquet',index=False)
    absolute=summarize(decisions,['model','policy'])
    annual=summarize(decisions,['year','model','policy'])
    annual.to_csv(OUT/'decision_annual.csv',index=False)
    # Descriptive dominance among the evaluated options, not a fitted efficient frontier.
    absolute['descriptively_nondominated']=False
    for ix,r in absolute.iterrows():
        dominates=((absolute['T']>=r['T'])&(absolute['U']>=r['U'])&((absolute['T']>r['T'])|(absolute['U']>r['U'])))
        absolute.loc[ix,'descriptively_nondominated']=not bool(dominates.any())
    annual_risk=annual.groupby(['model','policy']).agg(min_annual_delta_T=('delta_T','min'),
        max_annual_delta_T=('delta_T','max'),min_annual_delta_U=('delta_U','min'),
        years_total_loss=('delta_T',lambda x:int((x<0).sum())))
    absolute=absolute.merge(annual_risk,on=['model','policy'])
    absolute.to_csv(OUT/'decision_absolute_options.csv',index=False)
    preference=[]
    for lam in [1.,1.5,2.,3.]:
        table=absolute[['model','policy','T','U']].copy();table['lambda']=lam
        table['scenario_value']=table['T']+(lam-1)*table['U']
        table['descriptive_rank']=table.scenario_value.rank(method='min',ascending=False)
        preference.append(table)
    pd.concat(preference).to_csv(OUT/'decision_preference_scenarios.csv',index=False)
    citation=pd.DataFrame(citation_gross)
    citation.to_parquet(OUT/'decision_citation_gross_detail.parquet',index=False)
    cs=summarize(citation,['label','model','policy'])
    compos=citation.groupby(['label','model','policy'])[['added_all_only','removed_all_only','added_both','removed_both']].mean().reset_index()
    cs.merge(compos,on=['label','model','policy']).to_csv(OUT/'decision_citation_gross.csv',index=False)
    pd.DataFrame(redundancy).to_csv(OUT/'decision_redundancy_detail.csv',index=False)
    pd.DataFrame(redundancy).groupby(['model','policy'])[['mean_pairwise_title_cosine','mean_nearest_selected_title_cosine','max_pairwise_title_cosine']].mean().to_csv(OUT/'decision_redundancy.csv')
    costs=cost_scenarios(selected,pools)
    costs.to_parquet(OUT/'decision_cost_detail.parquet',index=False)
    summarize(costs,['unfamiliar_document_cost','model','policy']).to_csv(OUT/'decision_cost_scenarios.csv',index=False)
    random=pd.DataFrame(random_decisions)
    random.to_csv(OUT/'decision_matched_random_detail.csv',index=False)
    random.groupby('model').agg(n_decisions=('year','size'),replacement_n=('replacement_n','mean'),
        matched_removed_T=('matched_removed_T','mean'),deterministic_added_T=('deterministic_added_T','mean'),
        random_added_T_mean=('random_added_T_mean','mean'),random_T_mean=('random_T_mean','mean'),random_U_mean=('random_U_mean','mean'),
        analytic_expected_added_T=('analytic_expected_added_T','mean')).to_csv(OUT/'decision_matched_random.csv')
    rr=pd.DataFrame(random_seed_rows)
    rr.to_csv(OUT/'decision_matched_random_seed_year.csv',index=False)
    reps=rr.groupby(['model','seed'])[['sum_T','sum_U','sum_added_T','n_decisions']].sum().reset_index()
    for val in ['T','U','added_T']:reps[val]=reps['sum_'+val]/reps.n_decisions
    reps.to_csv(OUT/'decision_matched_random_replicates.csv',index=False)
    opp=pd.DataFrame(opportunity_rows)
    opp.to_csv(OUT/'decision_opportunity_detail.csv',index=False)
    opp.groupby('model').agg(n_decisions=('year','size'),mean_pool_n=('pool_n','mean'),
        mean_far_pool_n=('far_pool_n','mean'),mean_far_pool_high=('far_pool_high','mean'),mean_base_far_high=('base_far_high','mean'),
        mean_missed_far_high=('missed_far_high','mean'),fraction_any_missed_far=('missed_far_high',lambda x:float((x>0).mean())),
        fraction_far_signal_supply=('far_pool_high',lambda x:float((x>0).mean())),
        mean_far_yield=('far_yield','mean'),mean_nonfar_yield=('nonfar_yield','mean')).to_csv(OUT/'decision_opportunities.csv')
    tail=pd.DataFrame(tail_rows)
    tail.to_csv(OUT/'decision_ranking_tail_detail.csv',index=False)
    tails=tail.groupby(['model','band','boundary'])[['candidate_n','all_high_n','applicant_high_n']].sum().reset_index()
    tails['all_high_yield']=tails.all_high_n/tails.candidate_n
    tails['applicant_high_yield']=tails.applicant_high_n/tails.candidate_n
    tails.to_csv(OUT/'decision_ranking_tail.csv',index=False)
    (OUT/'decision_audit.json').write_text(json.dumps({'status':'PASS','year_audits':audit,
        'checked_policy_rows':len(decisions),'saved_boost_lists_exact':True,'all_model_metrics_exact':True,
        'random_repeats':repeats,'seed':SEED,'scope':'Post-critique extension; unchanged v1 pools/scores/rules; no outcome selection',
        'cost_order':'Original quota_select reservation-first order; topk score order; MMR greedy order. Prefix of each original K30 list stops before budget exceeded. Within each cost scenario the reference is the equally budget-truncated topk list of the same ranker. Cost multipliers are hypothetical, not measured time.',
        'random':'Lock original unfamiliar selections, exact deterministic removed set and replacement count; draw uniformly without replacement from unfamiliar candidates outside baseline. Replicate intervals measure random comparator variation, not inference uncertainty.',
        'nondominance':'Historical mean points over evaluated options; no universal optimality or statistical dominance claim.',
        'utility':'T+(lambda-1)U; familiar signal weight=1, unfamiliar weight=lambda; scenario values not commercial value.'},indent=2),encoding='utf-8')
    emit('decision_analysis_complete',rows=len(decisions),selections=len(selected),pool_rows=len(pools))

def cost_scenarios(selected,pools,score_order=False):
    """Compare equally budgeted prefixes; allocation order is fully explicit."""
    rows=[]
    for (org,year),pool in pools.groupby(['organization_id','year']):
        pool=pool.reset_index(drop=True)
        lookup={p:i for i,p in enumerate(pool.patent_id)}
        high=pool.all_high.to_numpy(bool);far=pool.distant.to_numpy(bool)
        local=selected.loc[selected.organization_id.eq(org)&selected.year.eq(year)]
        for model,model_lists in local.groupby('model'):
            ordered={policy:np.asarray([lookup[p] for p in g.sort_values('rank').patent_id],int)
                     for policy,g in model_lists.groupby('policy')}
            if score_order:
                for policy,ix in ordered.items():
                    ordered[policy]=ix[np.argsort(pool.iloc[ix]['rank_'+model].to_numpy())]
            for cost in [1.,1.5,2.]:
                prefixes={policy:ix[np.cumsum(np.where(far[ix],cost,1.))<=30.+1e-10] for policy,ix in ordered.items()}
                base=prefixes['topk']
                for policy,prefix in prefixes.items():
                    rows.append({'organization_id':org,'year':year,'model':model,'policy':policy,
                        'unfamiliar_document_cost':cost,'budget':30.,
                        'spent_cost':float(np.where(far[prefix],cost,1.).sum()),**metrics(prefix,base,high,far)})
    return pd.DataFrame(rows)

def task_addition():
    """Join later task labels without changing the previously reconstructed lists."""
    labels_path=ROOT/'datasets/revision_v2/task_patent_labels.parquet'
    if not labels_path.exists():raise FileNotFoundError(labels_path)
    labels=pd.read_parquet(labels_path)
    selected=pd.read_parquet(OUT/'decision_selected.parquet')
    pools=pd.read_parquet(OUT/'decision_pools.parquet')
    labelcols=[c for c in labels if 'signal' in c]
    pools=pools.merge(labels[['patent_id']+labelcols],on='patent_id',how='left',validate='many_to_one')
    if pools.future_core_signal_1patent.isna().any():raise AssertionError('Missing task labels in unchanged candidate pools')
    focal=pd.read_parquet(ROOT/'datasets/revision_v2/task_focal_core_links.parquet')
    fcols=['focal_core_signal_1patent','focal_core_applicant_signal_1patent',
           'focal_core_postorigin_filing_citing_patents','focal_core_applicant_postorigin_filing_citing_patents']
    pools=pools.merge(focal[['organization_id','year','patent_id']+fcols],on=['organization_id','year','patent_id'],how='left',validate='one_to_one')
    for c in fcols:pools[c]=pools[c].fillna(False if 'signal' in c else 0)
    pools['focal_core_postorigin_filing_signal_1patent']=pools.focal_core_postorigin_filing_citing_patents.ge(1)
    pools['focal_core_applicant_postorigin_filing_signal_1patent']=pools.focal_core_applicant_postorigin_filing_citing_patents.ge(1)
    outcomes=['future_external_signal_2org','future_external_signal_2org2patent',
        'future_applicant_signal_2org','future_examiner_signal_2org',
        'future_core_signal_1patent','future_core_signal_2org','future_core_signal_2org2patent',
        'future_core_applicant_signal_1patent','future_core_examiner_signal_1patent',
        'focal_core_signal_1patent','focal_core_applicant_signal_1patent',
        'focal_core_postorigin_filing_signal_1patent','focal_core_applicant_postorigin_filing_signal_1patent',
        'five_year_external_signal_2org','five_year_applicant_signal_2org','five_year_core_signal_1patent']
    rows=[];opportunities=[];tail=[]
    for (org,year),pool in pools.groupby(['organization_id','year']):
        pool=pool.reset_index(drop=True); lookup={p:i for i,p in enumerate(pool.patent_id)}
        far=pool.distant.to_numpy(bool)
        local=selected.loc[selected.organization_id.eq(org)&selected.year.eq(year)]
        valid=[o for o in outcomes if not o.startswith('five_year_') or year<=2019]
        for model,sg in local.groupby('model'):
            policies={policy:np.asarray([lookup[p] for p in group.sort_values('rank').patent_id],int)
                      for policy,group in sg.groupby('policy')}
            base=policies['topk']
            ordinal=pool['rank_'+model].to_numpy()
            for outcome in valid:
                if pool[outcome].isna().any():raise AssertionError('Incomplete mature task outcome')
                high=pool[outcome].to_numpy(bool)
                for policy,chosen in policies.items():
                    rows.append({'organization_id':org,'year':year,'model':model,'policy':policy,'outcome':outcome,
                                 **metrics(chosen,base,high,far)})
                opportunities.append({'organization_id':org,'year':year,'model':model,'outcome':outcome,
                    'far_pool_n':int(far.sum()),'far_pool_high':int((far&high).sum()),
                    'base_far_high':int((high[base]&far[base]).sum()),
                    'missed_far_high':int((far&high).sum()-(high[base]&far[base]).sum()),
                    'nonfar_pool_high':int((~far&high).sum())})
                if outcome in ['future_core_signal_1patent','future_core_applicant_signal_1patent','focal_core_signal_1patent']:
                    for band,mask in [('rank_1_30',ordinal<=30),('rank_31_100',(ordinal>30)&(ordinal<=100)),
                                      ('rank_101_500',(ordinal>100)&(ordinal<=500)),('rank_501_plus',ordinal>500)]:
                        for boundary,sub in [('far',far),('nonfar',~far)]:
                            ix=mask&sub
                            tail.append({'organization_id':org,'year':year,'model':model,'outcome':outcome,'band':band,'boundary':boundary,
                                'candidate_n':int(ix.sum()),'signal_n':int(high[ix].sum())})
    frame=pd.DataFrame(rows)
    frame.to_parquet(OUT/'decision_task_detail.parquet',index=False)
    summary=summarize(frame,['outcome','model','policy'])
    summary.to_csv(OUT/'decision_task_outcomes.csv',index=False)
    summarize(frame,['outcome','year','model','policy']).to_csv(OUT/'decision_task_annual.csv',index=False)
    opp=pd.DataFrame(opportunities)
    opp.to_csv(OUT/'decision_task_opportunity_detail.csv',index=False)
    opp.groupby(['outcome','model']).agg(n_decisions=('year','size'),mean_far_pool_high=('far_pool_high','mean'),
        mean_base_far_high=('base_far_high','mean'),mean_missed_far_high=('missed_far_high','mean'),
        mean_nonfar_pool_high=('nonfar_pool_high','mean'),fraction_any_missed_far=('missed_far_high',lambda x:float((x>0).mean())),
        fraction_far_signal_supply=('far_pool_high',lambda x:float((x>0).mean()))).to_csv(OUT/'decision_task_opportunities.csv')
    tails=pd.DataFrame(tail).groupby(['outcome','model','band','boundary'])[['candidate_n','signal_n']].sum().reset_index()
    tails['signal_yield']=tails.signal_n/tails.candidate_n
    tails.to_csv(OUT/'decision_task_ranking_tail.csv',index=False)
    # Independent label reconstruction must preserve the original global and applicant results.
    original=pd.read_csv(OUT/'decision_absolute_options.csv')
    audit=summary.loc[summary.outcome.eq('future_external_signal_2org')].merge(original,on=['model','policy'],suffixes=('','_v1'))
    if not np.allclose(audit['T'],audit.T_v1) or not np.allclose(audit['U'],audit.U_v1):raise AssertionError('Task label original-measurement mismatch')
    pools[['organization_id','year','patent_id']+outcomes].to_parquet(OUT/'decision_task_pool_labels.parquet',index=False)
    concentration(selected,pools)
    emit('fixed_list_task_addition_complete',decision_outcome_rows=len(frame),original_global_audit='PASS')

def concentration(selected,pools):
    """Outcome-aware shared-candidate diagnostics, never policy selection."""
    use=selected.merge(pools[['organization_id','year','patent_id','all_high','future_core_signal_1patent']],
                       on=['organization_id','year','patent_id'],validate='many_to_one')
    rows=[];influence=[]
    for (model,policy),group in use.groupby(['model','policy']):
        for outcome in ['all_high','future_core_signal_1patent']:
            for component in ['T','U']:
                hits=group[outcome].to_numpy(bool)&(group.distant.to_numpy(bool) if component=='U' else True)
                counts=group.loc[hits].groupby('patent_id').size().sort_values(ascending=False)
                total=int(counts.sum())
                rows.append({'model':model,'policy':policy,'outcome':outcome,'component':component,
                    'signal_selection_events':total,'unique_signal_patents':len(counts),
                    'top1_event_share':float(counts.head(1).sum()/total) if total else np.nan,
                    'top10_event_share':float(counts.head(10).sum()/total) if total else np.nan,
                    'event_concentration_hhi':float(((counts/total)**2).sum()) if total else np.nan})
        if model!='boosting' or policy not in ['quota_0.3','context_rule_retention_0.9']:continue
        base=use.loc[use.model.eq(model)&use.policy.eq('topk')]
        for outcome in ['all_high','future_core_signal_1patent']:
            def tally(g):
                temp=g.assign(T_event=g[outcome].astype(int),U_event=g[outcome].astype(int)*g.distant.astype(int))
                return temp.groupby('patent_id')[['T_event','U_event']].sum()
            a=tally(group);b=tally(base);change=a.subtract(b,fill_value=0)
            for ordering in ['T_event','U_event']:
                ranked=change[ordering].abs().sort_values(ascending=False).index
                for drop in [1,10]:
                    excluded=ranked[:drop]
                    aa=a.drop(index=excluded,errors='ignore').sum();bb=b.drop(index=excluded,errors='ignore').sum()
                    influence.append({'model':model,'policy':policy,'outcome':outcome,'ranked_by_absolute_net_contribution':ordering,
                        'drop_n':drop,'excluded_patents':'|'.join(excluded),
                        'delta_T_after_drop':float((aa.T_event-bb.T_event)/356),
                        'delta_U_after_drop':float((aa.U_event-bb.U_event)/356),
                        'count_ratio_after_drop':float(aa.T_event/bb.T_event) if bb.T_event else np.nan})
    pd.DataFrame(rows).to_csv(OUT/'decision_candidate_concentration.csv',index=False)
    pd.DataFrame(influence).to_csv(OUT/'decision_candidate_influence.csv',index=False)
    # Requested diagnostic: rank globally signalled *added* patents from boost
    # q30 by event frequency, break ties by ID, then mask those outcomes in all
    # unchanged policy and baseline lists. This is not a search strategy.
    keys=['organization_id','year','patent_id']
    q=use.loc[use.model.eq('boosting')&use.policy.eq('quota_0.3')]
    b=use.loc[use.model.eq('boosting')&use.policy.eq('topk'),keys]
    added=q.merge(b.assign(in_base=True),on=keys,how='left',validate='one_to_one')
    added=added.loc[added.in_base.isna()&added.all_high]
    contributors=added.groupby('patent_id').size().rename('added_signal_events').reset_index()
    contributors=contributors.sort_values(['added_signal_events','patent_id'],ascending=[False,True]).reset_index(drop=True)
    contributors['rank']=np.arange(1,len(contributors)+1)
    contributors.to_csv(OUT/'decision_candidate_added_contributors.csv',index=False)
    requested=[]
    for drop in [1,5,10]:
        excluded=set(contributors.head(drop).patent_id)
        for outcome in ['all_high','future_core_signal_1patent']:
            masked=use[outcome].astype(bool)&~use.patent_id.isin(excluded)
            temp=use.assign(T_event=masked.astype(int),U_event=(masked&use.distant).astype(int))
            sums=temp.groupby(['model','policy'])[['T_event','U_event']].sum()
            for (model,policy),r in sums.iterrows():
                base=sums.loc[(model,'topk')]
                requested.append({'drop_n':drop,'outcome':outcome,'model':model,'policy':policy,
                    'excluded_patents':'|'.join(contributors.head(drop).patent_id),
                    'T_after_mask':r.T_event/356,'U_after_mask':r.U_event/356,
                    'delta_T_after_mask':(r.T_event-base.T_event)/356,
                    'delta_U_after_mask':(r.U_event-base.U_event)/356,
                    'count_ratio_after_mask':r.T_event/base.T_event if base.T_event else np.nan})
    pd.DataFrame(requested).to_csv(OUT/'decision_candidate_added_influence.csv',index=False)

def taskpool_addition():
    """Independently score root's new raw-identity task pools and audit v1 recovery."""
    labels=pd.read_parquet(ROOT/'datasets/revision_v2/task_patent_labels.parquet')
    focal=pd.read_parquet(ROOT/'datasets/revision_v2/task_focal_core_links.parquet')
    outcomes=['future_external_signal_2org','future_applicant_signal_2org','future_examiner_signal_2org',
        'future_external_signal_2org2patent','future_core_signal_1patent','future_core_signal_2org',
        'future_core_applicant_signal_1patent','future_core_examiner_signal_1patent',
        'focal_core_signal_1patent','focal_core_applicant_signal_1patent',
        'focal_core_postorigin_filing_signal_1patent',
        'five_year_external_signal_2org','five_year_applicant_signal_2org','five_year_core_signal_1patent']
    selected_frames=[];pool_frames=[]
    for year in [2018,2019,2020,2021]:
        sel=pd.read_parquet(INPUT_REV/f'taskpool_raw_selected_{year}.parquet')
        pool=pd.read_parquet(INPUT_REV/f'taskpool_raw_pools_{year}.parquet')
        selected_frames.append(sel);pool_frames.append(pool)
    selected=pd.concat(selected_frames,ignore_index=True)
    pools=pd.concat(pool_frames,ignore_index=True)
    oldpools=pd.read_parquet(OUT/'decision_pools.parquet')
    pk=['organization_id','year','patent_id']
    check=pools.loc[pools.relevance.eq('whole_organization'),pk].merge(oldpools[pk],on=pk,how='outer',indicator=True,validate='one_to_one')
    pool_diff=check.loc[check._merge.ne('both')].copy()
    floating_boundary=[]
    if len(pool_diff):
        # The original and reconstructed portfolio row orders can differ in
        # float32 sparse means. Admit only explicitly recorded floor-edge IDs;
        # all actual selected sets still must match exactly below.
        for row in pool_diff.itertuples():
            old=oldpools.loc[oldpools.organization_id.eq(row.organization_id)&oldpools.year.eq(row.year)&oldpools.patent_id.eq(row.patent_id)]
            new=pools.loc[pools.organization_id.eq(row.organization_id)&pools.year.eq(row.year)&pools.patent_id.eq(row.patent_id)&pools.relevance.eq('whole_organization')]
            value=float(old.similarity.iloc[0]) if len(old) else float(new.task_similarity.iloc[0])
            if abs(value-.03)>2e-7:raise AssertionError('Substantive whole-organization raw pool ID mismatch')
            floating_boundary.append({'organization_id':row.organization_id,'year':int(row.year),'patent_id':row.patent_id,
                'side':'v1_only' if len(old) else 'new_only','observed_included_similarity':value,
                'difference_type':'float32 mean row-order floor edge; selected-list recovery separately exact'})
    original=pd.read_parquet(OUT/'decision_selected.parquet')
    newer=selected.loc[selected.relevance.eq('whole_organization')&selected.boundary.eq('subclass_external'),
                       pk+['model','q']].copy()
    newer['policy']=newer.q.map(lambda q:'topk' if q==0 else f'quota_{q:.1f}')
    keys=pk+['model','policy']
    older=original.loc[original.model.isin(newer.model.unique())&original.policy.isin(newer.policy.unique()),keys]
    recovery=newer[keys].merge(older,on=keys,how='outer',indicator=True,validate='one_to_one')
    if not recovery._merge.eq('both').all():raise AssertionError('New whole/subclass lists do not recover v1 IDs')
    # Independent numeric reconstruction of six prechosen core centroids.
    study=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet')
    study['year']=pd.to_datetime(study.patent_date).dt.year
    study=study.sort_values(['year','patent_id'])
    hist=pd.read_parquet(ROOT/'datasets/canonical_v1/study_portfolios.parquet')
    hist['year']=pd.to_datetime(hist.patent_date).dt.year
    audit=[]
    for year in [2018,2021]:
        orgs=sorted(pools.loc[pools.year.eq(year)&pools.relevance.eq('core_task')].organization_id.unique())[:3]
        train=study.loc[study.year.between(2010,year-3)]
        tv=TfidfVectorizer(max_features=20000,min_df=2,max_df=.98,ngram_range=(1,2),stop_words='english',dtype=np.float32,sublinear_tf=True)
        tv.fit(train.patent_title.fillna(''))
        cur=pd.read_parquet(RUN/f'scores_{year}.parquet')
        xc=tv.transform(cur.patent_title.fillna(''))
        ch=hist.loc[hist.year.between(year-5,year-1)&hist.is_core].copy()
        owner=cur.assignee_id.fillna('').str.split('|').map(set).tolist()
        classified=cur.cpc_codes.map(codes).map(bool).to_numpy()
        for org in orgs:
            h=ch.loc[ch.assignee_id.fillna('').str.split('|').map(lambda x:org in x)]
            xh=tv.transform(h.patent_title.fillna(''))
            centroid=normalize(sparse.csr_matrix(np.asarray(xh.mean(axis=0))))
            sim=(xc@centroid.T).toarray().ravel()
            mask=(sim>=.03)&classified&np.asarray([org not in o for o in owner])
            actual=pools.loc[pools.organization_id.eq(org)&pools.year.eq(year)&pools.relevance.eq('core_task')]
            if set(cur.loc[mask,'patent_id'])!=set(actual.patent_id):raise AssertionError('Independent core-centroid pool mismatch')
            actual=actual.merge(cur[['patent_id']].assign(independent_similarity=sim),on='patent_id',validate='one_to_one')
            error=float((actual.task_similarity-actual.independent_similarity).abs().max())
            if error>2e-7:raise AssertionError('Independent core-centroid similarity mismatch')
            audit.append({'year':year,'organization_id':org,'core_history_n':len(h),
                'last_core_history_year':int(h.year.max()),'last_training_year':int(train.year.max()),
                'pool_n':len(actual),'max_absolute_similarity_error':error})
    # Fixed outcome joins. Focal counts are raw-name links, and omitted rows
    # mean zero only because the sparse archive enumerates every nonzero pair.
    selected=selected.merge(labels[['patent_id']+[o for o in outcomes if o in labels]],on='patent_id',validate='many_to_one')
    selected=selected.merge(focal[pk+['focal_core_signal_1patent','focal_core_applicant_signal_1patent',
        'focal_core_postorigin_filing_citing_patents']],on=pk,how='left',validate='many_to_one')
    for col in ['focal_core_signal_1patent','focal_core_applicant_signal_1patent']:
        selected[col]=selected[col].fillna(False).astype(bool)
    selected['focal_core_postorigin_filing_signal_1patent']=selected.focal_core_postorigin_filing_citing_patents.fillna(0).ge(1)
    group=['organization_id','year','relevance','boundary','model','q']
    basekeys=group[:-1]
    details=[]
    for outcome in outcomes:
        s=selected.loc[selected.year.le(2019)] if outcome.startswith('five_year_') else selected
        if s[outcome].isna().any():raise AssertionError('Missing mature task-pool outcome')
        high=s[outcome].astype(bool)
        temp=s[group+['unfamiliar','added']].assign(T=high.astype(int),U=(high&s.unfamiliar).astype(int),
            added_T=(high&s.added).astype(int),added_U=(high&s.added&s.unfamiliar).astype(int))
        values=temp.groupby(group).agg(T=('T','sum'),U=('U','sum'),n_selected=('T','size'),
            far_selected=('unfamiliar','sum'),added_n=('added','sum'),added_T=('added_T','sum'),added_U=('added_U','sum')).reset_index()
        base=values.loc[values.q.eq(0),basekeys+['T','U']].rename(columns={'T':'base_T','U':'base_U'})
        values=values.merge(base,on=basekeys,validate='many_to_one')
        values['removed_n']=values.added_n
        values['removed_T']=values.base_T-(values['T']-values.added_T)
        values['removed_U']=values.base_U-(values['U']-values.added_U)
        values['original_T_surviving']=values['T']-values.added_T
        values['outcome']=outcome
        details.append(values)
    detail=pd.concat(details,ignore_index=True)
    detail.to_parquet(OUT/'decision_taskpool_detail.parquet',index=False)
    summarize(detail,['outcome','relevance','boundary','model','q']).to_csv(OUT/'decision_taskpool_signals.csv',index=False)
    summarize(detail,['outcome','year','relevance','boundary','model','q']).to_csv(OUT/'decision_taskpool_annual.csv',index=False)
    # Numeric recovery cross-check against independent decision reconstruction.
    original_detail=pd.read_parquet(OUT/'decision_detail.parquet')
    t=detail.loc[detail.relevance.eq('whole_organization')&detail.boundary.eq('subclass_external')&detail.outcome.eq('future_external_signal_2org')].copy()
    t['policy']=t.q.map(lambda q:'topk' if q==0 else f'quota_{q:.1f}')
    match=t.merge(original_detail,on=['organization_id','year','model','policy'],suffixes=('','_old'),validate='one_to_one')
    if not (match['T'].eq(match.T_old)&match['U'].eq(match.U_old)&match.added_T.eq(match.added_T_old)&match.removed_T.eq(match.removed_T_old)).all():
        raise AssertionError('Taskpool outcome reconstruction mismatch')
    (OUT/'decision_taskpool_audit.json').write_text(json.dumps({'status':'PASS_WITH_RECORDED_FLOAT32_FLOOR_EDGE' if floating_boundary else 'PASS',
        'whole_pool_id_rows_exactly_common':int(check._merge.eq('both').sum()),'whole_pool_float32_floor_differences':floating_boundary,
        'whole_subclass_selected_id_rows_recovered':len(recovery),'whole_subclass_policy_rows_recovered':len(match),
        'independently_rebuilt_core_centroids':audit,'scope':'Raw-identity new pools only; post-critique fixed scores and lists; no outcome selection',
        'focal_scope':'Raw grant-owner archive links, not observed screening or adoption; postorigin filing is separately labelled.',
        'five_year_scope':'Only 2018 and 2019 grants; 158 historical situations per relevance pool.'},indent=2),encoding='utf-8')
    emit('taskpool_labels_and_audit_complete',outcome_rows=len(detail),whole_pool_recovered=len(check))

def taskpool_bootstrap():
    """Paired organization resampling of 12 task-pool comparisons, 2000 draws."""
    detail=pd.read_parquet(OUT/'decision_taskpool_detail.parquet')
    summary=pd.read_csv(OUT/'decision_taskpool_signals.csv')
    subset=detail.loc[detail.relevance.eq('core_task')&detail.model.eq('boosting')&detail.q.eq(.3)&
        detail.outcome.isin(['future_external_signal_2org','future_applicant_signal_2org','future_core_signal_1patent'])]
    rows=[]
    for (boundary,outcome),g in subset.groupby(['boundary','outcome']):
        stats=g.groupby('organization_id')[['T','U','base_T','base_U','original_T_surviving']].sum().sort_index()
        stats['n']=g.groupby('organization_id').size().reindex(stats.index)
        rng=np.random.default_rng(20260929)
        ix=rng.integers(0,len(stats),size=(2000,len(stats)))
        draws=stats.to_numpy()[ix].sum(axis=1)
        dT=(draws[:,0]-draws[:,2])/draws[:,5]
        dU=(draws[:,1]-draws[:,3])/draws[:,5]
        ratio=draws[:,0]/draws[:,2]
        survival=draws[:,4]/draws[:,2]
        points={'delta_T':float((g['T']-g.base_T).mean()),'delta_U':float((g['U']-g.base_U).mean()),
            'count_ratio':float(g['T'].sum()/g.base_T.sum()),
            'original_signal_survival':float(g.original_T_surviving.sum()/g.base_T.sum())}
        published=summary.loc[summary.relevance.eq('core_task')&summary.model.eq('boosting')&summary.q.eq(.3)&
            summary.boundary.eq(boundary)&summary.outcome.eq(outcome)]
        if len(published)!=1:raise AssertionError('Missing task-pool point summary')
        for key,value in points.items():
            if not np.isclose(value,float(published.iloc[0][key]),rtol=0,atol=1e-12):raise AssertionError('Bootstrap point mismatch')
        row={'boundary':boundary,'outcome':outcome,'model':'boosting','relevance':'core_task','q':.3,
            'n_decisions':len(g),'n_organizations':len(stats),'repeats':2000,'seed':20260929,**points}
        for key,distribution in [('delta_T',dT),('delta_U',dU),('count_ratio',ratio),('original_signal_survival',survival)]:
            row[key+'_ci_low']=float(np.quantile(distribution,.025));row[key+'_ci_high']=float(np.quantile(distribution,.975))
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'decision_taskpool_bootstrap.csv',index=False)
    (OUT/'decision_taskpool_bootstrap_notes.json').write_text(json.dumps({'scope':'Post-critique paired organization bootstrap, fixed task pools/scores/lists',
        'sampling':'Resample organizations with replacement, retain all their historical situations; divide differences by sampled number of situations; calculate R and S as pooled ratios.',
        'n_comparisons':12,'repeats':2000,'seed':20260929,'point_audit':'PASS all four point metrics against decision_taskpool_signals.csv',
        'limits':'Shared candidate patents and only four historical years remain. Organization resampling does not resolve cross-organization shared outcomes, identify behavior, or provide future-environment transportability.'},indent=2),encoding='utf-8')
    emit('taskpool_paired_bootstrap_complete',comparisons=len(rows),point_audit='PASS')

def taskpool_opportunities():
    """Supply and missed-signal denominators for the new task-centered pools."""
    pools=pd.concat([pd.read_parquet(INPUT_REV/f'taskpool_raw_pools_{year}.parquet') for year in [2018,2019,2020,2021]],ignore_index=True)
    labels=pd.read_parquet(ROOT/'datasets/revision_v2/task_patent_labels.parquet')
    outcomes=['future_external_signal_2org','future_applicant_signal_2org','future_core_signal_1patent','focal_core_signal_1patent']
    pools=pools.merge(labels[['patent_id']+outcomes[:3]],on='patent_id',validate='many_to_one')
    focal=pd.read_parquet(ROOT/'datasets/revision_v2/task_focal_core_links.parquet')
    pk=['organization_id','year','patent_id']
    pools=pools.merge(focal[pk+['focal_core_signal_1patent']],on=pk,how='left',validate='many_to_one')
    pools['focal_core_signal_1patent']=pools.focal_core_signal_1patent.fillna(False).astype(bool)
    detail=pd.read_parquet(OUT/'decision_taskpool_detail.parquet')
    base=detail.loc[detail.q.eq(0)&detail.outcome.isin(outcomes)]
    group=['organization_id','year','relevance']
    rows=[]
    for boundary in ['subclass_external','text_quartile','core_newgroup','core_newpair']:
        for outcome in outcomes:
            high=pools[outcome].astype(bool)
            temp=pools[group].assign(pool_high=high.astype(int),far_high=(high&pools[boundary]).astype(int),far_n=pools[boundary].astype(int))
            denoms=temp.groupby(group).agg(pool_n=('pool_high','size'),pool_high=('pool_high','sum'),far_pool_high=('far_high','sum'),far_pool_n=('far_n','sum')).reset_index()
            b=base.loc[base.boundary.eq(boundary)&base.outcome.eq(outcome)]
            x=b.merge(denoms,on=group,validate='many_to_one')
            x['base_far_high']=x['U'];x['missed_far_high']=x.far_pool_high-x['U']
            x['base_T']=x['T']
            rows.append(x[group+['boundary','model','outcome','pool_n','pool_high','far_pool_n','far_pool_high','base_T','base_far_high','missed_far_high']])
    frame=pd.concat(rows,ignore_index=True)
    frame.to_csv(OUT/'decision_taskpool_opportunity_detail.csv',index=False)
    records=[]
    for key,g in frame.groupby(['relevance','boundary','model','outcome']):
        records.append(dict(zip(['relevance','boundary','model','outcome'],key),n_decisions=len(g),
            mean_pool_n=float(g.pool_n.mean()),mean_pool_high=float(g.pool_high.mean()),mean_far_pool_n=float(g.far_pool_n.mean()),
            mean_far_pool_high=float(g.far_pool_high.mean()),mean_base_far_high=float(g.base_far_high.mean()),
            mean_missed_far_high=float(g.missed_far_high.mean()),fraction_far_signal_supply=float(g.far_pool_high.gt(0).mean()),
            fraction_any_missed_far=float(g.missed_far_high.gt(0).mean()),
            pooled_far_signal_recall=float(g.base_far_high.sum()/g.far_pool_high.sum()) if g.far_pool_high.sum() else np.nan))
    pd.DataFrame(records).to_csv(OUT/'decision_taskpool_opportunities.csv',index=False)
    emit('taskpool_opportunity_denominators_complete',rows=len(frame))

def horizon_matched():
    """Compare 3/5-year labels within the identical 2018-19 historical situations."""
    frame=pd.read_parquet(OUT/'decision_taskpool_detail.parquet')
    frame=frame.loc[frame.year.le(2019)&frame.outcome.isin(['future_external_signal_2org','future_applicant_signal_2org',
        'future_core_signal_1patent','five_year_external_signal_2org','five_year_applicant_signal_2org','five_year_core_signal_1patent'])]
    summary=summarize(frame,['outcome','relevance','boundary','model','q'])
    summary['horizon_years']=summary.outcome.str.startswith('five_year_').map({True:5,False:3})
    summary.to_csv(OUT/'decision_taskpool_horizon_matched.csv',index=False)
    emit('matched_horizon_complete',rows=len(summary),n_situations=158)

def report():
    """Compact Chinese record of verified new decision evidence and its limits."""
    absolute=pd.read_csv(OUT/'decision_absolute_options.csv')
    task=pd.read_csv(OUT/'decision_taskpool_signals.csv')
    boot=pd.read_csv(OUT/'decision_taskpool_bootstrap.csv')
    def markdown(frame):
        columns=list(frame.columns)
        lines=['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
        for row in frame.itertuples(index=False,name=None):
            values=[f'{v:.4f}' if isinstance(v,(float,np.floating)) else str(v) for v in row]
            lines.append('| '+' | '.join(values)+' |')
        return '\n'.join(lines)
    main=task.loc[task.relevance.eq('core_task')&task.model.eq('boosting')&task.q.eq(.3)&
        task.outcome.isin(['future_external_signal_2org','future_applicant_signal_2org','future_core_signal_1patent']),
        ['boundary','outcome','T','U','added_T','removed_T','delta_T','delta_U','count_ratio','original_signal_survival']]
    options=absolute.loc[absolute.model.isin(['boosting','ridge','popularity'])&absolute.policy.isin(['topk','quota_0.3']),
        ['model','policy','T','U','added_T','removed_T','count_ratio','original_signal_survival']]
    uncertainty=boot[['boundary','outcome','delta_T','delta_T_ci_low','delta_T_ci_high','delta_U','delta_U_ci_low','delta_U_ci_high']]
    text='''# 批评意见后的决策分析与独立核验（2026-09-30）

这轮扩展保留原v1分数、名单及开发期规则，明确属于收到批评后的研究扩展，不冒称原先预设。主要增量是任务相关结果、不同知识边界、原有线索置换、强排序器绝对方案、引用来源与时间窗口共同进入决策评价。组织—年份仍是历史记录重建的筛选情景，不是观察到的企业阅读、搜索或采用行为。

## 1. 原研究恢复与新任务池核验

- 原K30所有四个排序器及31个确定性策略组合，共11,036策略—情景行，T/U/池规模逐项恢复；boost所有保存名单逐ID核对。
- 保存331,080入选事件、928,668组织—专利候选事件。原pool包含356情景，114组织；重复候选不是独立创新事件。
- root新whole-organization/subclass原名单160,200行、5,340策略行，入选ID及T/U/gross完全复现。
- 新whole池与原928,668候选事件有928,667严格相同。唯一差异是Ford2020专利10665839，原cosine=.03000003472，float32稀疏均值求和的行序差使新池在.03边缘排除它；实际入选ID及所有T/U/gross未变。不能宣称全部pool ID严格相同。
- 六个预先按年份2018/2021、组织名字母前三选定的core centroid独立重建，pool ID精确相同，similarity最大差0；历史均截至t−1，词表仅用已成熟t−3队列。

## 2. 主结果应从“配额增陌生信号”改为“跨哪种记录边界、交换什么信号”

下表是core-task centroid池、boosting、q=.30，356相同历史情景；T为名单目标信号数，U为其中符合该边界的信号数。前三种结果为：一般外部≥2组织引用；申请人来源≥2组织引用；至少1个后续电池热管理核心授权专利引用。最后一种是档案任务连接，不是组织技术采用。

'''+markdown(main)+'''

关键事实：外部四字符子类跨越的core信号净损失.3202，同时增加边界core信号.1404；core新子类组合的core信号净增1.4466，同时一般信号净增.1152、申请人信号净损失.1517。core_newpair是核心候选专利中、该组织prior核心专利组合未见的四字符分类对，比较集合不含非core业务中已经出现的组合，故是task-local记录重组边界；core_newgroup是全组织历史中未见的精细电池热CPC组。两者不是同一whole-organization知识新颖性指标，也不要都说成精细组对。分类迁移、CPC历史缺失及既有知识未专利化会限制“新”的解释；必须称记录中的分类边界。

12格paired组织bootstrap2000（原seed20260929）均已运行，四个point量对汇总表精度1e−12核对。以下是ΔT/ΔU的95%区间；R/S区间见CSV。区间仅组织重抽样，同一专利跨组织共享、只有四年环境仍未解决。

'''+markdown(uncertainty)+'''

## 3. 强基准、gross置换与偏好情景

以下绝对方案属于原whole-org池，不是新增core-task池。保持原boost为先前指定分析，不把Ridge改写成事前主模型。

'''+markdown(options)+'''

- boost q30平均新增.9101信号，移除1.3258信号，净损失.4157；总数量比95.3253%，原名单信号生存85.0916%。两个保留概念必须并列。
- 原池考察的T/U绝对均值非支配点均属于Ridge，不能将boost内部约5%价格表述为所有管理者不可避免的成本。这是描述性方案比较，无统计最优性。
- V=T+(λ−1)U只是假设熟悉信号权重1、陌生信号λ；boost q30内部break-even λ=1.4568，context90=1.4753，Ridge q30=1.6188。λ1/1.5/2/3下，原池历史最高均值对应Ridge topK/q10/context90/q40；并未测得真实偏好。
- 同成本预算30、far文档倍率1/1.5/2，原quota reservation-first顺序的boost q30 break-even λ=1.4568/2.4669/3.5147。未观测真实阅读顺序；保留相同30篇集合内按ranker score排序的另一执行情景，其λ=1.4568/2.0000/2.8849。不同顺序反映执行不确定性，不是筛选时间测量。

## 4. 引用来源为何改变净价格

原池boost q30新增.9101信号由applicant达到≥2组织的.4129和未达到该applicant门槛的.4972构成；移除1.3258由.2500和1.0758构成。因此applicant净+.1629，all-only净−.5787，一般净−.4157。all-only不代表纯examiner引用，可能含1个申请人组织或混合来源。另行examiner≥2结果见task输出，不和applicant结果相加，因为两事件重叠。

新core-task池core_newpair的一般净变化+.1152（95%区间跨0），applicant净−.1517（区间−.2240至−.0850），任务core净+1.4466（1.3217至1.5703）。不存在统一的“探索价格”：记录边界与测量对象会改变交换。

## 5. 可利用信号分母与非偏见解释

原池平均有17.6798个四字符跨界的一般信号，boost topK仅取.7697、漏16.9101；98.5955%情景有漏筛。far池平均信号率.0614低于nonfar .0811，rank尾部也递减，不能把入选少自动称熟悉性偏见。

在新的core-task池，外部子类far中core后续连接平均只有1.0983个，39.89%情景有供给；core_newpair平均18.2247个，100%有供给，topK取1.1798、漏17.0449。core_newgroup平均30.3736个、99.44%有供给。任务连接不是由增加位置自动保证，分母显示不同边界对应实质不同的技术供给。

## 6. 公平随机对照、MMR自身目标与共享候选

- matched random锁住原topK所有既有陌生项、确定性q30同一被移除对象和同一实际置换数；从base外far池不放回抽500次。boost实际置换6.5646篇、移除1.3258信号。确定性新增.9101，random平均.3639（解析期望.3633），差.5463。
- 随机500次总体均值的2.5/97.5分位不是实证效应置信区间，只是random comparator的Monte Carlo变化。
- 真实selected title pairwise cosine：topK=.04082、q30=.03315、MMR.9=.01703、MMR.7=.01240、MMR.5=.00982。MMR确实实现较强文本去冗余，其组织陌生性未增加不能据此说去冗余失败。
- boost q30新增一般信号324次来自90件不同专利；top10贡献132次（40.74%）。原topK的3166信号事件来自218件专利；q30的3018来自264件。
- 按q30新增信号频次↓、ID↑选择top1/5/10，事后将这些patent的signal在所有固定名单与基准中置0：boost q30 ΔU=.8258/.6517/.5393，ΔT=−.5000/−.6742/−.7725，R=.9437/.9240/.9124。正向边界信号并非单个对象支撑，但幅度有共享对象集中度。

## 7. 五年及focal组织关联

- 五年只允许2018–19成熟队列，158情景。matched-horizon表同时汇总这些相同情景三年结果，防止把样本变化当时间变化。
- core-task/newpair/applicant ΔT：同158情景3年−.0506，5年+.7785；一般+.7722→+1.3734，core+1.5190→+1.7215。引用窗口本身可改变价格方向，五年不是商业长期回报。
- focal-core记录极稀疏：core-task topK13个、newpair q30=14个入选事件；postorigin filing core link4→6个。没有足够证据证明组织特定收益，绝不能用百分比包装成强主发现；正文使用绝对事件数，并限定为后续授权所有者与引用档案连接。

## 8. 输出与复跑

脚本：scripts/revision_decision_analysis.py。读取v1及root/task agent稳定输入；所有派生输出均为results/revision_v2/decision_*，旧v1不改。

核心文件：decision_taskpool_signals.csv、decision_taskpool_bootstrap.csv、decision_taskpool_annual.csv、decision_taskpool_opportunities.csv、decision_taskpool_horizon_matched.csv、decision_taskpool_audit.json。
原池补充：decision_absolute_options.csv、decision_citation_gross.csv、decision_cost_scenarios.csv、decision_cost_score_order_scenarios.csv、decision_matched_random.csv、decision_redundancy.csv、decision_candidate_added_influence.csv；完整固定名单decision_selected.parquet及pools/detail保留。

复跑顺序：--output <D盘新目录> --repeats 500（不覆盖已完成名单）；随后每步保持同一--output，再--refresh-cost；--score-cost；task labels完成后--task-only；root新task pools完成后--task-pools；--task-pool-bootstrap；--task-pool-opportunities；--matched-horizon；--report。

本报告核验历史筛选结果与档案连接。论文主张应限定在innovation intelligence流程中的授权专利筛选决策，不推断人类真实注意力、工具采用、知识吸收或企业创新因果改善。
'''
    (ROOT/'research/revision_decision_analysis.md').write_text(text,encoding='utf-8')
    audit=json.loads((OUT/'decision_taskpool_audit.json').read_text())
    for diff in audit.get('whole_pool_float32_floor_differences',[]):
        if diff['patent_id']=='10665839':diff['side']='v1_only'
    (OUT/'decision_taskpool_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    emit('decision_report_written',path='research/revision_decision_analysis.md')

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--repeats',type=int,default=500)
    parser.add_argument('--output',type=Path,default=OUT,help='Fresh D-drive output directory for replay; taskpool source remains results/revision_v2')
    parser.add_argument('--task-only',action='store_true')
    parser.add_argument('--refresh-cost',action='store_true',help='Recompute budget-matched costs from saved unchanged lists, no TFIDF fitting')
    parser.add_argument('--score-cost',action='store_true',help='Alternative cost-prefix order: score-ranked within the unchanged selected set')
    parser.add_argument('--task-pools',action='store_true',help='Score and audit the independently supplied raw task-pool lists')
    parser.add_argument('--task-pool-bootstrap',action='store_true',help='Paired organization bootstrap for 12 core-task boost q30 comparisons')
    parser.add_argument('--task-pool-opportunities',action='store_true',help='Signal supply and missed-signal denominators for new task pools')
    parser.add_argument('--matched-horizon',action='store_true',help='Compare 3/5-year labels in identical 2018-19 situations')
    parser.add_argument('--report',action='store_true',help='Write the Chinese verified decision-analysis report')
    args=parser.parse_args()
    OUT=args.output.resolve()
    if not OUT.is_relative_to(ROOT):raise ValueError('Derived outputs must remain in the working project')
    if args.report:report()
    elif args.matched_horizon:horizon_matched()
    elif args.task_pool_opportunities:taskpool_opportunities()
    elif args.task_pool_bootstrap:taskpool_bootstrap()
    elif args.task_pools:taskpool_addition()
    elif args.score_cost:
        costs=cost_scenarios(pd.read_parquet(OUT/'decision_selected.parquet'),pd.read_parquet(OUT/'decision_pools.parquet'),score_order=True)
        costs.to_parquet(OUT/'decision_cost_score_order_detail.parquet',index=False)
        summarize(costs,['unfamiliar_document_cost','model','policy']).to_csv(OUT/'decision_cost_score_order_scenarios.csv',index=False)
        emit('score_order_budget_costs_complete',rows=len(costs))
    elif args.refresh_cost:
        costs=cost_scenarios(pd.read_parquet(OUT/'decision_selected.parquet'),pd.read_parquet(OUT/'decision_pools.parquet'))
        costs.to_parquet(OUT/'decision_cost_detail.parquet',index=False)
        summarize(costs,['unfamiliar_document_cost','model','policy']).to_csv(OUT/'decision_cost_scenarios.csv',index=False)
        audit=json.loads((OUT/'decision_audit.json').read_text())
        audit['cost_reference']='Within each multiplier, equally budget-truncated topk list of the same ranker'
        (OUT/'decision_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
        emit('budget_matched_costs_complete',rows=len(costs))
    elif args.task_only:task_addition()
    else:analyse(args.repeats)
if __name__=='__main__':main()
