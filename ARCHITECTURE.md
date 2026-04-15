# WLJ-巴菲特知识库 — 架构文档

## 整体架构

```
buffet1/
├── raw/          ← 原始资料（只读）
├── wiki/         ← LLM 预编译知识页面（Obsidian 兼容）
├── code/web/     ← Vue 3 前端 + Express 后端
└── docs/         ← 架构文档
```

## 数据流

```
原始 Markdown (raw/)
       ↓ convert_existing.py (概念/公司/人物，不调 API)
       ↓ ingest.py (信件/访谈，调 Anthropic API)
wiki/ (241 个结构化页面)
       ↓ build-data.py
public/data/ (JSON + Markdown 副本)
       ↓
Vue 3 前端 (浏览 + 搜索 + D3.js 图谱)
       ↓ /api/chat
Express 后端 (两阶段检索 + SSE 流式输出)
       ↓
AI 巴菲特 (基于 wiki 知识的巴菲特风格对话)
```

## 模块说明

### raw/ — 原始资料
- `letters/partnership/` — 35 篇合伙人信（1956-1970）
- `letters/berkshire/` — 60 篇股东信（1965-2024）
- `letters/special/` — 3 篇特别信件
- `interviews/` — 26 篇访谈与演讲
- `concepts/` — 49 个投资概念
- `companies/` — 61 家投资公司
- `people/` — 7 位关键人物

### wiki/ — 知识页面
- 总计 241 个页面
- 使用 YAML frontmatter + [[双向链接]]
- 兼容 Obsidian 图谱视图

### code/web/ — 前端网站
- **Vue 3** + Vite（ESM）
- **D3.js** 知识图谱可视化
- **Express** 后端 API（:3001）
- **Anthropic SDK** 流式输出
- 设计风格：深邃蓝金配色

## 知识图谱规模（目标）
- 节点：~567 个
- 边：~4000+ 条

## 启动命令

```bash
cd buffet1/

# 步骤1：转换已有概念/公司/人物
python code/convert_existing.py

# 步骤2：摄取信件和访谈（需 ANTHROPIC_API_KEY）
python code/ingest.py --all

# 步骤3：生成前端数据
python code/web/scripts/build-data.py

# 步骤4：启动服务
cd code/web
npm install
node --env-file=.env server.js   # 后端 :3001
npx vite --host                   # 前端 :5173
```
