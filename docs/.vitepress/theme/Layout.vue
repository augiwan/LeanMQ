<script setup>
import { ref, computed, onMounted } from 'vue'
import { useData, useRoute, withBase } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import { Sun, Moon } from 'lucide-vue-next'
import { VPNavBarSearch } from 'vitepress/theme'

const { Layout } = DefaultTheme
const { site, theme, page } = useData()
const route = useRoute()

// Dark mode toggle
const isDark = ref(true)
const toggleDarkMode = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  document.documentElement.classList.toggle('light', !isDark.value)
}

// Initialize dark mode
onMounted(() => {
  if (theme.value.appearance === 'dark' || !theme.value.appearance) {
    document.documentElement.classList.add('dark')
  }
})

// Top navigation links
const topNav = computed(() => theme.value.topNav || [])
const consoleLink = computed(() => theme.value.consoleLink || null)
const consoleText = computed(() => theme.value.consoleText || 'Console')

// Check if a nav item is active
const isActiveNav = (link) => {
  if (!link) return false
  const routePath = route.path
  const linkPath = withBase(link)

  // Exact match
  if (routePath === linkPath) return true

  // Match path including trailing slash
  if (routePath === linkPath + '/' || routePath + '/' === linkPath) return true

  // Match path as prefix (for parent routes)
  if (routePath.startsWith(linkPath + '/') && link !== '/') return true

  // Match parent path
  if (linkPath !== "/" && routePath.startsWith(linkPath.split('/').slice(0, -1).join('/'))) return true

  return false
}
</script>

<template>
  <div class="blazepress-theme">
    <!-- Custom top navbar -->
    <header class="blazepress-header">
      <div class="blazepress-header-container">
        <div class="blazepress-logo-container">
          <a :href="withBase('/')" class="site-title">{{ site.title }}</a>
        </div>

        <div class="blazepress-search-container">
          <VPNavBarSearch />
        </div>

        <div class="blazepress-top-nav">
          <a v-for="item in topNav" :key="item.text" :href="withBase(item.link)" class="blazepress-top-nav-link"
            target="_blank">
            {{ item.text }}
          </a>

          <a v-if="consoleLink" :href="withBase(consoleLink)" class="blazepress-console-button">
            {{ consoleText }}
            <span class="blazepress-arrow-icon">→</span>
          </a>

          <button class="blazepress-theme-toggle" @click="toggleDarkMode">
            <span class="icon">
              <Sun v-if="isDark" style="height: 1rem;" />
              <Moon v-else style="height: 1rem;" />
            </span>
          </button>
        </div>
      </div>
    </header>

    <!-- Main tabs navigation -->
    <div class="blazepress-secondary-nav">
      <div class="blazepress-secondary-nav-container">
        <a v-for="item in theme.nav" :key="item.text" :href="withBase(item.link)" class="blazepress-nav-tab"
          :class="{ 'active': isActiveNav(item.link) }">
          {{ item.text }}
        </a>
      </div>
    </div>

    <!-- Use the default VitePress layout for the rest of the content -->
    <Layout>
      <template #nav-bar>
        <!-- Empty to override the default navbar -->
      </template>

      <template #nav-screen-content-before>
        <!-- Add any mobile-specific custom content here -->
      </template>
    </Layout>
  </div>
</template>
