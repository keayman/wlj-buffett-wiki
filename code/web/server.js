// server.js — WLJ-巴菲特知识库后端
// Express + Anthropic API + SSE 流式输出
// 启动方式: node --env-file=.env server.js  (本地开发)
//          node server.js                     (生产环境，环境变量由 fly.io 注入)

import express from 'express'
import cors from 'cors'
import crypto from 'crypto'
import { readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import Anthropic from '@anthropic-ai/sdk'

const __dirname = dirname(fileURLToPath(import.meta.url))
// 优先从 dist/data 读取（生产环境 Vite 会把 public/data 复制到 dist/data）
// 其次从 public/data 读取（开发环境）
const DATA_DIR = existsSync(join(__dirname, 'dist', 'data'))
  ? join(__dirname, 'dist', 'data')
  : join(__dirname, 'public', 'data')
const PAGES_DIR = join(DATA_DIR, 'pages')

// ── 环境变量 ──────────────────────────────────────────────────────────────────
const API_KEY = process.env.ANTHROPIC_API_KEY
const BASE_URL = process.env.ANTHROPIC_BASE_URL
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-opus-4-5'
const PASSWORD = process.env.ACCESS_PASSWORD || 'REDACTED_PASSWORD'
const PORT = process.env.PORT || 3001
const HOST = process.env.HOST || '0.0.0.0'
const SESSION_SECRET = crypto.randomBytes(32).toString('hex')

if (!API_KEY) {
  console.error('错误：未设置 ANTHROPIC_API_KEY 环境变量')
  process.exit(1)
}

// ── Anthropic 客户端 ──────────────────────────────────────────────────────────
const clientOpts = { apiKey: API_KEY }
if (BASE_URL) clientOpts.baseURL = BASE_URL
const anthropic = new Anthropic(clientOpts)

// ── 安全：Session Token 管理 ──────────────────────────────────────────────────
const sessions = new Map() // token -> { createdAt, lastUsed }
const SESSION_TTL = 24 * 60 * 60 * 1000 // 24小时
const MAX_SESSIONS = 1000

function createSessionToken() {
  // 清理过期 session
  const now = Date.now()
  for (const [token, s] of sessions) {
    if (now - s.createdAt > SESSION_TTL) sessions.delete(token)
  }
  // 限制最大 session 数
  if (sessions.size >= MAX_SESSIONS) {
    const oldest = [...sessions.entries()].sort((a, b) => a[1].createdAt - b[1].createdAt)[0]
    if (oldest) sessions.delete(oldest[0])
  }
  const token = crypto.randomBytes(32).toString('hex')
  sessions.set(token, { createdAt: now, lastUsed: now })
  return token
}

function validateSession(token) {
  if (!token) return false
  const s = sessions.get(token)
  if (!s) return false
  if (Date.now() - s.createdAt > SESSION_TTL) {
    sessions.delete(token)
    return false
  }
  s.lastUsed = Date.now()
  return true
}

// ── 安全：Rate Limiting ───────────────────────────────────────────────────────
const rateLimits = new Map() // ip -> { count, resetAt }
const RATE_WINDOW = 60 * 1000 // 1分钟窗口
const CHAT_RATE_LIMIT = 10    // 每分钟最多10次 chat 请求
const VERIFY_RATE_LIMIT = 20  // 每分钟最多20次密码验证

function checkRateLimit(ip, limit) {
  const now = Date.now()
  let entry = rateLimits.get(ip)
  if (!entry || now > entry.resetAt) {
    entry = { count: 0, resetAt: now + RATE_WINDOW }
    rateLimits.set(ip, entry)
  }
  entry.count++
  return entry.count <= limit
}

// ── 预加载知识库数据 ──────────────────────────────────────────────────────────
let wikiIndex = []   // [{title, summary, links, category, slug, path, type}]
let graphData = null // {nodes, edges}
let neighbors = {}  // {nodeId -> [nodeId]}
let indexByTitle = {} // {title -> index_entry}

function loadKnowledgeBase() {
  try {
    const idxPath = join(DATA_DIR, 'wiki-index.json')
    if (existsSync(idxPath)) {
      wikiIndex = JSON.parse(readFileSync(idxPath, 'utf-8'))
      wikiIndex.forEach(p => { indexByTitle[p.title] = p })
      console.log(`已加载 ${wikiIndex.length} 个知识页面`)
    }

    const graphPath = join(DATA_DIR, 'graph.json')
    if (existsSync(graphPath)) {
      graphData = JSON.parse(readFileSync(graphPath, 'utf-8'))
      // 构建邻接表
      neighbors = {}
      graphData.edges.forEach(e => {
        if (!neighbors[e.source]) neighbors[e.source] = []
        if (!neighbors[e.target]) neighbors[e.target] = []
        neighbors[e.source].push(e.target)
        neighbors[e.target].push(e.source)
      })
      console.log(`已加载图谱：${graphData.nodes.length} 节点，${graphData.edges.length} 边`)
    }
  } catch (e) {
    console.error('加载知识库失败:', e.message)
  }
}

loadKnowledgeBase()

// ── 两阶段检索 ────────────────────────────────────────────────────────────────

/** 生成中文 n-gram 窗口 */
function ngrams(text, n = 3) {
  const grams = new Set()
  const normalized = text.replace(/\r\n/g, '\n')
  // 滑动窗口 (2-4字)
  for (let k = 2; k <= Math.min(4, normalized.length); k++) {
    for (let i = 0; i <= normalized.length - k; i++) {
      grams.add(normalized.slice(i, i + k))
    }
  }
  // 空格分词（处理英文）
  normalized.split(/\s+/).forEach(w => { if (w) grams.add(w) })
  return grams
}

/** 对单个页面评分 */
function scoreEntry(entry, question, qNgrams) {
  let score = 0
  const title = entry.title || ''
  const summary = entry.summary || ''
  const links = entry.links || []
  const titleLower = title.toLowerCase()
  const qLower = question.toLowerCase()

  // 标题完全包含在问题中
  if (title && qLower.includes(titleLower)) score += 50
  // 问题包含在标题中
  if (title && titleLower.includes(qLower)) score += 40
  // ngram 命中标题
  qNgrams.forEach(g => {
    if (titleLower.includes(g.toLowerCase())) score += 8
    if (summary.toLowerCase().includes(g.toLowerCase())) score += 3
  })
  // links 命中
  links.forEach(l => {
    if (qLower.includes(l.toLowerCase()) || l.toLowerCase().includes(qLower.slice(0, 4))) {
      score += 6
    }
  })
  return score
}

/** 两阶段检索 */
function retrieve(question) {
  const qNgrams = ngrams(question)

  // 阶段 1：直接命中
  const scored = wikiIndex
    .map(entry => ({ entry, score: scoreEntry(entry, question, qNgrams) }))
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)

  const result = scored.map(x => x.entry)
  const resultTitles = new Set(result.map(e => e.title))

  // 阶段 2：图谱关联扩展
  if (graphData) {
    const candidates = []
    result.forEach(entry => {
      const nbrs = neighbors[entry.title] || []
      nbrs.forEach(nbr => {
        if (resultTitles.has(nbr)) return
        const nbrEntry = indexByTitle[nbr]
        if (!nbrEntry) return
        const nbrScore = scoreEntry(nbrEntry, question, qNgrams)
        if (nbrScore > 0) candidates.push({ entry: nbrEntry, score: nbrScore })
      })
    })
    candidates
      .sort((a, b) => b.score - a.score)
      .slice(0, 2)
      .forEach(c => {
        if (!resultTitles.has(c.entry.title)) {
          result.push(c.entry)
          resultTitles.add(c.entry.title)
        }
      })
  }

  return result
}

