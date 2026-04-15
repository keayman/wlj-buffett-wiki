#!/usr/bin/env python3
"""
fix_headings.py — 第一轮修复：检测独立短行自动加 ## 标记。

规则：
  - 行长度 <= 25 字（中文）
  - 前一行为空行
  - 行本身不以 #、-、*、>、| 开头
  - 不在代码块内
  - 不是 YAML frontmatter 内
"""

import re
import sys
from pathlib import Path
import argparse

BASE_DIR = Path(__file__).parent.parent
WIKI_DIR = BASE_DIR / "wiki"

# 不应该被加 ## 的行特征
NON_HEADING_PATTERNS = [
    r'^\[',           # 链接
    r'^\!',           # 图片
    r'^\d+\.',        # 有序列表
    r'^\d{4}',        # 年份开头（正文）
    r'.*[，。！？：；]$',  # 以标点结尾
    r'.{30,}',        # 超过30字的长行
    r'——',           # 引号来源行
    r'^—',            # 破折号
    r'^\(',           # 括号
]


def is_non_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    for pat in NON_HEADING_PATTERNS:
        if re.search(pat, stripped):
            return True
    return False


def fix_headings(text: str) -> str:
    lines = text.split("\n")
    result = []
    in_frontmatter = False
    frontmatter_done = False
    in_code = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # YAML frontmatter 检测
        if i == 0 and stripped == "---":
            in_frontmatter = True
            result.append(line)
            i += 1
            continue
        
        if in_frontmatter:
            result.append(line)
            if stripped == "---" and i > 0:
                in_frontmatter = False
                frontmatter_done = True
            i += 1
            continue
        
        # 代码块
        if stripped.startswith("```"):
            in_code = not in_code
            result.append(line)
            i += 1
            continue
        
        if in_code:
            result.append(line)
            i += 1
            continue
        
        # 判断是否应该加 ##
        # 条件：前一行为空，当前行短且不像正文，下一行不为空
        should_add = (
            frontmatter_done
            and stripped
            and len(stripped) <= 25
            and not stripped.startswith("#")
            and not stripped.startswith("-")
            and not stripped.startswith("*")
            and not stripped.startswith(">")
            and not stripped.startswith("|")
            and not is_non_heading(stripped)
            and i > 0
            and not lines[i - 1].strip()  # 前一行为空
            and (i + 1 < len(lines) and lines[i + 1].strip())  # 下一行非空
        )
        
        if should_add:
            result.append(f"## {stripped}")
        else:
            result.append(line)
        
        i += 1
    
    return "\n".join(result)


def process_file(path: Path, dry_run: bool = False):
    text = path.read_text(encoding="utf-8")
    fixed = fix_headings(text)
    
    if fixed == text:
        return False
    
    if dry_run:
        # 显示变更
        orig_lines = text.split("\n")
        new_lines = fixed.split("\n")
        changes = [(i+1, o, n) for i, (o, n) in enumerate(zip(orig_lines, new_lines)) if o != n]
        if changes:
            print(f"  {path.name}: {len(changes)} 处修改")
            for lineno, old, new in changes[:3]:
                print(f"    行{lineno}: {old!r} → {new!r}")
    else:
        path.write_text(fixed, encoding="utf-8")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="修复 wiki 中缺失的 ## 标题标记（第一轮）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dir", help="指定子目录", default=None)
    args = parser.parse_args()
    
    if args.dir:
        target_dir = WIKI_DIR / args.dir
    else:
        target_dir = WIKI_DIR
    
    files = list(target_dir.rglob("*.md"))
    changed = 0
    
    for f in sorted(files):
        if f.name in ("SCHEMA.md", "README.md", "index.md", "log.md"):
            continue
        if process_file(f, args.dry_run):
            changed += 1
            if not args.dry_run:
                print(f"✓ {f.relative_to(BASE_DIR)}")
    
    print(f"\n{'[预览]' if args.dry_run else '完成'} 修改了 {changed}/{len(files)} 个文件")


if __name__ == "__main__":
    main()
