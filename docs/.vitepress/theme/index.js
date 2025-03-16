import DefaultTheme from "vitepress/theme";

import "./styles/main.css";
import Layout from "./Layout.vue";
import HomeLayout from "./HomeLayout.vue";

export default {
  ...DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    // Register custom components
    app.component("CustomHome", HomeLayout);
  },
};
