import { defineConfig } from "wxt";
import tailwindcss from "@tailwindcss/vite";
import { loadEnv } from "vite";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: ({ mode }) => {
    const env = loadEnv(mode, process.cwd(), "WXT_");
    const hosts = ["http://127.0.0.1/*", "http://localhost/*"];
    for (const value of [env.WXT_API_BASE_URL, env.WXT_CLERK_FRONTEND_API]) {
      if (value) {
        const url = new URL(value);
        hosts.push(`${url.protocol}//${url.hostname}/*`);
      }
    }
    return {
      permissions: ["cookies", "storage"],
      host_permissions: [...new Set(hosts)],
      ...(env.WXT_EXTENSION_PUBLIC_KEY ? { key: env.WXT_EXTENSION_PUBLIC_KEY } : {}),
    };
  },
  vite: () => ({ plugins: [tailwindcss()] }),
});
