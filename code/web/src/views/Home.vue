<template>
  <div>
    <!-- Hero -->
    <div class="hero">
      <div class="hero-inner" style="display:flex;gap:24px;align-items:center">
        <div style="flex:1">
          <div class="hero-title">巴菲特投资思想知识图谱</div>
          <div class="hero-subtitle">60 年投资智慧 · {{ totalPages }} 个知识节点 · {{ totalEdges.toLocaleString() }} 条关系</div>
          <div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap">
            <router-link to="/chat" class="btn btn-primary">🧑‍💼 问 AI 巴菲特</router-link>
            <router-link to="/graph" class="btn btn-outline">🕸️ 探索知识图谱</router-link>
          </div>
        </div>
        <!-- 迷你图谱 -->
        <div style="flex-shrink:0">
          <svg ref="miniGraphSvg" width="240" height="150" style="display:block"></svg>
        </div>
      </div>
    </div>

    <div class="content-area">
      <!-- 统计卡片 -->
      <div class="stat-cards" style="margin-bottom:24px">
        <router-link to="/category/letters" class="stat-card">
          <div class="stat-card-bar" style="background:#C2604A"></div>
          <div class="stat-card-body">
            <div class="stat-row">
              <span class="stat-icon">✉️</span>
              <span class="stat-number">98</span>
            </div>
            <div class="stat-label">股东信 / 合伙人信</div>
          </div>
        </router-link>
        <router-link to="/category/concepts" class="stat-card">
          <div class="stat-card-bar" style="background:#3B7DD8"></div>
          <div class="stat-card-body">
            <div class="stat-row">
              <span class="stat-icon">💡</span>
              <span class="stat-number">49</span>
            </div>
            <div class="stat-label">核心投资概念</div>
          </div>
        </router-link>
        <router-link to="/category/companies" class="stat-card">
          <div class="stat-card-bar" style="background:#47956A"></div>
          <div class="stat-card-body">
            <div class="stat-row">
              <span class="stat-icon">🏢</span>
              <span class="stat-number">61</span>
            </div>
            <div class="stat-label">投资公司</div>
          </div>
        </router-link>
        <router-link to="/category/interviews" class="stat-card">
          <div class="stat-card-bar" style="background:#7E5FAD"></div>
          <div class="stat-card-body">
            <div class="stat-row">
              <span class="stat-icon">🎤</span>
              <span class="stat-number">26</span>
            </div>
            <div class="stat-label">访谈与演讲</div>
          </div>
        </router-link>
      </div>

      <!-- 搜索框 -->
      <div class="search-wrap" style="margin-bottom:24px">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索概念、公司、人物、信件..."
          @input="onSearch"
        />
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchQuery && searchResults.length" class="card" style="margin-bottom:24px;overflow:hidden">
        <div class="page-list">
          <router-link
            v-for="r in searchResults.slice(0, 8)"
            :key="r.path"
            :to="`/page/${r.category}/${encodeURIComponent(r.slug)}`"
            class="page-list-item"
          >
            <span style="margin-right:8px">{{ typeIcon(r.type) }}</span>
            <span class="page-list-title">{{ r.title }}</span>
            <span class="page-list-date">{{ r.category }}</span>
          </router-link>
        </div>
      </div>
      <div v-else-if="searchQuery && !searchResults.length" style="text-align:center;color:var(--text-tertiary);padding:20px 0;margin-bottom:24px;font-size:14px">
        没有找到"{{ searchQuery }}"相关内容
      </div>

      <!-- 核心投资概念 TOP 15 -->
      <div class="chip-area chip-area-concept" style="margin-bottom:20px">
        <div class="chip-area-header">
          <span class="chip-area-title">核心投资概念</span>
          <span class="chip-area-label">TOP {{ conceptChips.length }}</span>
        </div>
        <div class="chips">
          <router-link
            v-for="c in conceptChips"
            :key="c.name"
            :to="`/page/concepts/${encodeURIComponent(c.name)}`"
            class="chip"
          >
            <span>{{ c.name }}</span>
            <span class="chip-badge">{{ c.refs }}</span>
          </router-link>
        </div>
      </div>

      <!-- 重要公司 TOP 15 -->
      <div class="chip-area chip-area-company" style="margin-bottom:20px">
        <div class="chip-area-header">
          <span class="chip-area-title">重要投资公司</span>
          <span class="chip-area-label">TOP {{ companyChips.length }}</span>
        </div>
        <div class="chips">
          <router-link
            v-for="c in companyChips"
            :key="c.name"
            :to="`/page/companies/${encodeURIComponent(c.name)}`"
            class="chip chip-company"
          >
            <span>{{ c.name }}</span>
            <span class="chip-badge">{{ c.refs }}</span>
          </router-link>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
        <!-- 关键人物 -->
        <div class="card" style="padding:20px">
          <div class="section-header">
            <div class="section-title">👤 关键人物</div>
          </div>
          <div class="person-grid">
            <router-link
              v-for="p in people"
              :key="p.name"
              :to="`/page/people/${encodeURIComponent(p.name)}`"
              class="person-card"
            >
              <div class="person-avatar" :style="{ background: p.color }">
                {{ p.initials }}
              </div>
              <div class="person-name">{{ p.name }}</div>
              <div class="person-refs">{{ p.refs }} 引用</div>
            </router-link>
          </div>
        </div>

        <!-- 快速导航 -->
        <div class="card" style="padding:20px">
          <div class="section-header">
            <div class="section-title">🚀 快速导航</div>
          </div>
          <div class="quick-nav-grid">
            <router-link to="/category/letters" class="quick-nav-btn">✉️ 股东信</router-link>
            <router-link to="/category/concepts" class="quick-nav-btn">💡 核心概念</router-link>
            <router-link to="/category/companies" class="quick-nav-btn">🏢 投资公司</router-link>
            <router-link to="/category/people" class="quick-nav-btn">👤 关键人物</router-link>
            <router-link to="/category/interviews" class="quick-nav-btn">🎤 访谈演讲</router-link>
            <router-link to="/graph" class="quick-nav-btn">🕸️ 知识图谱</router-link>
          </div>
        </div>
      </div>

      <!-- 时间线 -->
      <div class="card" style="padding:20px;margin-bottom:20px">
        <div class="section-header">
          <div class="section-title">📅 时间线（1956–2025）</div>
        </div>
        <div class="timeline-wrap">
          <div class="timeline-bar">
            <div class="timeline-dots">
              <div
                v-for="doc in timelineDocs"
                :key="doc.id"
                class="timeline-dot"
                :class="doc.kind"
                :style="{ left: doc.pct + '%' }"
                :title="doc.title"
                @click="$router.push(`/page/${doc.category}/${encodeURIComponent(doc.slug)}`)"
              ></div>
            </div>
          </div>
          <div class="timeline-labels">
            <span>1956</span>
            <span>1970</span>
            <span>1985</span>
            <span>2000</span>
            <span>2010</span>
            <span>2025</span>
          </div>
        </div>
        <div class="timeline-legend">
          <div class="legend-item">
            <div class="legend-dot" style="background:#3B7DD8"></div>
            <span>合伙人信</span>
          </div>
          <div class="legend-item">
            <div class="legend-dot" style="background:#47956A"></div>
            <span>伯克希尔股东信</span>
          </div>
          <div class="legend-item">
            <div class="legend-dot" style="background:#7E5FAD"></div>
            <span>访谈演讲</span>
          </div>
          <div class="legend-item">
            <div class="legend-dot" style="background:#E5A020"></div>
            <span>特别信件</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as d3 from 'd3'

