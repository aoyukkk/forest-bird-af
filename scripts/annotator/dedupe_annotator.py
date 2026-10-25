"""Scan all annotation inputs and publish a reversible deduplicated queue."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from forest_bird_annotator.store import Store
from forest_bird_annotator.dedupe import scan

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True,type=Path)
    args=parser.parse_args()
    result=scan(Store(args.workspace))
    print(json.dumps({'run_id':result['run_id'],**result['summary']},ensure_ascii=False,indent=2))
