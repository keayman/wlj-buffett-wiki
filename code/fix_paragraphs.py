#!/usr/bin/env python3
"""
fix_paragraphs.py — 修复超长行（>150字符）：在中文句号后分段，加空行。
"""

import re
from pathlib import Path
import argparse

BASE_DIR = Path(__file__).parent.parent
WIKI_DIR = BASE_DIR / "wiki"

MAX_LINE_LEN = 150
# 中文句末标点
SENTENCE_END = re.compile(r'([。！？])')


def split_long_line(line: str) -> list:
    """将超长行在中文句号处分段"""
    if len(line) <= MAX_LINE_LEN:
        return [line]
    
    # 在句末标点后分割
    parts = SENTENCE_END.sub(r'\1\n', line).split('\n')
    parts = [p.strip() for p in parts if p.strip()]
    
    # 如果还是太长，直接返回原行（不强行分割）
    if not parts:
        return [line]
    
    return parts


def fix_paragraphs(text: str) -> str:
    lines = text.split("\n")
    result = []
    in_frontmatter = False
    frontmatter_done = False
    in_code = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # YAML frontmatter
        if i == 0 and stripped == "---":
            in_frontmatter = True
            result.append(line)
            continue
        
        if in_frontmatter:
            result.append(line)
            if stripped == "---" and i > 0:
                in_frontmatter = False
                frontmatter_done = True
            continue
        
        # 代码块
        if stripped.startswith("```"):
            in_code = not in_code
            result.append(line)
            continue
        
        if in_code:
            result.append(line)
            continue
        
        # 跳过标题行
        if line.startswith("#"):
            result.append(line)
            continue
        
        # 处理超长行
        if frontmatter_done and len(stripped) > MAX_LINE_LEN:
            parts = split_long_line(stripped)
            if len(parts) > 1:
                # 在段落之间加空行
                for j, part in enumerate(parts):
                    result.append(part)
                    if j < len(parts) - 1:
                        result.append("")
            else:
                result.append(line)
        else:
            result.append(line)
    
    return "\n".join(result)


def process_file(path: Path, dry_run: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    fixed = fix_paragraphs(text)
    
    if fixed == text:
        return False
    
    if not dry_run:
        path.write_text(fixed, encoding="utf-8")
        print(f"✓ {path.name}")
    else:
        print(f"  [预览] {path.name}: 有修改")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="修复超长行，在中文句号后分段")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dir", default=None)
    args = parser.parse_args()
    
    target_dir = (WIKI_DIR / args.dir) if args.dir else WIKI_DIR
    files = list(target_dir.rglob("*.md"))
    changed = 0
    
    for f in sorted(files):
        if f.name in ("SCHEMA.md", "README.md", "index.md", "log.md"):
            continue
        if process_file(f, args.dry_run):
            changed += 1
    
    print(f"\n{'[预览]' if args.dry_run else '完成'} 修改了 {changed}/{len(files)} 个文件")


if __name__ == "__main__":
    main()
