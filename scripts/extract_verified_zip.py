"""Extract a ZIP into a new directory and verify every file before deletion."""
import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--legacy-encoding', default='gbk')
    args = parser.parse_args()
    archive_path, root = args.archive.resolve(), args.output.resolve()
    before = archive_path.stat()
    archive_sha = digest(archive_path)
    planned, seen = [], set()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            name = info.filename if info.flag_bits & 0x800 else info.filename.encode('cp437').decode(args.legacy_encoding)
            path = PurePosixPath(name.replace('\\', '/'))
            if path.is_absolute() or not path.parts or any(
                    part in ('.', '..') or ':' in part or part.rstrip(' .') != part
                    or re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)', part)
                    for part in path.parts):
                raise ValueError('Unsafe archive path')
            target = (root / Path(*path.parts)).resolve()
            if not target.is_relative_to(root) or target == root:
                raise ValueError('Archive path escapes output')
            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                raise ValueError('Links and encrypted members are unsupported')
            key = str(target).casefold()
            if key in seen:
                raise ValueError('Duplicate archive path')
            seen.add(key)
            planned.append((info, target))
        root.mkdir(parents=True, exist_ok=False)
        records = []
        for info, target in planned:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            value = hashlib.sha256()
            size = 0
            with archive.open(info) as source, target.open('xb') as output:
                for block in iter(lambda: source.read(4 * 1024 * 1024), b''):
                    output.write(block)
                    value.update(block)
                    size += len(block)
            if size != info.file_size or digest(target) != value.hexdigest():
                raise ValueError('Extracted file mismatch')
            records.append({'relative_path': target.relative_to(root).as_posix(),
                            'bytes': size, 'sha256': value.hexdigest(), 'crc32': f'{info.CRC:08x}'})
    after = archive_path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or digest(archive_path) != archive_sha:
        raise ValueError('Archive changed during extraction')
    report = {'passed': True, 'archive_path': str(archive_path), 'archive_sha256': archive_sha,
              'archive_bytes': before.st_size, 'output_path': str(root),
              'files': len(records), 'file_records': records, 'archive_deleted': False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'file_records'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
