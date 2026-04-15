#!/usr/bin/env node
/**
 * build-data.js — Node.js 版本的前端数据构建脚本
 * 扫描 wiki/ 和 raw/ 生成前端所需的 JSON + Markdown 数据文件
 * 
 * 用法: node scripts/build-data.js
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync, readdirSync, statSync } from 'fs'
import { join, dirname, resolve } from 'path'
import { fileURLToPath } from 'url'

// import.meta.url 在中文路径下可能被 URL 编码，用 decodeURIComponent 修复
const __filename = decodeURIComponent(fileURLToPath(import.meta.url))
const __dirname = dirname(__filename)
const WEB_DIR = resolve(__dirname, '..')
const BASE_DIR = resolve(WEB_DIR, '..', '..')

const WIKI_DIR = join(BASE_DIR, 'wiki')
const RAW_DIR = join(BASE_DIR, 'raw')
const DATA_DIR = join(WEB_DIR, 'public', 'data')
const PAGES_DIR = join(DATA_DIR, 'pages')
const RAW_OUT_DIR = join(DATA_DIR, 'raw')

const CATEGORY_DIRS = {
  concepts:   { type: 'concept',            dir: join(WIKI_DIR, 'concepts') },
  companies:  { type: 'company',            dir: join(WIKI_DIR, 'companies') },
  people:     { type: 'person',             dir: join(WIKI_DIR, 'people') },
  interviews: { type: 'interview-summary',  dir: join(WIKI_DIR, 'interviews') },
  letters:    { type: 'letter-summary',     dir: join(WIKI_DIR, 'letters') },
  insights:   { type: 'insight',            dir: join(WIKI_DIR, 'insights') },
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function parseFrontmatter(text) {
  if (!text.startsWith('---')) return { meta: {}, body: text }
  const parts = text.split('---', 3)
  if (parts.length < 3) return { meta: {}, body: text }
  const meta = {}
  // 处理 CRLF 换行
  const lines = parts[1].trim().replace(/\r\n/g, '\n').split('\n')
  for (const line of lines) {
    const m = line.match(/^(\w+):\s*(.+)$/)
    if (m) {
      let val = m[2].trim().replace(/^['"]|['"]$/g, '')
      if (val.startsWith('[') && val.endsWith(']')) {
        meta[m[1]] = val.slice(1, -1).split(',').map(x => x.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean)
      } else {
        meta[m[1]] = val
      }
    }
  }
  return { meta, body: parts[2].trim() }
}

function extractSummary(body, maxLen = 200) {
  for (const line of body.split('\n')) {
    const s = line.trim()
    if (s && !s.startsWith('#') && !s.startsWith('-')) {
      const clean = s.replace(/\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]/g, '$1')
      if (clean.length > 30) return clean.slice(0, maxLen) + (clean.length > maxLen ? '...' : '')
    }
  }
  return ''
}

function extractLinks(text) {
  const matches = text.matchAll(/\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]/g)
  return [...new Set([...matches].map(m => m[1]))]
}

function readDir(dir) {
  if (!existsSync(dir)) return []
  return readdirSync(dir).filter(f => f.endsWith('.md'))
}

function copyRecursive(src, dst) {
  mkdirSync(dst, { recursive: true })
  for (const f of readdirSync(src)) {
    const srcF = join(src, f)
    const dstF = join(dst, f)
    if (statSync(srcF).isDirectory()) {
      copyRecursive(srcF, dstF)
    } else {
      copyFileSync(srcF, dstF)
    }
  }
}

// ── Build wiki-index ──────────────────────────────────────────────────────────
function buildWikiIndex() {
  const pages = []
  for (const [cat, { type, dir }] of Object.entries(CATEGORY_DIRS)) {
    if (!existsSync(dir)) continue
    const files = readDir(dir).sort()
    for (const file of files) {
      const text = readFileSync(join(dir, file), 'utf-8')
      const { meta, body } = parseFrontmatter(text)
      if (!meta.title) continue
      const links = extractLinks(body)
      pages.push({
        title: meta.title,
        slug: file.replace('.md', ''),
        type: meta.type || type,
        category: cat,
        date: meta.date || '',
        source: meta.source || '',
        tags: meta.tags || [],
        summary: meta.summary || extractSummary(body),
        links,
        path: `${cat}/${file.replace('.md', '')}`,
      })
    }
  }
  console.log(`  wiki-index: ${pages.length} 个页面`)
  return pages
}

// ── Build graph ───────────────────────────────────────────────────────────────
function buildGraph(index) {
  const nodesSet = new Set()
  const nodes = []
  const edgesSet = new Set()
  const edges = []

  for (const p of index) {
    if (!nodesSet.has(p.title)) {
      nodes.push({ id: p.title, type: p.type, category: p.category })
      nodesSet.add(p.title)
    }
  }

  for (const p of index) {
    for (const link of p.links) {
      if (!nodesSet.has(link)) {
        nodes.push({ id: link, type: 'unknown', category: 'unknown' })
        nodesSet.add(link)
      }
      const key = [p.title, link].sort().join('|||')
      if (!edgesSet.has(key)) {
        edges.push({ source: p.title, target: link })
        edgesSet.add(key)
      }
    }
  }
  console.log(`  graph: ${nodes.length} 节点，${edges.length} 边`)
  return { nodes, edges }
}

// ── Main ──────────────────────────────────────────────────────────────────────
console.log('构建前端数据...')

mkdirSync(DATA_DIR, { recursive: true })
mkdirSync(PAGES_DIR, { recursive: true })
mkdirSync(RAW_OUT_DIR, { recursive: true })

const index = buildWikiIndex()
writeFileSync(join(DATA_DIR, 'wiki-index.json'), JSON.stringify(index, null, 2), 'utf-8')

const graph = buildGraph(index)
writeFileSync(join(DATA_DIR, 'graph.json'), JSON.stringify(graph, null, 2), 'utf-8')

writeFileSync(join(DATA_DIR, 'search-index.json'),
  JSON.stringify(index.map(p => ({ title: p.title, slug: p.slug, category: p.category, type: p.type, summary: p.summary, tags: p.tags, path: p.path })), null, 2),
  'utf-8')

// Copy wiki pages
let pageCount = 0
for (const [cat, { dir }] of Object.entries(CATEGORY_DIRS)) {
  if (!existsSync(dir)) continue
  const outDir = join(PAGES_DIR, cat)
  mkdirSync(outDir, { recursive: true })
  for (const file of readDir(dir)) {
    copyFileSync(join(dir, file), join(outDir, file))
    pageCount++
  }
}
console.log(`  复制了 ${pageCount} 个 wiki 页面`)

// Copy raw files
let rawCount = 0
for (const sub of ['letters', 'interviews']) {
  const srcDir = join(RAW_DIR, sub)
  if (!existsSync(srcDir)) continue
  const dstDir = join(RAW_OUT_DIR, sub)
  copyRecursive(srcDir, dstDir)
  rawCount++
}
console.log(`  复制了 ${rawCount} 个原始目录`)

console.log('\n构建完成！')
