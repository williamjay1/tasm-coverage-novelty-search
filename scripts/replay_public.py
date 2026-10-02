"""Run analysis in a fresh working copy, never over retained evidence."""
from pathlib import Path
import argparse,datetime,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
COMMANDS={
 'smoke':[['check_policy_core.py'],['check_label_adapter.py'],['revision_v6_boundary_development.py','--pilot'],['revision_v7_effective_intervention.py','--pilot'],['revision_v8_sensitivity_analysis.py','--pilot'],['revision_v8_sensitivity_analysis.py','--window-summary-replay']],
 'v3':[['revision_v3_decisions.py','--points-only'],['revision_v3_decisions.py','--bootstrap-only'],['revision_v3_validation.py','--stage','replay']],
 'v6':[['revision_v6_boundary_development.py']],
 'v7':[['revision_v7_effective_intervention.py']],
 'v8':[['revision_v8_sensitivity_analysis.py','--budget'],['revision_v8_sensitivity_analysis.py','--joint'],['revision_v8_sensitivity_analysis.py','--random'],['revision_v8_sensitivity_analysis.py','--windows']],
 'figures':[['nature_figures12.py'],['nature_figure3.py'],['nature_tables.py']],
 'primary-refit':[['run_search_study.py','--input','datasets/canonical_v1/study_patents.parquet','--portfolios','datasets/canonical_v1/study_portfolios.parquet','--output','results/primary_reproduction'],['summarize_tradeoffs.py','--run','results/primary_reproduction'],['context_and_uncertainty.py','--run','results/primary_reproduction']],
 'synthetic-software-test':[['check_pipeline_synthetic.py']]}
def main():
    p=argparse.ArgumentParser();p.add_argument('--layer',choices=list(COMMANDS),required=True);p.add_argument('--work-dir',type=Path,required=True);args=p.parse_args()
    work=args.work_dir.resolve()
    if work.exists():raise FileExistsError('Choose a new work directory; retained evidence must not be overwritten')
    if os.name=='nt' and work.drive.upper()=='C:':raise ValueError('Use a computational work disk such as D:, never C:')
    if work.is_relative_to(ROOT):raise ValueError('The replay working directory must be outside the public repository')
    work.mkdir(parents=True)
    for folder in ['datasets','results','scripts','research','data']:
        shutil.copytree(ROOT/folder,work/folder)
    (work/'temp').mkdir();(work/'figures/nature_v1').mkdir(parents=True)
    # Replace only a machine-specific workspace field in a working protocol copy.
    proto=work/'results/revision_v6/development_protocol.json'
    if proto.exists():
        d=json.loads(proto.read_text());d['temporary_directory']=str(work/'temp');proto.write_text(json.dumps(d,indent=2),encoding='utf-8')
    rows=[]
    for command in COMMANDS[args.layer]:
        cmd=[sys.executable,'-B','scripts/'+command[0],*command[1:]]
        start=time.perf_counter();out=subprocess.run(cmd,cwd=work,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        log=work/'research'/('public_replay_'+str(len(rows)+1)+'.log');log.write_text(out.stdout,encoding='utf-8')
        rows.append({'command':cmd[2:],'exit_code':out.returncode,'elapsed_seconds':time.perf_counter()-start,'log':str(log.relative_to(work))})
        print(out.stdout,flush=True)
        if out.returncode:break
    record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'layer':args.layer,'status':'PASS' if all(r['exit_code']==0 for r in rows) and len(rows)==len(COMMANDS[args.layer]) else 'FAIL','commands':rows,'empirical_refit':args.layer=='primary-refit','new_download':False,'synthetic_empirical_evidence':False}
    (work/'research/public_replay_run.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record));sys.exit(0 if record['status']=='PASS' else 1)
if __name__=='__main__':main()
