import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl =
    env.VITE_DEV_BACKEND_URL || "http://127.0.0.1:7777";
  const proxy = {
    "/backend": {
      target: backendUrl,
      changeOrigin: true,
    },
  };

  return {
    plugins: [vue()],
    server: {
      proxy,
    },
    preview: {
      proxy,
    },
  };
});
