// import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

// https://vitepress.dev/reference/site-config
export default withMermaid({
  title: "LeanMQ",
  description:
    "Replace your internal webhooks with a reliable, performant, and scalable MQ with a fantastic DX.",

  cleanUrls: true,
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "Home", link: "/" },
      { text: "Guide", link: "/guide/intro" },
    ],

    sidebar: {
      "/guide/": [
        {
          text: "Hello LeanMQ",
          items: [
            { text: "Intro", link: "/guide/intro" },
            { text: "Getting Started", link: "/guide/getting-started" },
            { text: "Basic Overview", link: "/guide/basic-overview" },
            { text: "Webhooks", link: "/guide/webhook-pattern" },
            { text: "Why LeanMQ?", link: "/guide/why-leanmq" },
          ],
        },
      ],
    },

    // topNav: [{ text: "GitHub", link: "https://github.com/augiwan/LeanMQ" }],

    socialLinks: [
      { icon: "github", link: "https://github.com/augiwan/LeanMQ" },
    ],

    search: {
      provider: "local",
      options: {
        detailedView: true,
      },
    },

    mermaid: {
      // refer https://mermaid.js.org/config/setup/modules/mermaidAPI.html#mermaidapi-configuration-defaults for options
    },

    // optionally set additional config for plugin itself with MermaidPluginConfig
    // mermaidPlugin: {
    //   class: "mermaid my-class", // set additional css classes for parent container
    // },
  },
});
