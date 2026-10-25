"""Launch or initialize the local annotation workspace."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from forest_bird_annotator.importer import import_runs
from forest_bird_annotator.server import create_server


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init')
    init.add_argument('--workspace',required=True,type=Path)
    init.add_argument('--runs',required=True,type=Path)
    init.add_argument('--registry',type=Path,default=Path(__file__).resolve().parents[1]/'data/registry.csv')
    serve=sub.add_parser('serve')
    serve.add_argument('--workspace',required=True,type=Path)
    serve.add_argument('--port',type=int,default=8765)
    a=p.parse_args()
    if a.command=='init':print(json.dumps(import_runs(a.workspace,a.runs,a.registry),ensure_ascii=True,indent=2))
    else:
        server=create_server(a.workspace,a.port)
        print(f'Forest Bird Annotator: http://127.0.0.1:{server.server_port}',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()


if __name__=='__main__':main()
