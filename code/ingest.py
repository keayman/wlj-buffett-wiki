#!/usr/bin/env python3
"""
ingest.py — 使用 Anthropic API 批量生成信件和访谈的结构化摘要，写入 wiki/。

用法：
  python ingest.py --all                          # 摄取所有未处理的信件和访谈
  python ingest.py --dry-run                      # 预览模式
  python ingest.py --dir letters/berkshire        # 只处理指定目录
  python ingest.py --file "1988 巴菲特致股东信.md"  # 处理单个文件

环境变量（在 code/web/.env 中配置）：
  ANTHROPIC_API_KEY=your-key
  ANTHROPIC_BASE_URL=https://api.aicodewith.com  # 可选
  ANTHROPIC_MODEL=claude-sonnet-4-6               # 可选
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import date

try:
    import anthropic
except ImportError:
    print("错误：请先安装 anthropic 库: pip install anthropic")
    sys.exit(1)

# ── 路径配置 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "raw"
WIKI_DIR = BASE_DIR / "wiki"
LOG_PATH = WIKI_DIR / "log.md"
ENV_FILE = BASE_DIR / "code" / "web" / ".env"

# ── 摄取目标 ──────────────────────────────────────────────────────────────────
INGEST_TARGETS = [
    {
        "raw_sub": "letters/berkshire",
        "wiki_sub": "letters",
        "type": "letter-summary",
        "tags": ["股东信", "伯克希尔"],
    },
    {
        "raw_sub": "letters/partnership",
        "wiki_sub": "letters",
        "type": "letter-summary",
        "tags": ["合伙人信"],
    },
    {
        "raw_sub": "letters/special",
        "wiki_sub": "letters",
        "type": "letter-summary",
        "tags": ["特别信件"],
    },
    {
        "raw_sub": "interviews",
        "wiki_sub": "interviews",
        "type": "interview-summary",
        "tags": ["访谈", "演讲"],
    },
]

# ── 加载实体列表（用于提示词） ────────────────────────────────────────────────
def load_entity_names():
    names = {"concepts": [], "companies": [], "people": []}
    for cat in names:
        d = RAW_DIR / cat
        if d.exists():
            names[cat] = [f.stem for f in d.glob("*.md")]
    return names


# ── 构建摘要提示词 ────────────────────────────────────────────────────────────
def build_prompt(raw_text: str, doc_type: str, title: str, entities: dict) -> str:
    concepts = "、".join(entities["concepts"][:30])
    companies = "、".join(entities["companies"][:30])
    people = "、".join(entities["people"])
    
    type_instruction = ""
    if doc_type == "letter-summary":
        type_instruction = "这是巴菲特写给股东或合伙人的信件。"
    else:
        type_instruction = "这是巴菲特的演讲或访谈记录。"
    
    return f"""你是巴菲特投资思想知识库的编辑。{type_instruction}

请为以下文档生成一个结构化的 Markdown 摘要页面。

## 要求

1. **长度**：约为原文的 20-30%，精炼核心思想
2. **结构**：严格按照以下 Markdown 格式
3. **双向链接**：在正文中，凡是出现以下实体名称，必须替换为 [[实体名]] 格式（不要在标题行使用）
4. **语言**：中文，保持巴菲特原有风格的直接和坦率

## 已知实体（需要转换为双向链接）

概念：{concepts}
公司：{companies}  
人物：{people}

## 输出格式（严格遵守）

```
# {title}

## 核心要点

- 要点1
- 要点2
- 要点3（3-5个最重要的观点）

## 详细摘要

（按主题组织的结构化摘要，使用小标题分段，插入 [[双向链接]]）

## 提到的概念

[[概念1]] · [[概念2]] · ...

## 提到的公司

[[公司1]] · [[公司2]] · ...

## 提到的人物

[[人物1]] · [[人物2]] · ...

## 原文金句

> "金句1"

> "金句2"

> "金句3"（选择最精彩的 3-5 句）
```

## 原文

---
{raw_text[:8000]}
---

请严格按照上述格式输出，只输出 Markdown 内容，不要有任何其他解释。"""


# ── 生成 frontmatter ──────────────────────────────────────────────────────────
def generate_frontmatter(title: str, page_type: str, source_path: str, 
                         tags: list, doc_date: str = "") -> str:
    today = date.today().isoformat()
    date_str = doc_date or today
    tags_str = ", ".join(f'"{t}"' for t in tags)
    return f"""---
