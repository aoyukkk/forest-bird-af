"""Extract a RAR with bsdtar, then compare a second archive read per file.

The original archive is retained. Delete it separately only after inspecting
the successful private report. Requires a tar implementation with RAR support.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--report',required=True,type=Path)
    p.add_argument('--tar',default='tar')
    p.add_argument('--verify-existing',action='store_true',help='Verify an already extracted directory without rewriting it')
    a=p.parse_args()
    archive=a.archive.resolve();root=a.output.resolve()
    before=archive.stat();archive_sha=digest(archive)
    names=subprocess.run([a.tar,'-tf',str(archive)],capture_output=True,check=True).stdout.decode('utf-8').splitlines()
    details=subprocess.run([a.tar,'-tvf',str(archive)],capture_output=True,check=True).stdout.decode('utf-8',errors='replace').splitlines()
    if len(names)!=len(details) or not names:
        raise ValueError('Unrecognized or empty archive listing')
    planned=[];seen=set()
    for name,line in zip(names,details):
        path=PurePosixPath(name.replace('\\','/'))
        if path.is_absolute() or not path.parts or any(part in ('.','..') or ':' in part or part.rstrip(' .')!=part or re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)',part) for part in path.parts):
            raise ValueError('Unsafe archive path')
        target=(root/Path(*path.parts)).resolve()
        if not target.is_relative_to(root) or target==root:
            raise ValueError('Archive path escapes output')
        kind=line[0];fields=line.split()
        if kind not in ('-','d') or len(fields)<6:
            raise ValueError('Links and special entries are unsupported')
        key=str(target).casefold()
        if key in seen:
            raise ValueError('Duplicate archive path')
        seen.add(key)
        if kind=='-':planned.append((name,target,int(fields[4])))
    if a.verify_existing:
        if not root.is_dir() or root.is_symlink():
            raise ValueError('Expected the existing extraction directory')
    else:
        root.mkdir(parents=True,exist_ok=False)
        subprocess.run([a.tar,'-xf',str(archive),'-C',str(root)],check=True)
    extracted={p.resolve() for p in root.rglob('*') if p.is_file()}
    if extracted!={target for _,target,_ in planned} or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Extracted paths do not match the safe archive list')
    # One sequential pass avoids quadratic decompression for solid archives.
    records=[]
    # RAR directory records can produce a bsdtar error with -O. Select regular
    # members explicitly, keeping their original archive order in one pass.
    with subprocess.Popen([a.tar,'-xOf',str(archive),'--']+[name for name,_,_ in planned],stdout=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
        for index,(name,target,size) in enumerate(planned,1):
            remaining=size;h=hashlib.sha256()
            while remaining:
                block=proc.stdout.read(min(4*1024*1024,remaining))
                if not block:raise ValueError('Archive stream ended early')
                h.update(block);remaining-=len(block)
            if target.stat().st_size!=size or digest(target)!=h.hexdigest():
                raise ValueError('Extracted file content mismatch: '+name)
            records.append({'relative_path':target.relative_to(root).as_posix(),'bytes':size,'sha256':h.hexdigest()})
            if index%10==0:print(json.dumps({'verified':index,'total':len(planned)}),flush=True)
        extra=proc.stdout.read(1);error=proc.stderr.read();code=proc.wait()
        if extra or code:
            raise ValueError('Archive validation failed: '+error.decode(errors='replace'))
    after=archive.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or digest(archive)!=archive_sha:
        raise ValueError('Archive changed during extraction')
    report={'passed':True,'archive_path':str(archive),'archive_sha256':archive_sha,'archive_bytes':before.st_size,'output_path':str(root),'files':len(records),'file_records':records,'validation':'Two bsdtar decompressions; per-file size and SHA-256 match; archive hash unchanged','archive_deleted':False}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='file_records'},ensure_ascii=True),flush=True)


if __name__=='__main__':
    main()
