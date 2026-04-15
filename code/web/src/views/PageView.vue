<template>
  <div>
    <!-- 面包屑 -->
    <div class="breadcrumb">
      <router-link to="/">首页</router-link>
      <span class="breadcrumb-sep">›</span>
      <router-link :to="`/category/${category}`">{{ categoryLabel }}</router-link>
      <span class="breadcrumb-sep">›</span>
      <span>{{ pageTitle }}</span>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" style="padding:48px;text-align:center;color:var(--text-tertiary)">加载中...</div>

    <!-- 内容 -->
    <template v-else-if="frontmatter">
      <!-- 页面头部 -->
      <div class="page-header">
        <span :class="`badge badge-${badgeType}`">{{ categoryLabel }}</span>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <div class="page-date">{{ frontmatter.date }}</div>
      </div>

      <div class="content-area">
        <!-- 正文 -->
        <div class="prose-container">
          <div class="prose" v-html="renderedBody"></div>

          <!-- 原文全文 (仅信件/访谈) -->
          <div v-if="rawText" class="raw-toggle">
            <div class="raw-toggle-header" @click="rawOpen = !rawOpen">
              <span>{{ rawOpen ? '▼' : '▶' }}</span>
              <span>📄 原文全文 — {{ rawOpen ? '收起' : '展开阅读完整原文' }}</span>
            </div>
            <div v-if="rawOpen" class="raw-body">
              <div class="prose" v-html="renderedRaw"></div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 404 -->
    <div v-else style="padding:48px;text-align:center">
      <div style="font-size:48px;margin-bottom:16px">📭</div>
      <div style="font-size:18px;font-weight:700;color:var(--text-secondary)">页面不存在</div>
      <div style="margin-top:16px">
        <router-link to="/" class="btn btn-blue">← 返回首页</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'

const route = useRoute()
const router = useRouter()
const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

const loading = ref(true)
const frontmatter = ref(null)
const bodyMd = ref('')
const rawText = ref('')
const rawOpen = ref(false)

const category = computed(() => route.params.category)
const slug = computed(() => decodeURIComponent(route.params.slug))

const categoryLabel = computed(() => {
  const m = { concepts:'💡 核心概念', companies:'🏢 投资公司', people:'👤 关键人物', interviews:'🎤 访谈与演讲', letters:'✉️ 信件', insights:'🔍 交叉分析' }
  return m[category.value] || category.value
})

const badgeType = computed(() => {
  const m = { concepts:'concept', companies:'company', people:'person', interviews:'interview', letters:'letter' }
  return m[category.value] || 'concept'
})

const pageTitle = computed(() => frontmatter.value?.title || slug.value)

// 渲染 Markdown，将 [[链接]] 转为 <a>
function renderMd(text) {
  // 将 [[实体名]] 转为链接
  let t = text.replace(/\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g, (_, target, label) => {
    const display = label || target
    // 从 target 推断 category
    const cat = guessCategory(target)
    const href = `/page/${cat}/${encodeURIComponent(target)}`
    return `[${display}](${href})`
  })
  return md.render(t)
}

// 推断链接的分类
function guessCategory(name) {
  // 基于名称特征判断
  if (/^\d{4}/.test(name)) return 'letters'
  return '_guess_' // 运行时通过 index 解析
}

// 优化版：用 wikiIndex 数据来精确推断
let wikiIndex = []
async function loadWikiIndex() {
  try {
    const r = await fetch('/data/wiki-index.json')
    if (r.ok) wikiIndex = await r.json()
  } catch (e) {}
}

function renderMdWithIndex(text) {
  const titleCatMap = {}
  wikiIndex.forEach(p => { titleCatMap[p.title] = p.category })
  
  let t = text.replace(/\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g, (_, target, label) => {
    const display = label || target
    const cat = titleCatMap[target] || guessCategoryFallback(target)
    const href = `/page/${cat}/${encodeURIComponent(target)}`
    return `[${display}](${href})`
  })
  return md.render(t)
}

function guessCategoryFallback(name) {
  if (/^\d{4}/.test(name)) return 'letters'
  if (/采访|演讲|大会|商学院|对话/.test(name)) return 'interviews'
  return 'concepts'
}

const renderedBody = computed(() => renderMdWithIndex(bodyMd.value))

const renderedRaw = computed(() => {
  if (!rawText.value) return ''
  // 过滤掉 > **Source** 和 > **Type** 行
  const filtered = rawText.value
    .split('\n')
    .filter(l => !l.trim().startsWith('> **Source**') && !l.trim().startsWith('> **Type**'))
    .join('\n')
  return md.render(filtered)
})

// 解析 frontmatter
function parseFrontmatter(text) {
  if (!text.startsWith('---')) return { fm: {}, body: text }
  const parts = text.split('---')
  if (parts.length < 3) return { fm: {}, body: text }
  
  const fmText = parts[1].trim()
  const body = parts.slice(2).join('---').trim()
  
  const fm = {}
  fmText.split('\n').forEach(line => {
    const m = line.match(/^(\w+):\s*(.+)$/)
    if (m) {
      let val = m[2].trim().replace(/^["']|["']$/g, '')
      fm[m[1]] = val
    }
  })
  
  return { fm, body }
}

async function loadPage() {
  loading.value = true
  frontmatter.value = null
  bodyMd.value = ''
  rawText.value = ''
  rawOpen.value = false

  try {
    // 尝试从 pages/ 目录加载
    const cat = route.params.category
    const sl = decodeURIComponent(route.params.slug)
    const res = await fetch(`/data/pages/${cat}/${encodeURIComponent(sl)}.md`)
    
    if (!res.ok) throw new Error('not found')
    
    const text = await res.text()
    const { fm, body } = parseFrontmatter(text)
    
    frontmatter.value = fm
    bodyMd.value = body
    
    // 加载原文（仅信件/访谈有 source 字段）
    if (fm.source && (cat === 'letters' || cat === 'interviews')) {
      try {
        const rawRes = await fetch(`/data/${fm.source.replace(/^raw\//, 'raw/')}`)
        if (rawRes.ok) rawText.value = await rawRes.text()
      } catch (e) {}
    }
    
  } catch (e) {
    frontmatter.value = null
  }
  
  loading.value = false
}

onMounted(async () => {
  await loadWikiIndex()
  await loadPage()
})

watch(() => route.params, loadPage)
</script>