// State
const miniGraphSvg = ref(null)
const searchQuery = ref('')
const searchResults = ref([])
const conceptChips = ref([])
const companyChips = ref([])
const people = ref([])
const timelineDocs = ref([])
const totalPages = ref(241)
const totalEdges = ref(4000)

// 实体列表（fallback）
const DEFAULT_CONCEPTS = ['护城河','内在价值','安全边际','能力圈','复利','市场先生','资本配置','长期持有','管理层','竞争优势','商业模式','品牌','股东导向','集中投资','保险浮存金']
const DEFAULT_COMPANIES = ['可口可乐','苹果','盖可保险','美国运通','喜诗糖果','伯克希尔哈撒韦','BNSF铁路','富国银行','吉列','华盛顿邮报','比亚迪','西方石油','雪佛龙','美国银行','卡夫亨氏']
const DEFAULT_PEOPLE = [
  { name: '芒格', color: '#3B7DD8', initials: '芒', refs: 312 },
  { name: '格雷厄姆', color: '#47956A', initials: '格', refs: 156 },
  { name: '阿吉特·贾恩', color: '#C5961B', initials: '阿', refs: 89 },
  { name: '格雷格·阿贝尔', color: '#7E5FAD', initials: '阿', refs: 67 },
  { name: 'B夫人', color: '#C2604A', initials: 'B', refs: 45 },
  { name: '泰德·韦施勒', color: '#2E8B57', initials: '泰', refs: 38 },
  { name: '托德·库姆斯', color: '#8B4513', initials: '托', refs: 35 },
]

