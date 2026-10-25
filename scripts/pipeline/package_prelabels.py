"""Build a portable review bundle without raw model tensors or private paths."""
import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageOps
from build_review_page import build_html
from prepare_community_release import digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--snapshot', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--archive-name', default='z8-prelabels-review-20261024.zip')
    p.add_argument('--review-id', help='Separate browser storage namespace for this batch')
    a = p.parse_args()
    summary = json.loads((a.run / 'summary.json').read_text())
    if not summary['complete'] or summary['failed']:
        raise RuntimeError('Cannot package an incomplete run')
    a.output.mkdir(parents=True, exist_ok=False)
    for directory in ['overlays', 'previews', 'raw-review']:
        (a.output / directory).mkdir()
    manifest = {r['image_id']: r for r in json.loads((a.snapshot / 'manifest.json').read_text())}
    rows = [json.loads(line) for line in (a.run / 'predictions.jsonl').read_text().splitlines()]
    links = []
    for row in rows:
        image_id = row['image_id']
        meta = manifest[image_id]
        source = a.snapshot / meta['review_file']
        shutil.copyfile(a.run / 'overlays' / (image_id + '.jpg'), a.output / 'overlays' / (image_id + '.jpg'))
        with Image.open(source) as image:
            preview = ImageOps.exif_transpose(image).convert('RGB')
            preview.thumbnail((1800, 1400), Image.Resampling.LANCZOS)
            preview.save(a.output / 'previews' / (image_id + '.jpg'), quality=90)
        if meta['format'] == 'nef':
            full_path = 'raw-review/' + source.name
            shutil.copyfile(source, a.output / full_path)
        else:
            full_path = 'images/' + meta['file']
        row['review_relative_path'] = 'previews/' + image_id + '.jpg'
        row['full_review_relative_path'] = full_path
        links.append({'image_id': image_id, 'full_review_file': full_path,
                      'review_sha256': meta['review_sha256']})
    (a.output / 'predictions.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    (a.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    with (a.output / 'full-resolution-links.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(links[0]))
        writer.writeheader()
        writer.writerows(links)
    page = a.output / 'review.html'
    page.write_text(build_html(rows, a.review_id), encoding='utf-8')
    (a.output / 'README.md').write_text('''# Z8 review bundle

**English** | [简体中文](README.zh-CN.md)

Extract this batch's community image archive(s) here to merge images/. Open review.html, which defaults to English and includes Simplified Chinese. Review the whole image, add decisions and notes, then export the JSON file.

Full-resolution NEF review JPEGs are in raw-review/. The image paths and review hashes are listed in full-resolution-links.csv. Use full-resolution images for detailed annotation.

Native slots 0-5 still need semantic labels. Proposals await human review. Photographs retain contributor copyrights.
''', encoding='utf-8')
    (a.output / 'README.zh-CN.md').write_text('''# Z8 预标注复核包

[English](README.md) | **简体中文**

1. 解压后打开 review.html，查看带框预览、切换原图预览、筛选无候选图，并导出人工复核决定。
2. 为检查微小眼部，请把本批 community-images 图片包解压到本目录，合并 images/。完整图路径见 full-resolution-links.csv；若本批含 NEF，其固定全尺寸审核 JPEG 包含于 raw-review/。
3. 预览不能代替完整图精标。slot 0–5 的眼/头/鸟语义尚未确认；所有结果都是待审核建议，不是人工真值。没有候选不等于没有鸟。
4. 人工决定保存在当前浏览器 localStorage，结束时必须导出 JSON。原模型输出不随人工决定覆盖。
5. 本包不含权重、固件、SDK、神经网络输出张量、私人原路径或联系方式。图片版权仍归摄影者，不默认授予统一 CC 许可。
''', encoding='utf-8')
    target = a.output.parent / a.archive_name
    if target.exists():
        raise RuntimeError('Do not overwrite an earlier bundle')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for path in sorted(a.output.rglob('*')):
            if path.is_file():
                archive.write(path, str(path.relative_to(a.output)).replace('\\', '/'))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    assert target.stat().st_size < 2 * 1024 ** 3
    result = {'file': target.name, 'images': len(rows), 'bytes': target.stat().st_size,
              'sha256': digest(target), 'human_review_complete': False}
    (a.output.parent / 'review-bundle.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
