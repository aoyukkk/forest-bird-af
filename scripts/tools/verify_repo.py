#!/usr/bin/env python3
"""检查仓库中是否误入不该公开的资产。

用法:
    python scripts/tools/verify_repo.py [repo_root]

退出码 0 表示通过，1 表示发现违规文件。
"""
import os
import sys

# 禁止入库的扩展名
FORBIDDEN_EXT = {
    '.nab', '.vvpm', '.nbg', '.nb',
    '.fdat', '.tar', '.img',
    '.bin', '.dat',
    '.jpg', '.jpeg', '.png', '.tif', '.tiff',
    '.nef', '.arw', '.cr2', '.cr3', '.raf', '.orf',
    '.pt', '.pth', '.onnx', '.weights', '.engine', '.safetensors',
    '.zip', '.7z', '.rar', '.gz',
}

# 允许的例外（文档插图、标签归档），按相对路径前缀匹配。
# 这里的 zip 只含逐图 YOLO 文本，不含图片或权重。
ALLOWED_PREFIX = (
    'docs/figures/',
    'data/annotations-2026-10-25/confirmed/yolo-labels.zip',
)

# 禁止出现的目录名
FORBIDDEN_DIR = {
    'models_all', 'fwtool', 'z8-qemu', 'NikonFirmwarePatch',
    'toolchains', 'extract', 'work',
}

# 体积上限（单文件 MB）
MAX_MB = 20

# 厂商固件文件名特征
FORBIDDEN_NAME_PARTS = (
    'BODYDATA', 'Z_8_', 'Z_9_', 'nflasha', 'firmware.fdat',
)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    violations = []
    total = 0
    total_bytes = 0

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace('\\', '/')

        if rel_dir == '.':
            rel_dir = ''

        if '.git' in dirnames:
            dirnames.remove('.git')

        for d in list(dirnames):
            if d in FORBIDDEN_DIR:
                violations.append((f'{rel_dir}/{d}/', '禁止的目录'))

        for fn in filenames:
            rel = f'{rel_dir}/{fn}' if rel_dir else fn
            full = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()

            try:
                size = os.path.getsize(full)
            except OSError:
                continue

            total += 1
            total_bytes += size

            if any(rel.startswith(p) for p in ALLOWED_PREFIX):
                continue

            if ext in FORBIDDEN_EXT:
                violations.append((rel, f'禁止的扩展名 {ext}'))
                continue

            for part in FORBIDDEN_NAME_PARTS:
                if part in fn:
                    violations.append((rel, f'文件名含厂商资产特征 {part}'))
                    break

            if size > MAX_MB * 1024 * 1024:
                violations.append((rel, f'超过 {MAX_MB} MB（{size/1048576:.1f} MB）'))

    print(f'扫描 {total} 个文件，共 {total_bytes/1048576:.1f} MB')

    if violations:
        print(f'\n发现 {len(violations)} 处违规：\n')
        for path, reason in violations:
            print(f'  {path}  --  {reason}')
        return 1

    print('通过：未发现禁止入库的资产')
    return 0


if __name__ == '__main__':
    sys.exit(main())
