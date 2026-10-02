"""Acquire public archived PatentsView files, verify checksums, preserve immutable raw."""
import os
os.environ.update(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
import argparse, concurrent.futures, datetime, hashlib, json, pathlib, shutil, stat, time, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=pathlib.Path(os.environ.get('TASM_RAW_ROOT', str(ROOT/'source_raw')))
STAMP='20260929'
RECORD='15058362'
FILES=['g_patent.tsv.zip','g_cpc_at_issue.tsv.zip','g_assignee_disambiguated.tsv.zip','g_application.tsv.zip','g_patent_abstract.tsv.zip','g_us_patent_citation.tsv.zip']
RANGE_WORKERS=1

def request(url, headers=None):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Academic research data acquisition; TASM study',**(headers or {})}), timeout=90)

def immutable_bytes(path, content):
    with open(path,'xb') as f: f.write(content)
    path.chmod(stat.S_IREAD)

def range_bytes(url,start,end,total):
    with request(url,{'Range':f'bytes={start}-{end}'}) as response:
        if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{total}':
            raise RuntimeError('Unexpected public byte range response')
        data=response.read()
    if len(data)!=end-start+1:raise ValueError('Incomplete byte range')
    return data

def fetch(entry):
    name=entry['key']; expected=entry['checksum'].split(':')[1]
    dest=RAW/f'zenodo_{RECORD}_{STAMP}__{name}'
    stage=ROOT/'temp'/f'acquire_{RECORD}_{name}.part'
    if dest.exists():
        print('ALREADY_RAW',name,flush=True)
        return dict(key=name,path=str(dest),size=dest.stat().st_size,expected_md5=expected,status='existing_raw')
    url=f'https://zenodo.org/records/{RECORD}/files/{name}?download=1'; begun=time.time()
    for attempt in range(8):
        try:
            offset=stage.stat().st_size if stage.exists() else 0
            count=offset
            ranges=iter((start,min(start+32*1024*1024,entry['size'])-1) for start in range(count,entry['size'],32*1024*1024))
            with concurrent.futures.ThreadPoolExecutor(max_workers=RANGE_WORKERS) as rangepool:
                pending=[]
                for _ in range(RANGE_WORKERS):
                    chunk=next(ranges,None)
                    if chunk is not None:pending.append(rangepool.submit(range_bytes,url,*chunk,entry['size']))
                while pending:
                    data=pending.pop(0).result()
                    with stage.open('ab') as output:output.write(data)
                    count+=len(data)
                    print('PROGRESS',name,count,entry['size'],round(time.time()-begun,1),flush=True)
                    chunk=next(ranges,None)
                    if chunk is not None:pending.append(rangepool.submit(range_bytes,url,*chunk,entry['size']))
            digest=hashlib.md5()
            with stage.open('rb') as old:
                for block in iter(lambda:old.read(4*1024*1024),b''):digest.update(block)
            if stage.stat().st_size!=entry['size'] or digest.hexdigest()!=expected:
                raise ValueError(f'Checksum/size mismatch {name}: {stage.stat().st_size} {digest.hexdigest()}')
            with stage.open('rb') as source, dest.open('xb') as target: shutil.copyfileobj(source,target,4*1024*1024)
            dest.chmod(stat.S_IREAD)
            result=dict(key=name,url=url,path=str(dest),size=entry['size'],md5=digest.hexdigest(),status='verified',download_seconds=round(time.time()-begun,1))
            print('COMPLETE',json.dumps(result),flush=True)
            return result
        except Exception as e:
            print('ERROR',name,attempt,repr(e),flush=True)
            if attempt==7: raise
            time.sleep(3*(attempt+1))

def main():
    global RECORD,RANGE_WORKERS
    parser=argparse.ArgumentParser();parser.add_argument('--files',nargs='*');parser.add_argument('--workers',type=int,default=2);parser.add_argument('--range-workers',type=int,choices=[1,2],default=1);parser.add_argument('--manifest',default='patent_acquisition_manifest.json');parser.add_argument('--record',default=RECORD);args=parser.parse_args()
    RECORD=args.record
    RANGE_WORKERS=args.range_workers
    selected=args.files or FILES
    RAW.mkdir(parents=True,exist_ok=True)
    with request(f'https://zenodo.org/api/records/{RECORD}') as r: data=r.read()
    metadata=json.loads(data);entries=[x for x in metadata['files'] if x['key'] in selected]
    total=sum(x['size'] for x in entries)
    assert len(entries)==len(selected),(selected,[x['key'] for x in entries])
    assert total<=10_000_000_000,total
    assert shutil.disk_usage(RAW).free>total+1_000_000_000
    assert shutil.disk_usage(ROOT).free>total+10_000_000_000
    meta_path=RAW/f'zenodo_{RECORD}_{STAMP}__record.json'
    if not meta_path.exists():immutable_bytes(meta_path,data)
    print('PLAN',json.dumps([dict(key=x['key'],size=x['size'],url=x['links']['self']) for x in entries]),'TOTAL',total,flush=True)
    byname={x['key']:x for x in entries}
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.workers,2)) as pool:
        for result in pool.map(fetch,[byname[x] for x in selected]):
            results.append(result)
            (ROOT/'datasets'/args.manifest).write_text(json.dumps({'record':RECORD,'retrieved':datetime.datetime.now(datetime.timezone.utc).isoformat(),'record_title':metadata['metadata']['title'],'license':metadata['metadata'].get('license'),'coverage_end':'2024-12-31','files':results},indent=2),encoding='utf-8')
    print('ALL_DONE',len(results),flush=True)

if __name__=='__main__':main()