title: "{title}"
type: {page_type}
date: {date_str}
source: "{source_path}"
tags: [{tags_str}]
related: []
created: {today}
updated: {today}
---
"""


# ── 从文件名提取日期 ──────────────────────────────────────────────────────────
def extract_date(filename: str) -> str:
    # 提取年份
    m = re.search(r'(\d{4})', filename)
    if m:
        year = m.group(1)
        return f"{year}-01-01"
    return ""


# ── Anthropic 客户端 ──────────────────────────────────────────────────────────
def create_client():
    # 尝试从 .env 文件加载
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    
    if not api_key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("ANTHROPIC_BASE_URL="):
                base_url = line.split("=", 1)[1].strip().strip('"').strip("'")
    
    if not api_key:
        print("错误：未找到 ANTHROPIC_API_KEY，请在 code/web/.env 中配置")
        sys.exit(1)
    
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5")
    
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    
    return anthropic.Anthropic(**kwargs), model


# ── 处理单个文件 ──────────────────────────────────────────────────────────────
def ingest_file(src_path: Path, wiki_sub: str, page_type: str, base_tags: list,
                client, model: str, dry_run: bool = False, force: bool = False) -> bool:
    title = src_path.stem
    wiki_dir = WIKI_DIR / wiki_sub
    dst_path = wiki_dir / src_path.name
    
    # 检查是否已存在
    if dst_path.exists() and not force:
        print(f"  跳过（已存在）: {src_path.name}")
        return False
    
    if dry_run:
        print(f"  [预览] 将摄取: {src_path.name} → {dst_path.relative_to(BASE_DIR)}")
        return True
    
    print(f"  摄取: {src_path.name}...", end=" ", flush=True)
    
    # 读取原文
    raw_text = src_path.read_text(encoding="utf-8")
    
    # 加载实体
    entities = load_entity_names()
    
    # 构建提示词
    prompt = build_prompt(raw_text, page_type, title, entities)
    
    try:
        # 调用 API
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = message.content[0].text.strip()
        
        # 生成 frontmatter
        doc_date = extract_date(title)
        tags = base_tags + [page_type]
        source_rel = f"raw/{src_path.relative_to(RAW_DIR).as_posix()}"
        
        frontmatter = generate_frontmatter(title, page_type, source_rel, tags, doc_date)
        
        # 如果摘要中有 # 标题，去掉（frontmatter 后面会重新加）
        summary_lines = summary.split("\n")
        if summary_lines and summary_lines[0].startswith("# "):
            summary_lines = summary_lines[1:]
            while summary_lines and not summary_lines[0].strip():
                summary_lines.pop(0)
            summary = "\n".join(summary_lines)
        
        final = frontmatter + f"# {title}\n\n" + summary + "\n"
        
        # 写入文件
        wiki_dir.mkdir(parents=True, exist_ok=True)
        dst_path.write_text(final, encoding="utf-8")
        
        print(f"✓ ({len(final)} 字符)")
        
        # 更新 log
        append_log(f"摄取: {src_path.name} → {dst_path.relative_to(BASE_DIR)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


# ── 更新日志 ──────────────────────────────────────────────────────────────────
def append_log(message: str):
    today = date.today().isoformat()
    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 操作日志\n\n"
    
    # 检查今天的日期头是否存在
    if f"## {today}" not in content:
        content += f"\n## {today}\n\n"
    
    content += f"- {message}\n"
    LOG_PATH.write_text(content, encoding="utf-8")


# ── 主函数 ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Anthropic API 批量摄取信件和访谈")
    parser.add_argument("--all", action="store_true", help="摄取所有未处理的文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--force", action="store_true", help="强制重新生成（覆盖已有）")
    parser.add_argument("--dir", help="只处理指定子目录（如 letters/berkshire）")
    parser.add_argument("--file", help="只处理单个文件名")
    parser.add_argument("--delay", type=float, default=1.0, help="API 调用间隔（秒）")
    args = parser.parse_args()
    
    if not (args.all or args.dir or args.file):
        parser.print_help()
        return
    
    # 初始化客户端（dry-run 时不需要）
    client, model = (None, None)
    if not args.dry_run:
        client, model = create_client()
        print(f"使用模型: {model}")
    
    total_success = 0
    total_fail = 0
    
    for target in INGEST_TARGETS:
        raw_sub = target["raw_sub"]
        raw_dir = RAW_DIR / raw_sub
        
        if not raw_dir.exists():
            continue
        
        # 过滤目标
        if args.dir and not raw_sub.startswith(args.dir.rstrip("/")):
            continue
        
        files = sorted(raw_dir.glob("*.md"))
        
        # 过滤单文件
        if args.file:
            files = [f for f in files if f.name == args.file or f.stem == args.file]
        
        if not files:
            continue
        
        print(f"\n处理 {raw_sub}（{len(files)} 个文件）...")
        
        for src_path in files:
            # 跳过 SUMMARY.md
            if src_path.name == "SUMMARY.md":
                continue
            
            success = ingest_file(
                src_path,
                target["wiki_sub"],
                target["type"],
                target["tags"],
                client, model,
                args.dry_run,
                args.force,
            )
            
            if success:
                total_success += 1
                if not args.dry_run and args.delay > 0:
                    time.sleep(args.delay)  # 避免 API 限速
            else:
                if not (success is False):
                    total_fail += 1
    
    print(f"\n{'[预览]' if args.dry_run else '完成'}")
    print(f"  成功: {total_success}")
    if total_fail:
        print(f"  失败: {total_fail}")


if __name__ == "__main__":
    main()
