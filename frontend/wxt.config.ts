import { defineConfig } from "wxt";
import tailwindcss from "@tailwindcss/vite";

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    host_permissions: ["http://127.0.0.1/*"],
  },
  vite: () => ({
    plugins: [tailwindcss()],
  }),
});
