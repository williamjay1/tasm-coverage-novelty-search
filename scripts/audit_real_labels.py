"""Independent real-label audit: pandas/Python sets, no adapter SQL reuse.

Reads inputs only. Writes the assigned Markdown report, not research datasets.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import collections,datetime as dt,hashlib,json,pathlib,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

LABELS=['early_external_attention','future_external_attention','early_applicant_attention','future_applicant_attention','future_external_citing_patents','early_disambig_attention','future_disambig_attention']
FUTURE=[x for x in LABELS if x.startswith('future_')]
SEED=20260929

def log(event,**data):print(json.dumps({'event':event,**data},default=str),flush=True)
def read(name,columns=None):return pq.read_table(ROOT/'datasets'/name,columns=columns,use_threads=False).to_pandas()
def clean(value):return '' if value is None or pd.isna(value) else str(value).strip()
def owners(value):return {x for x in clean(value).split('|') if x}
def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def value_repr(v):return 'NA' if v is None or pd.isna(v) else str(int(v))

def main():
    started=time.time()
    can=read('canonical_v1/study_patents.parquet',['patent_id','patent_date','application_id','assignee_id','disambig_assignee_id']+LABELS)
    domain=read('patent_domain.parquet',['patent_id','patent_date','application_id','assignee_id','disambig_assignee_id'])
    cites=read('patent_citations.parquet',['citing_id','cited_id','citing_date','citation_category','citing_assignee_id','citing_disambig_assignee_id','citing_application_id','cited_application_id'])
    can['patent_date']=pd.to_datetime(can.patent_date)
    domain['patent_date']=pd.to_datetime(domain.patent_date)
    cites['citing_date']=pd.to_datetime(cites.citing_date)
    can['year']=can.patent_date.dt.year
    cby=can.set_index('patent_id')
    dby=domain.set_index('patent_id')
    failures=[]
    expected_candidates=domain[domain.assignee_id.map(clean).ne('')].copy()
    expected_candidates['application_key']=[('APPLICATION:'+clean(a)) if clean(a) else ('GRANT:'+str(p)) for p,a in zip(expected_candidates.patent_id,expected_candidates.application_id)]
    expected_candidates=expected_candidates.sort_values(['patent_date','patent_id']).drop_duplicates('application_key',keep='first')
    missing=set(expected_candidates.patent_id)-set(can.patent_id)
    extra=set(can.patent_id)-set(expected_candidates.patent_id)
    if missing or extra:failures.append(f'Candidate set mismatch: missing={len(missing)}, extra={len(extra)}')
    if len(can)!=can.patent_id.nunique():failures.append('Canonical patent_id duplicate')
    global_checks={
      'canonical_candidates':len(can),'expected_candidates':len(expected_candidates),'candidate_missing':len(missing),'candidate_extra':len(extra),
      'mature_candidates':int((can.year<=2021).sum()),'censored_candidates':int((can.year>2021).sum()),
      'mature_missing_future_cells':int(can.loc[can.year<=2021,FUTURE].isna().sum().sum()),
      'censored_nonmissing_future_cells':int(can.loc[can.year>2021,FUTURE].notna().sum().sum()),
      'negative_label_cells':int((can[LABELS]<0).sum().sum()),
      'applicant_greater_than_all_future':int((can.future_applicant_attention>can.future_external_attention).sum()),
      'applicant_greater_than_all_early':int((can.early_applicant_attention>can.early_external_attention).sum())}
    for key in ['mature_missing_future_cells','censored_nonmissing_future_cells','negative_label_cells','applicant_greater_than_all_future','applicant_greater_than_all_early']:
        if global_checks[key]:failures.append(f'Global label invariant failed: {key}={global_checks[key]}')
    # Build complete per-candidate edge lists from the source edge table, not
    # only the rows that the adapter considered external.
    grouped=collections.defaultdict(list)
    pools=collections.defaultdict(set)
    coverage=collections.defaultdict(collections.Counter)
    for e in cites.itertuples(index=False):
        if e.cited_id not in cby.index or e.citing_date>pd.Timestamp('2024-12-31'):continue
        r=cby.loc[e.cited_id]
        ro=owners(e.citing_assignee_id); target=owners(r.assignee_id)
        overlap=bool(ro & target)
        same_app=bool(clean(e.citing_application_id) and clean(r.application_id) and clean(e.citing_application_id)==clean(r.application_id))
        category=clean(e.citation_category).lower()
        grouped[e.cited_id].append(e)
        co=coverage[int(r.year)];co['edges']+=1;co['known_owner_edges']+=bool(ro);co['overlapping_owner_edges']+=overlap
        co['same_application_edges']+=same_app;co['before_cited_grant_edges']+=e.citing_date<r.patent_date;co['applicant_edges']+='applicant' in category
        if overlap and len(ro)>1 and ro-target:pools['mixed_coowner_self_edge'].add(e.cited_id)
        if not overlap and len(ro)>1:pools['external_multiowner_edge'].add(e.cited_id)
        if not ro:pools['unknown_citing_owner'].add(e.cited_id)
        if e.citing_date.year in [int(r.year)+3,int(r.year)+4]:pools['window_end_or_after'].add(e.cited_id)
    reported_coverage=read('canonical_v1/citation_coverage.parquet').set_index('year')
    coverage_mismatches=[]
    for year in sorted(set(coverage)|set(reported_coverage.index)):
        for column in ['edges','known_owner_edges','overlapping_owner_edges','same_application_edges','before_cited_grant_edges','applicant_edges']:
            expected=int(coverage[year][column]);actual=int(reported_coverage.loc[year,column]) if year in reported_coverage.index else 0
            if expected!=actual:coverage_mismatches.append((year,column,expected,actual))
    if coverage_mismatches:failures.append(f'Coverage table mismatch: {coverage_mismatches}')
    rng=np.random.default_rng(SEED)
    selected={}
    allocation=collections.Counter()
    def take(pool,n,reason):
        pool=sorted(set(pool)-set(selected))
        if not pool:return
        for pid in rng.choice(pool,size=min(n,len(pool)),replace=False).tolist():selected[pid]=reason;allocation[reason]+=1
    for year in [2010,2015,2021]:
        take(can.loc[(can.year==year)&can.future_external_attention.eq(0),'patent_id'],4,f'{year}_future_zero')
        take(can.loc[(can.year==year)&can.future_external_attention.gt(0),'patent_id'],4,f'{year}_future_positive')
    in2022=set(can.loc[can.year.eq(2022),'patent_id'])
    take(in2022 & set(grouped),4,'2022_censored_with_edges')
    take(in2022-set(grouped),4,'2022_censored_without_edges')
    take(pools['mixed_coowner_self_edge'],4,'mixed_coowner_self_edge')
    take(pools['external_multiowner_edge'],4,'external_multiowner_edge')
    take(can.loc[(can.year<=2021)&can.early_external_attention.gt(0),'patent_id'],4,'early_positive')
    take(pools['unknown_citing_owner'],4,'unknown_citing_owner')
    take(can.loc[(can.year<=2021)&can.future_disambig_attention.notna()&can.future_disambig_attention.ne(can.future_external_attention),'patent_id'],4,'raw_disambig_difference')
    take(pools['window_end_or_after'],4,'window_end_or_after')
    if len(selected)<56:take(can.loc[can.year.isin([2010,2015,2021,2022]),'patent_id'],56-len(selected),'supplementary')
    assert 40<=len(selected)<=60,len(selected)
    log('sample_fixed',n=len(selected),allocation=allocation,coverage_checked=len(cites))
    comparisons=[];coowner_examples=[];edge_diagnostics=collections.Counter()
    for pid,reason in selected.items():
        r=dby.loc[pid];year=int(r.patent_date.year)
        primary=owners(r.assignee_id);disambig=owners(r.disambig_assignee_id)
        early_end=dt.date(year,12,31);future_start=dt.date(year+1,1,1);future_end=dt.date(year+3,12,31)
        original_date=r.patent_date.date()
        sets={k:set() for k in LABELS}
        for e in grouped[pid]:
            when=e.citing_date.date();ro=owners(e.citing_assignee_id);di=owners(e.citing_disambig_assignee_id)
            same_app=bool(clean(e.citing_application_id) and clean(r.application_id) and clean(e.citing_application_id)==clean(r.application_id))
            category=clean(e.citation_category).lower();edge_diagnostics['sample_edges']+=1
            if not ro:edge_diagnostics['unknown_raw_owner_edges']+=1
            if when<original_date:edge_diagnostics['pregrant_edges']+=1
            if same_app:edge_diagnostics['same_application_edges']+=1
            if ro & primary:
                edge_diagnostics['overlapping_raw_owner_edges']+=1
                if len(ro)>1 and ro-primary and len(coowner_examples)<6:
                    coowner_examples.append({'cited_id':pid,'citing_id':e.citing_id,'citing_owners':sorted(ro),'cited_owners':sorted(primary),'whole_link_excluded':True})
            if when<original_date or same_app:continue
            early=original_date<=when<=early_end;future=future_start<=when<=future_end
            # Any common raw owner disqualifies the entire citing grant edge,
            # even if another co-owner on that same edge is external.
            if ro and not (ro & primary):
                if early:sets['early_external_attention'].update(ro)
                if future:sets['future_external_attention'].update(ro);sets['future_external_citing_patents'].add(e.citing_id)
                if 'applicant' in category:
                    if early:sets['early_applicant_attention'].update(ro)
                    if future:sets['future_applicant_attention'].update(ro)
            if disambig and di and not (di & disambig):
                if early:sets['early_disambig_attention'].update(di)
                if future:sets['future_disambig_attention'].update(di)
        expected={name:len(sets[name]) for name in LABELS}
        if year>2021:
            for name in FUTURE:expected[name]=None
        if not disambig:
            expected['early_disambig_attention']=None;expected['future_disambig_attention']=None
        actual={name:cby.loc[pid,name] for name in LABELS}
        bad=[name for name in LABELS if not ((expected[name] is None and pd.isna(actual[name])) or (expected[name] is not None and not pd.isna(actual[name]) and float(actual[name])==expected[name]))]
        if bad:failures.append(f'{pid}: mismatched labels {bad}; expected={expected}; actual={actual}')
        comparisons.append({'patent_id':pid,'year':year,'stratum':reason,'source_edges':len(grouped[pid]),'expected':expected,'actual':actual,'mismatches':bad})
    log('labels_recomputed',candidates=len(comparisons),label_cells=len(comparisons)*len(LABELS),mismatches=len(failures))
    # Independent source-edge completeness check. Scan every original TSV row,
    # retaining only the fixed sample IDs; no source query function is reused.
    work=ROOT/'datasets'/'patent_work'
    source_edges=[];source_rows=0
    csv_args=dict(sep='\t',dtype=str,keep_default_na=False,chunksize=500000,engine='c',on_bad_lines='error')
    for i,chunk in enumerate(pd.read_csv(work/'g_us_patent_citation.tsv',usecols=['patent_id','citation_patent_id','citation_category'],**csv_args)):
        source_rows+=len(chunk)
        keep=chunk[chunk.citation_patent_id.isin(selected)]
        if len(keep):source_edges.extend(keep.itertuples(index=False,name=None))
        if i%40==0:log('original_citation_scan',rows=source_rows,retained=len(source_edges))
    citing_needed={x[0] for x in source_edges};grant_meta={}
    for chunk in pd.read_csv(work/'g_patent.tsv',usecols=['patent_id','patent_type','patent_date','withdrawn'],**csv_args):
        keep=chunk[chunk.patent_id.isin(citing_needed)]
        for row in keep.itertuples(index=False):grant_meta[row.patent_id]=(row.patent_type,row.patent_date,row.withdrawn)
    expected_source=set();filtered_nonutility=0;missing_source_metadata=0
    for citing,cited,category in source_edges:
        if citing not in grant_meta:missing_source_metadata+=1;continue
        kind,date,withdrawn=grant_meta[citing]
        if kind!='utility' or withdrawn!='0' or date>'2024-12-31':filtered_nonutility+=1;continue
        expected_source.add((citing,cited,clean(category),date))
    provided_source={(str(e.citing_id),str(e.cited_id),clean(e.citation_category),e.citing_date.strftime('%Y-%m-%d')) for e in cites[cites.cited_id.isin(selected)].itertuples(index=False)}
    missing_edges=expected_source-provided_source;extra_edges=provided_source-expected_source
    if missing_edges or extra_edges:failures.append(f'Original edge completeness failed: missing={len(missing_edges)}, extra={len(extra_edges)}')
    log('original_edges_checked',source_rows=source_rows,selected_raw_rows=len(source_edges),expected_edges=len(expected_source),provided_edges=len(provided_source),missing=len(missing_edges),extra=len(extra_edges))
    sources={name:file_hash(ROOT/'datasets'/name) for name in ['canonical_v1/study_patents.parquet','patent_domain.parquet','patent_citations.parquet','canonical_v1/citation_coverage.parquet']}
    status='PASS' if not failures else 'FAIL'
    lines=['# 真实标签独立核验', '',f'核验时间：{dt.datetime.now(dt.timezone.utc).isoformat()}。结论：**{status}**。', '',
      '本次只核验候选集合、真实引用标签与观测完整性；未读取任何政策排名、模型胜负或政策效应。使用 paper-verification 技能的数值追溯和代码—定义核验模块。', '',
      '## 方法与抽样','',
      f'固定种子 {SEED}，抽取 {len(selected)} 个真实候选。分层使用标签零/正值仅服务核验覆盖，不作模型选择。独立读取原始领域表和引用子集，以 pandas 逐记录遍历及 Python 集合复算；未调用 prepare_study_data.py 的函数或 SQL。', '',
      '早期窗口为被引专利授权日至当年12月31日；后续窗口为次年1月1日至授权年后三年12月31日。主标签逐边排除未知引用方组织、任何共有组织及相同申请，再累计不同外部组织名称。申请人标签进一步限制来源类别。消歧敏感性独立使用消歧ID交集与集合。2022年及以后未来标签应为空，不将已观测部分窗口当完整三年结果。', '',
      '| 抽样层 | 数量 |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in allocation.items()]
    lines += ['', '## 全量结构与覆盖检查', '', '| 检查 | 实测 |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in global_checks.items()]
    lines += [f'| 全年候选引用覆盖统计差异项 | {len(coverage_mismatches)} |',f'| 样本标签比较单元数 | {len(comparisons)*len(LABELS)} |',f'| 样本引用边 | {edge_diagnostics["sample_edges"]} |',f'| 样本中未知原始组织边 | {edge_diagnostics["unknown_raw_owner_edges"]} |',f'| 样本中共有组织边 | {edge_diagnostics["overlapping_raw_owner_edges"]} |',f'| 样本中同申请边 | {edge_diagnostics["same_application_edges"]} |',f'| 样本中授权前引用边 | {edge_diagnostics["pregrant_edges"]} |','',
      '## 原始引用边完整性','',
      f'对已由校验通过的 ZIP 原样解压所得引用 TSV 顺序扫描全部 {source_rows:,} 行，保留固定样本的 {len(source_edges):,} 条原始记录，再从原始专利元数据重建 utility、withdrawn=0、截至2024-12-31的引用方限制。预期有效不同边 {len(expected_source):,}，交付引用子集对应边 {len(provided_source):,}；缺失 {len(missing_edges)}，多余 {len(extra_edges)}。因专利类型/撤回/日期限制排除的原始记录 {filtered_nonutility}，未匹配引用方元数据记录 {missing_source_metadata}。这是对固定样本所有原始边的检查，不是只抽取其中部分边。', '',
      '## 逐候选结果','',
      '向量顺序：early raw / future raw / early applicant / future applicant / future citing patents / early disambiguated / future disambiguated。NA 表示右删失或缺失所需机构身份。', '',
      '| 专利 | 年 | 分层 | 输入边 | 独立复算向量 | Canonical向量 | 比较 |','|---|---:|---|---:|---|---|---|']
    for row in comparisons:
        ex='/'.join(value_repr(row['expected'][k]) for k in LABELS);ac='/'.join(value_repr(row['actual'][k]) for k in LABELS)
        lines.append(f'| {row["patent_id"]} | {row["year"]} | {row["stratum"]} | {row["source_edges"]} | {ex} | {ac} | {"FAIL" if row["mismatches"] else "PASS"} |')
    lines += ['', '## 共同权利人排除实例','']
    for e in coowner_examples:
        lines.append(f'- 被引 {e["cited_id"]}，引用 {e["citing_id"]}：被引组织 {", ".join(e["cited_owners"])}；引用组织 {", ".join(e["citing_owners"])}。存在交集，整条引用排除，不计其余共同权利人为新的外部组织。')
    lines += ['', '## 问题与边界','']
    lines += [f'- {x}' for x in failures] if failures else ['未发现真实标签构造错误；抽样标签、全量候选/删失约束、覆盖统计及固定样本原始边完整性均通过。']
    lines += ['', '此核验不证明引用等于企业实际关注或收益，不消除名字别名和专利家族限制；也不替代专家内容效度评估。研究中的同申请边实际为零，本次不能据此声称已在真实正例上验证该排除分支；只能核对其逻辑及未发生误排。分类和原始表校验已有独立数据审计，本报告不重复声称重新验证所有文本及全部专利实体关系。', '', '## 追溯信息','',f'执行时间约 {time.time()-started:.1f} 秒；审计脚本 SHA-256：`{file_hash(pathlib.Path(__file__))}`。', '']
    lines += [f'- `{name}`：`{digest}`' for name,digest in sources.items()]
    if missing_edges or extra_edges:lines += ['', '原始边差异示例：', '```json',json.dumps({'missing':sorted(missing_edges)[:20],'extra':sorted(extra_edges)[:20]},ensure_ascii=False,indent=2),'```']
    target=ROOT/'research'/'real_label_audit.md'
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    log('audit_complete',status=status,failures=failures,report=str(target),seconds=round(time.time()-started,1))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
