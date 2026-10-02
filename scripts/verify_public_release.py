"""Verify every tracked release item and original scientific input hashes."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    m=json.loads((ROOT/'public_manifest.json').read_text())
    for item in m['files']:
        p=ROOT/item['path'];assert p.is_file() and p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],item['path']
    parts=json.loads((ROOT/'data_parts/index.json').read_text())
    for item in parts['files']:
        p=ROOT/item['path']
        if p.exists():assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],item['path']
    print('PASS:',len(m['files']),'manifest files; any restored input matches the original byte checksum')
if __name__=='__main__':main()
