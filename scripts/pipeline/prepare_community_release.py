"""Freeze an append-only photo snapshot without altering the collection.

Private source mapping stays outside Git. Public images are separate copies;
metadata cleaning and review rendering are later explicit steps.
"""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--legacy', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--new-only', action='store_true', help='Copy only assets absent from the prior register')
    parser.add_argument('--ignore-extension', action='append', default=[], help='Explicit non-image extensions to leave local')
    parser.add_argument('--ignore-appledouble', action='store_true', help='Leave verified macOS AppleDouble resource forks local, regardless of suffix')
    args = parser.parse_args()
    out = args.output.resolve()
    source = args.source.resolve()
    if out == source or source in out.parents:
        parser.error('Output must be outside the original collection')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'public-images').mkdir()
    with args.legacy.open(encoding='utf-8-sig', newline='') as stream:
        legacy = list(csv.DictReader(stream))
    def source_hash(row):
        return row.get('original_sha256') or row['sha256']
    known = {source_hash(row): row['image_id'] for row in legacy}
    assert len(known) == len(legacy), 'Legacy duplicate hash requires explicit alias migration'
    next_id = max(int(row['image_id'].split('_')[1]) for row in legacy) + 1
    legacy_hashes = set(known)
    rows, errors = [], []
    ignored = []
    seen = set()
    candidates = sorted(p for p in source.rglob('*') if p.is_file() and not p.is_symlink())
    for path in candidates:
        if args.ignore_appledouble and path.name.startswith('._'):
            with path.open('rb') as stream:
                appledouble = stream.read(4) == b'\x00\x05\x16\x07'
            if appledouble:
                ignored.append({'source': str(path), 'reason': 'appledouble_resource_fork'})
                continue
        if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.nef', '.arw', '.tif', '.tiff', '.dng'}:
            if path.suffix.lower() in args.ignore_extension:
                ignored.append({'source': str(path), 'reason': 'explicit_non_image_extension'})
                continue
            errors.append({'source': str(path), 'error': 'unhandled_file_type'})
            continue
        before = path.stat()
        sha = digest(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            errors.append({'source': str(path), 'error': 'changed_during_read'})
            continue
        image_id = known.get(sha)
        if args.new_only and sha in legacy_hashes:
            seen.add(sha)
            continue
        if image_id is None:
            image_id = f'fb_{next_id:04d}'
            next_id += 1
            known[sha] = image_id
        public_name = image_id + path.suffix.lower()
        target = out / 'public-images' / public_name
        duplicate = sha in seen
        if not duplicate:
            shutil.copyfile(path, target)
            assert digest(target) == sha
        seen.add(sha)
        rows.append({'image_id': image_id, 'source_path': str(path),
                     'source_relative_path': str(path.relative_to(source)),
                     'original_sha256': sha, 'original_bytes': before.st_size,
                     'public_name': public_name, 'duplicate_occurrence': duplicate})
    missing = [row['image_id'] for row in legacy if source_hash(row) not in seen]
    report = {'source_files': len(candidates), 'registered_occurrences': len(rows),
              'unique_assets': len(seen), 'legacy_count': len(legacy),
              'new_assets': len(seen - {source_hash(r) for r in legacy}),
              'original_bytes': sum(r['original_bytes'] for r in rows),
              'missing_legacy_ids': missing, 'errors': errors,
              'snapshot_assets': len({row['image_id'] for row in rows}),
              'new_only': args.new_only, 'ignored_non_images': ignored,
              'originals_modified': False, 'public_metadata_cleaned': False}
    (out / 'private-source-map.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'snapshot.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)
    if errors or missing:
        raise SystemExit('Snapshot incomplete; do not publish')


if __name__ == '__main__':
    main()
