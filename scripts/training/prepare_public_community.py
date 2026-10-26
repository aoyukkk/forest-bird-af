"""Adapt published reviewed labels and frozen input PNGs for YOLO training.

No vendor package, production SQLite or private source paths are required.
Historical test entries carry metadata only; their labels/pixels are not loaded.
"""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path


def build(labels, split, registry, inputs):
    registered = {row['image_id']: row for row in registry}
    images = []
    for entry in split['images']:
        ident = entry['image_id']
        published = labels[ident]
        annotation = published['annotation_image']
        if annotation['png_sha256'] != entry['png_sha256']:
            raise ValueError('Published label/input split mismatch: ' + ident)
        metadata = dict(image_id=ident, width=384, height=256,
                        png_sha256=entry['png_sha256'], input_sha256=entry['input_sha256'],
                        original_sha256=registered[ident]['original_sha256'],
                        preprocess_id=entry['preprocess_id'])
        doc = None
        if entry['split'] != 'test':
            if published['review_status'] != 'confirmed' or not published['confirmed']:
                raise ValueError('Confirmed human review required: ' + ident)
            raw = (inputs / (ident + '.png')).read_bytes()
            if hashlib.sha256(raw).hexdigest() != metadata['png_sha256']:
                raise ValueError('Frozen input bytes differ: ' + ident)
            doc = dict(status='confirmed', confirmed_by={'kind': 'human', 'id': 'published-review'},
                       presence=published['presence'], items=copy.deepcopy(published['items']),
                       provenance={'source': 'published Z8-assisted human review; no new confirmation'})
        images.append(dict(image_id=ident, metadata=metadata, document=doc,
                           split=entry['split'], leakage_group_id=entry['leakage_group_id']))
    return dict(schema='public-community-parts-input-v1', counts=split['counts'], images=images,
                historical_test='metadata only; no target or pixel import',
                source='published reviewed labels and frozen split; not independently blind truth')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--split', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error('Private derived workspace belongs outside public repository')
    if args.output.exists():
        parser.error('Output already exists; preserve earlier manifests')
    labels = {row['image_id']: row for line in args.labels.read_text(encoding='utf-8').splitlines() if (row := json.loads(line))}
    split = json.loads(args.split.read_text(encoding='utf-8'))
    with args.registry.open(encoding='utf-8-sig', newline='') as stream:
        registry = list(csv.DictReader(stream))
    result = build(labels, split, registry, args.inputs)
    result['source_hashes'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in
                              [('labels', args.labels), ('split', args.split), ('registry', args.registry)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'images': len(result['images']), 'counts': result['counts'], 'vendor_package_needed': False}))


if __name__ == '__main__':
    main()
