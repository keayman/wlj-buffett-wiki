<template>
  <div>
    <!-- Hero -->
    <div class="hero">
      <h1 class="hero-title">{{ categoryLabel }}</h1>
      <div class="hero-subtitle">{{ filtered.length }} 个{{ categoryNoun }}</div>
    </div>

    <div class="content-area">
      <!-- 搜索 -->
      <div class="search-wrap" style="margin-bottom:16px">
        <span class="search-icon">🔍</span>
        <input v-model="q" class="search-input" :placeholder="`搜索${categoryNoun}...`" />
      </div>

      <!-- 列表 -->
      <div v-if="loading" style="text-align:center;padding:40px;color:var(--text-tertiary)">加载中...</div>
      
      <div v-else-if="filtered.length" class="page-list">
        <router-link
          v-for="p in filtered"
          :key="p.path"
          :to="`/page/${category}/${encodeURIComponent(p.slug)}`"
          class="page-list-item"
        >
          <span style="margin-right:8px;font-size:16px">{{ typeIcon(p.type) }}</span>
          <span class="page-list-title">{{ p.title }}</span>
          <span class="page-list-date">{{ formatDate(p.date) }}</span>
        </router-link>
      </div>

      <div v-else style="text-align:center;padding:40px;color:var(--text-tertiary)">
        没有找到相关内容
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const q = ref('')
const loading = ref(true)
const pages = ref([])

const category = computed(() => route.params.type)

const categoryLabel = computed(() => {
  const m = {
    concepts: '💡 核心投资概念',
    companies: '🏢 投资公司',
    people: '👤 关键人物',
    interviews: '🎤 访谈与演讲',
    letters: '✉️ 股东信 / 合伙人信',
    insights: '🔍 交叉分析',
  }
  return m[category.value] || category.value
})

const categoryNoun = computed(() => {
  const m = { concepts: '概念', companies: '公司', people: '人物', interviews: '访谈', letters: '信件', insights: '分析' }
  return m[category.value] || '条目'
})

const filtered = computed(() => {
  const kw = q.value.trim().toLowerCase()
  if (!kw) return pages.value
  return pages.value.filter(p =>
    p.title?.toLowerCase().includes(kw) ||
    p.summary?.toLowerCase().includes(kw)
  )
})

function typeIcon(type) {
  const m = { concept:'💡', company:'🏢', person:'👤', 'interview-summary':'🎤', 'letter-summary':'✉️' }
  return m[type] || '📄'
}

function formatDate(d) {
  if (!d) return ''
  return d.slice(0, 4)  // 只显示年份
}

async function loadPages() {
  loading.value = true
  try {
    const res = await fetch('/data/wiki-index.json')
    if (res.ok) {
      const all = await res.json()
      pages.value = all
        .filter(p => p.category === category.value)
        .sort((a, b) => {
          // 信件按年份排序
          if (category.value === 'letters') {
            const ya = a.title?.match(/\d{4}/)?.[0] || '0'
            const yb = b.title?.match(/\d{4}/)?.[0] || '0'
            return ya.localeCompare(yb)
          }
          return a.title?.localeCompare(b.title, 'zh') || 0
        })
    }
  } catch (e) {}
  loading.value = false
}

onMounted(loadPages)
watch(() => route.params.type, loadPages)
</script>