/** 读取 wiki 页面内容 */
function loadPageContent(entry) {
  try {
    const cat = entry.category || 'concepts'
    const slug = entry.slug || entry.title
    const filePath = join(PAGES_DIR, cat, `${slug}.md`)
    if (existsSync(filePath)) {
      const text = readFileSync(filePath, 'utf-8')
      return text.slice(0, 3000)
    }
    // 用摘要 fallback
    return entry.summary || entry.title
  } catch (e) {
    return entry.summary || entry.title
  }
}

// ── 系统提示词 ────────────────────────────────────────────────────────────────
function buildSystemPrompt(contextPages) {
  const context = contextPages
    .map(entry => {
      const content = loadPageContent(entry)
      return `### ${entry.title}\n${content}`
    })
    .join('\n\n---\n\n')

  return `你是沃伦·巴菲特。根据以下知识库内容，以巴菲特的第一人称风格回答问题。

要求：
1. 以第一人称（"我"）回答，模拟巴菲特的语气：直接、坦率、用简单例子说明复杂道理
2. 引用知识库中的具体案例、数据和原话
3. 偶尔用幽默感，就像巴菲特在股东大会上的讲话风格
4. 如果问题超出知识库范围，坦率说明但仍尝试给出有价值的见解
5. 回答结构清晰，适当分段

知识库内容：
---
${context}
---`
}

