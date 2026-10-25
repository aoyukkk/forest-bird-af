"""Loopback HTTP application; UI and AI share the same revisioned API."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
from .store import Store, Problem, dumps, initial, validate
from .schema import describe
from . import z8_review, dedupe

STATIC = Path(__file__).parent/'web'


def create_server(workspace, port=8765):
    store = Store(workspace)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'ForestBirdAnnotator/1.0'

        def log_message(self, fmt, *args):
            if args and '/api/images/' not in str(args[0]) and '/api/dataset' not in str(args[0]):
                super().log_message(fmt,*args)

        def send(self, value, status=200, mime='application/json; charset=utf-8', filename=None):
            data = value if isinstance(value,bytes) else (dumps(value).encode('utf-8') if mime.startswith('application/json') else value.encode('utf-8'))
            self.send_response(status)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            if filename:
                self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                raise Problem('Content-Type must be application/json',415)
            size=int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 20*1024*1024:
                raise Problem('JSON body must be 1 byte to 20 MB',413)
            return json.loads(self.rfile.read(size))

        def check_origin(self):
            port=self.server.server_port
            allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
            if self.headers.get('Host') not in allowed:
                raise Problem('Only localhost access is allowed',403)
            origin=self.headers.get('Origin')
            if origin and origin not in {f'http://{x}' for x in allowed}:
                raise Problem('Cross-origin access is not allowed',403)

        def do_GET(self): self.dispatch('GET')
        def do_POST(self): self.dispatch('POST')
        def do_PUT(self): self.dispatch('PUT')

        def dispatch(self, method):
            try:
                self.check_origin()
                parsed=urlparse(self.path);path=parsed.path;query=parse_qs(parsed.query)
                if method=='GET' and path in ('/','/index.html','/annotate','/app.js','/style.css','/z8-review.html','/z8-review.js','/z8-review.css'):
                    file=STATIC/({'/':'z8-review.html','/index.html':'z8-review.html','/annotate':'index.html'}.get(path,path.lstrip('/')))
                    mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[file.suffix]
                    return self.send(file.read_bytes(),mime=mime)
                if method=='GET' and path=='/api/health':
                    return self.send({'ok':True,'schema_version':'forest-bird-input-manual-v1','images':len(store.dataset()),
                                      'workspace_id':hashlib.sha256(str(store.root).casefold().encode('utf-8')).hexdigest()[:16],
                                      'features':['z8-correction-v1','queue-dedupe-v1']})
                if path=='/api/z8-review/dedupe':
                    if method=='GET':return self.send(dedupe.view(store))
                    if method=='POST':
                        body=self.body()
                        if body.get('action')=='scan':dedupe.scan(store)
                        else:dedupe.decide(store,body)
                        return self.send(dedupe.view(store))
                if method=='GET' and path=='/api/z8-review/dataset':
                    return self.send({'images':z8_review.dataset(store)})
                if method=='GET' and path=='/api/z8-review/schema':
                    return self.send(z8_review.describe())
                if method=='GET' and path=='/api/z8-review/export':
                    scope=query.get('scope',['confirmed'])[0]
                    records=z8_review.export(store,'confirmed' if scope=='usable' else scope)
                    if scope=='usable':
                        hidden=dedupe.read(store)['hidden'];records=[r for r in records if r['image_id'] not in hidden]
                    text=''.join(dumps(r)+'\n' for r in records)
                    return self.send(text,mime='application/x-ndjson; charset=utf-8',filename=f'z8-human-corrections-{scope}.jsonl')
                review_match=re.fullmatch(r'/api/z8-review/(fb_\d{4,})(?:/(history))?',path)
                if review_match:
                    ident,kind=review_match.groups()
                    if method=='GET':return self.send({'history':z8_review.history(store,ident)} if kind else z8_review.get(store,ident))
                    if method=='PUT' and kind is None:return self.send(z8_review.save(store,ident,self.body()))
                if method=='GET' and path=='/api/dataset':
                    return self.send({'images':store.dataset()})
                if method=='GET' and path=='/api/schema':
                    return self.send(describe())
                if method=='GET' and path=='/api/help':
                    return self.send({'schema_version':'forest-bird-input-manual-v1','coordinate_space':'z8_input_384x256',
                        'default_workflow':{'name':'z8-assisted-human-correction','schema':'GET /api/z8-review/schema',
                            'read':['GET /api/z8-review/dataset','GET /api/z8-review/{id}','GET /api/z8-review/{id}/history'],
                            'write':'PUT /api/z8-review/{id}: {base_revision,review,actor:{id,kind},action:draft|confirm|uncertain}',
                            'export':'GET /api/z8-review/export?scope=all|confirmed|uncertain',
                            'instructions':['Start from frozen Z8 proposals, not old LLM annotations.',
                                'Only explicit human confirmation assesses correctness. Navigation is not confirmation.',
                                'AI may save drafts only; use actor.kind=ai. Corrections and manual labels are separate schemas.']},
                        'read':['GET /api/schema','GET /api/dataset','GET /api/images/{id}','GET /api/images/{id}/png','GET /api/annotations/{id}','GET /api/history/{id}'],
                        'write':['PUT /api/annotations/{id}: {base_revision,annotation,actor:{id,kind}}',
                                 'POST /api/import: {records:[{image_id,base_revision,annotation}],actor}',
                                 'POST /api/claim: {actor,seconds:600,zero_only:false}',
                                 'POST /api/release-claim: {image_id,actor}'],
                        'exports':['GET /api/export?scope=all|complete|reviewed'],
                        'instructions':['Read annotation revision before writing; conflicts return 409.',
                         'AI must identify actor.kind=ai. AI submissions cannot mark reviewed.',
                         'Coordinates describe evidence in the 384x256 input. Original-reference visibility is a different assessment.',
                         'Annotate every visible bird, head and eye. Do not invent occluded geometry.',
                         'Raw Z8 candidates are suggestions; do not copy all slots into human ground truth.']})
                match=re.fullmatch(r'/api/images/(fb_\d{4,})(?:/(png|reference))?',path)
                if method=='GET' and match:
                    ident,kind=match.groups()
                    if kind is None:return self.send(store.image(ident))
                    meta=store.metadata(ident)
                    if kind=='png':
                        target=store.root/'images'/(ident+'.png');expected=meta['png_sha256']
                    else:
                        if not meta.get('reference_path'):raise Problem('No original reference',404)
                        target=Path(meta['reference_path']);expected=meta['reference_sha256']
                    raw=target.read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=expected:raise Problem('Image integrity check failed',409)
                    mime='image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg'
                    return self.send(raw,mime=mime)
                match=re.fullmatch(r'/api/(annotations|history)/(fb_\d{4,})',path)
                if match:
                    kind,ident=match.groups()
                    if method=='GET':return self.send(store.get(ident) if kind=='annotations' else {'history':store.history(ident)})
                    if method=='PUT' and kind=='annotations':
                        b=self.body()
                        return self.send(store.save_many([{'image_id':ident,'base_revision':b.get('base_revision'),'annotation':b.get('annotation')}],b.get('actor'))[0])
                if method=='POST' and path=='/api/validate':
                    b=self.body();_,issues=validate(b['annotation'],store.metadata(b['image_id']))
                    return self.send({'valid':True,'issues':issues})
                if method=='POST' and path=='/api/import':
                    b=self.body()
                    return self.send({'records':store.save_many(b.get('records'),b.get('actor'))})
                if method=='POST' and path=='/api/claim':
                    b=self.body()
                    return self.send({'claim':store.claim(b.get('actor'),b.get('seconds',600),b.get('zero_only',False))})
                if method=='POST' and path=='/api/release-claim':
                    b=self.body();store.release_claim(b['image_id'],b.get('actor'));return self.send({'ok':True})
                if method=='GET' and path=='/api/export':
                    scope=query.get('scope',['all'])[0]
                    text=''.join(dumps(r)+'\n' for r in store.export(scope))
                    return self.send(text,mime='application/x-ndjson; charset=utf-8',filename=f'forest-bird-input-labels-{scope}.jsonl')
                if method=='POST' and path=='/api/backup':
                    self.body();target=store.backup();return self.send({'ok':True,'file':target.name})
                raise Problem('Not found',404)
            except Problem as e:
                self.send({'error':str(e),'details':e.details},e.status)
            except (ValueError,TypeError,KeyError) as e:
                self.send({'error':str(e)},400)
            except (BrokenPipeError,ConnectionResetError):
                pass
            except Exception as e:
                self.log_error('%s',e)
                self.send({'error':'Local operation failed; check server log'},500)

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.store=store
    return server


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('--port',type=int,default=8765)
    a=p.parse_args()
    server=create_server(a.workspace,a.port)
    print(f'Forest Bird Annotator: http://127.0.0.1:{server.server_port}',flush=True)
    print(f'Workspace: {a.workspace.resolve()}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
