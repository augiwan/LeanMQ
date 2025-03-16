import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "LeanMQ",
  description:
    "Replace your internal webhooks with a reliable, performant, and scalable MQ with a fantastic DX.",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "Home", link: "/" },
      // { text: "Guide", link: "/guide/intro" },
    ],

    sidebar: [
      // {
      //   text: "Guide",
      //   items: [
      //     { text: "Markdown Examples", link: "/markdown-examples" },
      //     { text: "Runtime API Examples", link: "/api-examples" },
      //   ],
      // },
    ],

    topNav: [{ text: "GitHub", link: "https://github.com/augiwan/LeanMQ" }],

    // socialLinks: [
    //   { icon: "github", link: "https://github.com/augiwan/LeanMQ" },
    // ],

    search: {
      provider: "local",
      options: {
        detailedView: true,
      },
    },
  },
});
