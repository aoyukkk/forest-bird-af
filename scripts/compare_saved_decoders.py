"""Compare E7 host decoding to saved original-Z8 proposals without inference."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', required=True, type=Path)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    summary = json.loads((args.run / 'summary.json').read_text())
    if not summary['complete'] or summary['failed']:
        raise ValueError('Run must be complete')
    sys.path.insert(0, str(args.upstream.resolve()))
    from consumer import Consumer, pack_heads
    decoder = Consumer()
    rows = [json.loads(line) for line in (args.run / 'predictions.jsonl').read_text().splitlines()]
    differences = []
    for row in rows:
        with np.load(args.run / 'heads' / (row['image_id'] + '.npz')) as heads:
            raw = pack_heads(heads['fine'].view('<f2'), heads['coarse'].view('<f2'))
        host = decoder.consume(raw)
        expected = []
        for candidate in row['candidates']:
            x1, y1, x2, y2 = candidate['box_input_xyxy']
            expected.append([(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1,
                             candidate['native_integer_score'], candidate['class_slot']])
        if host['status'] != 0 or host['records'] != expected:
            differences.append(row['image_id'])
    report = {'passed': not differences, 'images_compared': len(rows),
              'equal_records': len(rows) - len(differences), 'different_records': differences,
              'postprocessor_used_for_prelabels': 'original local Z8 BA2',
              'scope': 'Finite corpus comparison of E7 host decoding and saved original-Z8 proposals on the same head buffers.'}
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    if differences:
        raise ValueError('Decoder differences require review')


if __name__ == '__main__':
    main()