const PERSON_COLORS = ['#3B7DD8','#47956A','#C5961B','#7E5FAD','#C2604A','#2E8B57','#8B4513','#E56020','#5B3EA6']

// 工具函数
function typeIcon(type) {
  const m = { concept:'💡', company:'🏢', person:'👤', 'interview-summary':'🎤', 'letter-summary':'✉️' }
  return m[type] || '📄'
}

// 搜索
let wikiIndex = []
function onSearch() {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) { searchResults.value = []; return }
  searchResults.value = wikiIndex.filter(p =>
    p.title?.toLowerCase().includes(q) ||
    p.summary?.toLowerCase().includes(q) ||
    p.tags?.some(t => t.toLowerCase?.().includes(q))
  ).slice(0, 10)
}

// 迷你图谱动画
function initMiniGraph(graphData) {
  const el = miniGraphSvg.value
  if (!el || !graphData) return

  const W = 240, H = 150
  const svg = d3.select(el)
  svg.selectAll('*').remove()

  // 只取一部分节点
  const nodes = graphData.nodes.slice(0, 40).map(n => ({...n}))
  const nodeIds = new Set(nodes.map(n => n.id))
  const links = graphData.edges
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    .slice(0, 60)
    .map(e => ({...e}))

  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(20))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide(5))

  const g = svg.append('g')

  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', 'rgba(255,255,255,0.25)')
    .attr('stroke-width', 0.8)

  const colorMap = {concept:'#568DE5', company:'#5CB88A', person:'#E5C040', 'interview-summary':'#A07DE5', 'letter-summary':'#E5826A'}
  
  const node = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', d => d.type === 'unknown' ? 2.5 : 4)
    .attr('fill', d => colorMap[d.type] || '#8899BB')
    .attr('stroke', 'rgba(255,255,255,0.5)')
    .attr('stroke-width', 0.8)

  let tick = 0
  sim.on('tick', () => {
    tick++
    if (tick > 120) { sim.stop(); return }
    link
      .attr('x1', d => clamp(d.source.x, 8, W-8))
      .attr('y1', d => clamp(d.source.y, 8, H-8))
      .attr('x2', d => clamp(d.target.x, 8, W-8))
      .attr('y2', d => clamp(d.target.y, 8, H-8))
    node
      .attr('cx', d => clamp(d.x, 6, W-6))
      .attr('cy', d => clamp(d.y, 6, H-6))
  })

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)) }
}

// 时间线
function buildTimeline(wikiIdx) {
  const START = 1956, END = 2025, RANGE = END - START
  const docs = []
  
  wikiIdx.forEach(p => {
    const m = p.title?.match(/(\d{4})/)
    if (!m) return
    const year = parseInt(m[1])
    if (year < START || year > END) return
    
    let kind = 'berkshire'
    if (p.category === 'interviews') kind = 'interview'
    else if (p.title?.includes('合伙人')) kind = 'partnership'
    else if (p.tags?.includes('特别信件')) kind = 'special'
    
    docs.push({
      id: p.path,
      title: p.title,
      year,
      kind,
      category: p.category,
      slug: p.slug,
      pct: ((year - START) / RANGE) * 100,
    })
  })
  
  return docs.sort((a, b) => a.year - b.year)
}

