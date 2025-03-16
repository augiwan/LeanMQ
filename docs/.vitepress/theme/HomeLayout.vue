<script setup lang="ts">
import VPHomeHero from 'vitepress/dist/client/theme-default/components/VPHomeHero.vue'
import VPHomeFeatures from 'vitepress/dist/client/theme-default/components/VPHomeFeatures.vue'
import VPHomeContent from 'vitepress/dist/client/theme-default/components/VPHomeContent.vue'
import { useData } from 'vitepress'

const { frontmatter, theme } = useData()
</script>

<template>
    <div class="VPHome" :class="{
        'external-link-icon-enabled': theme.externalLinkIcon
    }">
        <div class="home-layout">
            <!-- Left column: Hero and Features -->
            <div class="left-column">
                <!-- Hero content -->
                <div class="hero-container">
                    <slot name="home-hero-before" />
                    <VPHomeHero>
                        <template #home-hero-info-before>
                            <slot name="home-hero-info-before" />
                        </template>
                        <template #home-hero-info>
                            <slot name="home-hero-info" />
                        </template>
                        <template #home-hero-info-after>
                            <slot name="home-hero-info-after" />
                        </template>
                        <template #home-hero-actions-after>
                            <slot name="home-hero-actions-after" />
                        </template>
                        <template #home-hero-image>
                            <slot name="home-hero-image" />
                        </template>
                    </VPHomeHero>
                    <slot name="home-hero-after" />
                </div>

                <!-- Features below hero -->
                <div class="features-container">
                    <slot name="home-features-before" />
                    <VPHomeFeatures />
                    <slot name="home-features-after" />
                </div>
            </div>

            <!-- Right column: Markdown content -->
            <div class="right-column">
                <VPHomeContent v-if="frontmatter.markdownStyles !== false">
                    <Content />
                </VPHomeContent>
                <Content v-else />
            </div>
        </div>
    </div>
</template>

<style scoped>
.VPHome {
    margin-bottom: 96px;
}

.VPHero.VPHomeHero,
.VPFeatures.VPHomeFeatures {
    padding-left: 0;
    padding-right: 0;
}

.home-layout {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    max-width: 1424px;
    margin: 0 auto;
    padding: 0 24px;
}

.left-column,
.right-column {
    width: 100%;
}

/* Features styling */
.features-container {
    margin-top: 2rem;
}

.features-container :deep(.VPFeatures) {
    display: block !important;
}

.features-container :deep(.VPFeatures .items) {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
}

.features-container :deep(.VPFeatures .item) {
    width: calc(50% - 8px) !important;
    max-width: calc(50% - 8px) !important;
    margin: 0 !important;
}

.features-container :deep(.VPFeatures .VPFeature) {
    height: 100%;
}

/* Responsive layout */
@media (min-width: 960px) {
    .home-layout {
        flex-direction: row;
        align-items: flex-start;
    }

    .left-column {
        width: 50%;
        padding-right: 2rem;
    }

    .right-column {
        width: 50%;
        padding-top: 64px;
        /* Align with hero content */
    }
}

/* On small screens, make tiles full width */
@media (max-width: 1280px) {
    .features-container :deep(.VPFeatures .item) {
        width: 100% !important;
        max-width: 100% !important;
    }
}

@media (min-width: 768px) {
    .VPHome {
        margin-bottom: 128px;
    }
}
</style>