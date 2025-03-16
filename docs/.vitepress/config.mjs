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
      { text: "Reference", link: "/reference/core" },
      { text: "Examples", link: "/examples/webhook-services" },
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
        {
          text: "Advanced",
          items: [
            {
              text: "Queue Management",
              link: "/guide/advanced/queue-management",
            },
            {
              text: "Atomic Transactions",
              link: "/guide/advanced/transactions",
            },
            {
              text: "Error Handling",
              link: "/guide/advanced/error-handling",
            },
            {
              text: "Scaling",
              link: "/guide/advanced/scaling",
            },
            {
              text: "Production",
              link: "/guide/advanced/production",
            },
          ],
        },
      ],

      "/reference/": [
        {
          text: "Reference",
          items: [
            { text: "Core", link: "/reference/core" },
            { text: "Webhook", link: "/reference/webhook" },
            { text: "Queue", link: "/reference/queue" },
            { text: "Message", link: "/reference/message" },
            { text: "Transaction", link: "/reference/transaction" },
            { text: "Exceptions", link: "/reference/exceptions" },
          ],
        },
      ],
      "/examples/": [
        {
          text: "Examples",
          items: [
            { text: "Webhook Services", link: "/examples/webhook-services" },
            { text: "Basic Messaging", link: "/examples/basic-messaging" },
          ],
        },
        {
          text: "Full Microservice",
          items: [
            {
              text: "Defining the Event System",
              link: "/examples/microservice/defining-the-event-system",
            },
            {
              text: "Event Bus Implementation",
              link: "/examples/microservice/event-bus-implementation",
            },
            {
              text: "Microservice Implementation",
              link: "/examples/microservice/microservice-implementation",
            },
            {
              text: "Implementing Specific Microservices",
              link: "/examples/microservice/implementing-specific-microservices",
            },
            {
              text: "Implementing Shipping and Notification Services",
              link: "/examples/microservice/implementing-shipping-and-notification-services",
            },
            {
              text: "Running the Event-Driven System",
              link: "/examples/microservice/running-the-event-driven-system",
            },
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
