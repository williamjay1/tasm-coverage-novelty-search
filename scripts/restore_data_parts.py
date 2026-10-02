"""Verify and restore split archival inputs. Never overwrite an existing file."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    a=argparse.ArgumentParser();a.add_argument('--check-only',action='store_true');args=a.parse_args()
    index=json.loads((ROOT/'data_parts/index.json').read_text())
    for item in index['files']:
        for part in item['parts']:
            p=ROOT/part['path'];assert p.stat().st_size==part['bytes'] and digest(p)==part['sha256'],p
        if args.check_only:continue
        out=ROOT/item['path']
        if out.exists():
            assert out.stat().st_size==item['bytes'] and digest(out)==item['sha256'],out
            print('Existing checksum-verified input:',item['path']);continue
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('xb') as target:
            for part in item['parts']:
                with (ROOT/part['path']).open('rb') as f:
                    for block in iter(lambda:f.read(1048576),b''):target.write(block)
        assert out.stat().st_size==item['bytes'] and digest(out)==item['sha256'],out
        print('Restored:',item['path'])
    print('PASS: split inputs verified'+(' and restored' if not args.check_only else ''))
if __name__=='__main__':main()