// ── Express 服务器 ────────────────────────────────────────────────────────────
const app = express()
app.use(cors())
app.use(express.json())
app.use(express.static(join(__dirname, 'dist')))
// 开发模式下不提供 dist，让 Vite 代理处理

// 密码验证接口（返回 session token，不暴露密码是否正确）
app.post('/api/verify', (req, res) => {
  const ip = req.ip || req.connection.remoteAddress
  if (!checkRateLimit(ip, VERIFY_RATE_LIMIT)) {
    return res.status(429).json({ ok: false, error: '请求过于频繁，请稍后再试' })
  }

  const { password } = req.body
  if (password === PASSWORD) {
    const token = createSessionToken()
    res.json({ ok: true, token })
  } else {
    // 固定延迟，防止暴力破解时序攻击
    setTimeout(() => {
      res.json({ ok: false })
    }, 500)
  }
})

// 登出接口
app.post('/api/logout', (req, res) => {
  const token = req.headers['x-session-token']
  if (token) sessions.delete(token)
  res.json({ ok: true })
})

// AI 对话接口（SSE 流式输出）
app.post('/api/chat', async (req, res) => {
  const ip = req.ip || req.connection.remoteAddress
  if (!checkRateLimit(ip, CHAT_RATE_LIMIT)) {
    return res.status(429).json({ error: '请求过于频繁，请稍后再试' })
  }

  // Session token 验证（替代明文密码传输）
  const token = req.headers['x-session-token']
  if (!validateSession(token)) {
    return res.status(401).json({ error: '未授权，请重新验证密码' })
  }

  const { question, history = [] } = req.body

  if (!question?.trim()) {
    return res.status(400).json({ error: '问题不能为空' })
  }

  // 限制消息长度
  if (question.length > 2000) {
    return res.status(400).json({ error: '问题过长，请控制在2000字以内' })
  }

  // 限制对话历史长度
  const safeHistory = history.slice(-8).map(m => ({
    role: m.role,
    content: String(m.content || '').slice(0, 1000),
  }))

  // SSE headers
  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.flushHeaders()

  const send = (data) => {
    res.write(`data: ${JSON.stringify(data)}\n\n`)
  }

  try {
    // 检索相关页面
    const relevantPages = retrieve(question)
    const sources = relevantPages.map(p => p.title)

    // 构建对话历史
    const messages = [
      ...safeHistory,
      { role: 'user', content: question },
    ]

    // 流式调用 API
    const stream = await anthropic.messages.stream({
      model: MODEL,
      max_tokens: 2048,
      system: buildSystemPrompt(relevantPages),
      messages,
    })

    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta' && chunk.delta?.text) {
        send({ text: chunk.delta.text })
      }
    }

    send({ done: true, sources })

  } catch (e) {
    console.error('API 错误:', e.message)
    send({ text: '\n\n抱歉，生成回复时遇到了问题，请稍后再试。', done: true, sources: [] })
  }

  res.end()
})

// 健康检查（不暴露内部信息）
app.get('/api/health', (req, res) => {
  res.json({ ok: true, pages: wikiIndex.length })
})

app.listen(PORT, HOST, () => {
  console.log(`\n🎩 WLJ-巴菲特知识库后端`)
  console.log(`   端口: ${PORT}`)
  console.log(`   模型: ${MODEL}`)
  console.log(`   知识页面: ${wikiIndex.length}`)
  console.log(`   图谱节点: ${graphData?.nodes?.length || 0}`)
  console.log(`\n   访问: http://localhost:${PORT}/api/health\n`)
})
