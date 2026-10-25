"""Start the local annotation service in the background and open its browser UI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--no-open',action='store_true')
    a=p.parse_args();root=a.workspace.resolve()
    if not (root/'annotations.sqlite3').is_file():
        raise SystemExit('Initialize this workspace with scripts/annotator/annotator.py init first.')
    expected=hashlib.sha256(str(root).casefold().encode('utf-8')).hexdigest()[:16]
    url=f'http://127.0.0.1:{a.port}'
    def health():
        try:
            with urlopen(url+'/api/health',timeout=1) as r:return json.load(r)
        except Exception:return None
    current=health();process=None
    if current:
        if current.get('workspace_id')!=expected:raise SystemExit('Port belongs to a different workspace; select another port.')
    else:
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with (root/'server.stdout.log').open('ab') as stdout,(root/'server.stderr.log').open('ab') as stderr:
            process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('annotator.py')),'serve',
                 '--workspace',str(root),'--port',str(a.port)],stdout=stdout,stderr=stderr,
                 stdin=subprocess.DEVNULL,creationflags=flags,start_new_session=os.name!='nt',cwd=Path(__file__).resolve().parents[1])
        for _ in range(60):
            current=health()
            if current and current.get('workspace_id')==expected:break
            if process.poll() is not None:raise SystemExit('Service exited; inspect server.stderr.log in the workspace.')
            time.sleep(.15)
        else:raise SystemExit('Service did not become ready; inspect server.stderr.log.')
        (root/'server-process.json').write_text(json.dumps({'pid':process.pid,'port':a.port,'workspace_id':expected,'url':url},indent=2),encoding='utf-8')
    if not a.no_open:webbrowser.open(url)
    print(json.dumps({'url':url,'images':current['images'],'running':True,'started':process is not None}))


if __name__=='__main__':main()
