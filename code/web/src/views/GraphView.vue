<template>
  <div>
    <!-- Hero -->
    <div class="hero">
      <h1 class="hero-title">🕸️ 知识图谱</h1>
      <div class="hero-subtitle">
        {{ nodeCount }} 个节点 · {{ edgeCount }} 条关系
        <span style="margin-left:16px;font-size:12px;opacity:0.6">滚轮缩放 · 拖拽节点 · 点击跳转</span>
      </div>
    </div>

    <div class="content-area">
      <!-- 图例 -->
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px">
        <div v-for="l in legend" :key="l.label" style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text-secondary)">
          <div :style="{width:'12px',height:'12px',borderRadius:'50%',background:l.color}"></div>
          {{ l.label }}
        </div>
      </div>

      <!-- 图谱容器 -->
      <div class="graph-container">
        <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:500px;color:var(--text-tertiary)">
          加载图谱数据...
        </div>
        <svg v-else ref="svgEl" :width="svgW" :height="svgH" style="display:block;cursor:grab"></svg>
      </div>

      <!-- Tooltip -->
      <div v-if="tooltip.visible" class="tooltip" :style="{left:tooltip.x+'px',top:tooltip.y+'px',position:'fixed'}">
        {{ tooltip.text }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'

const router = useRouter()
const svgEl = ref(null)
const loading = ref(true)
const nodeCount = ref(0)
const edgeCount = ref(0)
const svgW = ref(1000)
const svgH = ref(600)
const tooltip = ref({ visible: false, x: 0, y: 0, text: '' })

const legend = [
  { label: '概念', color: '#3B7DD8' },
  { label: '公司', color: '#47956A' },
  { label: '人物', color: '#C5961B' },
  { label: '访谈', color: '#7E5FAD' },
]

// 节点颜色
const typeColor = {
  concept: '#3B7DD8',
  company: '#47956A',
  person: '#C5961B',
  'interview-summary': '#7E5FAD',
  'letter-summary': '#C2604A',
  insight: '#40A8E0',
  unknown: '#888899',
}

let simulation = null

function initGraph(data) {
  const el = svgEl.value
  if (!el) return

  // 计算容器大小
  const container = el.parentElement
  const W = container.clientWidth || 1000
  const H = Math.max(window.innerHeight - 280, 500)
  svgW.value = W
  svgH.value = H

  const nodes = data.nodes.map(n => ({ ...n }))
  const links = data.edges.map(e => ({ ...e }))

  nodeCount.value = nodes.length
  edgeCount.value = links.length

  const svg = d3.select(el)
  svg.selectAll('*').remove()

  // Zoom
  const zoom = d3.zoom()
    .scaleExtent([0.2, 5])
    .on('zoom', e => g.attr('transform', e.transform))

  svg.call(zoom)
  svg.on('dblclick.zoom', null)

  const g = svg.append('g')

  // 模拟
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(50))
    .force('charge', d3.forceManyBody().strength(-80))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(8))

  // 连线
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#E5E5EA')
    .attr('stroke-width', 0.5)
    .attr('stroke-opacity', 0.8)

  // 节点组
  const nodeG = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .style('cursor', 'pointer')
    .call(
      d3.drag()
        .on('start', (e, d) => {
          if (!e.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
        .on('end', (e, d) => {
          if (!e.active) simulation.alphaTarget(0)
          d.fx = null; d.fy = null
        })
    )
    .on('click', (e, d) => {
      if (d.type !== 'unknown') {
        const catMap = {
          concept: 'concepts',
          company: 'companies',
          person: 'people',
          'interview-summary': 'interviews',
          'letter-summary': 'letters',
          insight: 'insights',
        }
        const cat = catMap[d.type] || 'concepts'
        router.push(`/page/${cat}/${encodeURIComponent(d.id)}`)
      }
    })
    .on('mouseover', (e, d) => {
      if (d.type !== 'unknown') {
        tooltip.value = { visible: true, x: e.clientX + 12, y: e.clientY - 8, text: d.id }
      }
    })
    .on('mouseout', () => { tooltip.value.visible = false })

  // 节点圆
  nodeG.append('circle')
    .attr('r', d => d.type === 'unknown' ? 3 : 6)
    .attr('fill', d => typeColor[d.type] || '#888899')
    .attr('stroke', '#FFFFFF')
    .attr('stroke-width', 1.5)

  // 节点标签（只显示非 unknown）
  nodeG.filter(d => d.type !== 'unknown')
    .append('text')
    .attr('dx', 9)
    .attr('dy', 3)
    .attr('font-size', '9px')
    .attr('fill', '#6B6B6B')
    .attr('pointer-events', 'none')
    .text(d => d.id.slice(0, 6))

  // Tick
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
    nodeG.attr('transform', d => `translate(${d.x},${d.y})`)
  })
}

onMounted(async () => {
  try {
    const res = await fetch('/data/graph.json')
    if (res.ok) {
      const data = await res.json()
      loading.value = false
      setTimeout(() => initGraph(data), 50)
    } else {
      loading.value = false
    }
  } catch (e) {
    loading.value = false
  }
})

onUnmounted(() => {
  if (simulation) simulation.stop()
})
</script>
