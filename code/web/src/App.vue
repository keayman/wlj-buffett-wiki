<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-scroll">
        <!-- Logo -->
        <div class="sidebar-logo">
          <router-link to="/">
            <span class="logo-icon">📚</span>
            <span>WLJ-巴菲特知识库</span>
          </router-link>
        </div>

        <!-- 首页 -->
        <router-link to="/" class="nav-item" exact-active-class="active">
          <span class="nav-icon">🏠</span>
          <span class="nav-text">知识库首页</span>
        </router-link>

        <div class="nav-divider"></div>

        <!-- 索引 -->
        <div class="nav-label">索引</div>
        <router-link to="/category/concepts" class="nav-item" active-class="active">
          <span class="nav-icon">💡</span>
          <span class="nav-text">核心概念</span>
          <span class="nav-count">{{ stats.concepts }}</span>
        </router-link>
        <router-link to="/category/companies" class="nav-item" active-class="active">
          <span class="nav-icon">🏢</span>
          <span class="nav-text">投资公司</span>
          <span class="nav-count">{{ stats.companies }}</span>
        </router-link>
        <router-link to="/category/people" class="nav-item" active-class="active">
          <span class="nav-icon">👤</span>
          <span class="nav-text">关键人物</span>
          <span class="nav-count">{{ stats.people }}</span>
        </router-link>

        <div class="nav-divider"></div>

        <!-- 来源 -->
        <div class="nav-label">来源</div>
        <router-link to="/category/interviews" class="nav-item" active-class="active">
          <span class="nav-icon">🎤</span>
          <span class="nav-text">访谈与演讲</span>
          <span class="nav-count">{{ stats.interviews }}</span>
        </router-link>
        <router-link to="/category/letters" class="nav-item" active-class="active">
          <span class="nav-icon">✉️</span>
          <span class="nav-text">股东信</span>
          <span class="nav-count">{{ stats.letters }}</span>
        </router-link>

        <div class="nav-divider"></div>

        <!-- 工具 -->
        <div class="nav-label">工具</div>
        <router-link to="/graph" class="nav-item" active-class="active">
          <span class="nav-icon">🕸️</span>
          <span class="nav-text">知识图谱</span>
        </router-link>
      </div>

      <!-- AI 巴菲特 固定底部 -->
      <div class="sidebar-footer">
        <router-link to="/chat" class="ai-btn">
          <span>🧑‍💼</span>
          <span>AI 巴菲特</span>
          <span class="ai-badge">NEW</span>
        </router-link>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref({ concepts: 49, companies: 61, people: 7, interviews: 26, letters: 98 })

onMounted(async () => {
  try {
    const res = await fetch('/data/wiki-index.json')
    if (!res.ok) return
    const data = await res.json()
    const s = { concepts: 0, companies: 0, people: 0, interviews: 0, letters: 0 }
    data.forEach(p => {
      if (p.category === 'concepts') s.concepts++
      else if (p.category === 'companies') s.companies++
      else if (p.category === 'people') s.people++
      else if (p.category === 'interviews') s.interviews++
      else if (p.category === 'letters') s.letters++
    })
    // 只更新非零值
    if (s.concepts) stats.value.concepts = s.concepts
    if (s.companies) stats.value.companies = s.companies
    if (s.people) stats.value.people = s.people
    if (s.interviews) stats.value.interviews = s.interviews
    if (s.letters) stats.value.letters = s.letters
  } catch (e) {
    // 保留默认值
  }
})
</script>