// 统计引用次数
function countRefs(graphData, wikiIdx) {
  if (!graphData) {
    // fallback
    conceptChips.value = DEFAULT_CONCEPTS.map((n, i) => ({ name: n, refs: 80 - i * 3 }))
    companyChips.value = DEFAULT_COMPANIES.map((n, i) => ({ name: n, refs: 60 - i * 2 }))
    people.value = DEFAULT_PEOPLE
    return
  }

  const refCount = {}
  graphData.edges.forEach(e => {
    refCount[e.target] = (refCount[e.target] || 0) + 1
    refCount[e.source] = (refCount[e.source] || 0) + 1
  })

  // 从 wiki-index 提取节点类型
  const nodeType = {}
  wikiIdx.forEach(p => { nodeType[p.title] = p.type })

  const conceptNodes = wikiIdx.filter(p => p.category === 'concepts')
  const companyNodes = wikiIdx.filter(p => p.category === 'companies')
  const peopleNodes  = wikiIdx.filter(p => p.category === 'people')

  conceptChips.value = conceptNodes
    .map(p => ({ name: p.title, refs: refCount[p.title] || 0 }))
    .sort((a, b) => b.refs - a.refs)
    .slice(0, 15)

  companyChips.value = companyNodes
    .map(p => ({ name: p.title, refs: refCount[p.title] || 0 }))
    .sort((a, b) => b.refs - a.refs)
    .slice(0, 15)

  people.value = peopleNodes.map((p, i) => ({
    name: p.title,
    refs: refCount[p.title] || 0,
    color: PERSON_COLORS[i % PERSON_COLORS.length],
    initials: p.title.slice(0, 1),
  }))

  // 如果数据少，用默认
  if (!conceptChips.value.length) conceptChips.value = DEFAULT_CONCEPTS.map((n, i) => ({ name: n, refs: 80 - i*3 }))
  if (!companyChips.value.length) companyChips.value = DEFAULT_COMPANIES.map((n, i) => ({ name: n, refs: 60 - i*2 }))
  if (!people.value.length) people.value = DEFAULT_PEOPLE
}

onMounted(async () => {
  // 加载数据
  let graphData = null
  
  try {
    const [idxRes, graphRes] = await Promise.all([
      fetch('/data/wiki-index.json'),
      fetch('/data/graph.json'),
    ])
    
    if (idxRes.ok) {
      wikiIndex = await idxRes.json()
      totalPages.value = wikiIndex.length || 241
      timelineDocs.value = buildTimeline(wikiIndex)
    }
    
    if (graphRes.ok) {
      graphData = await graphRes.json()
      totalEdges.value = graphData.edges?.length || 4000
    }
  } catch (e) {
    // 使用默认值
    timelineDocs.value = buildFallbackTimeline()
  }
  
  countRefs(graphData, wikiIndex)
  
  // 稍后初始化迷你图（等 DOM 就绪）
  setTimeout(() => initMiniGraph(graphData || buildFallbackGraph()), 100)
})

function buildFallbackTimeline() {
  const docs = []
  for (let y = 1957; y <= 1970; y++) {
    docs.push({ id: `p${y}`, title: `${y} 巴菲特致合伙人信`, year: y, kind: 'partnership', category: 'letters', slug: `${y} 巴菲特致合伙人信`, pct: ((y-1956)/69)*100 })
  }
  for (let y = 1965; y <= 2024; y++) {
    docs.push({ id: `b${y}`, title: `${y} 巴菲特致股东信`, year: y, kind: 'berkshire', category: 'letters', slug: `${y} 巴菲特致股东信`, pct: ((y-1956)/69)*100 })
  }
  return docs
}

function buildFallbackGraph() {
  const nodes = [
    ...DEFAULT_CONCEPTS.slice(0, 8).map(n => ({ id: n, type: 'concept' })),
    ...DEFAULT_COMPANIES.slice(0, 8).map(n => ({ id: n, type: 'company' })),
    { id: '芒格', type: 'person' },
  ]
  const edges = []
  DEFAULT_CONCEPTS.slice(0, 8).forEach((c, i) => {
    DEFAULT_COMPANIES.slice(0, i % 4 + 1).forEach(comp => {
      edges.push({ source: c, target: comp })
    })
  })
  return { nodes, edges }
}
</script>
