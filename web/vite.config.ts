import { defineConfig, loadEnv } from "vite";

/** GitHub Pages project site: set VITE_BASE=/repository-name/ in CI. Apex/custom domain: VITE_BASE=/ */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const base = env.VITE_BASE || "/";
  return {
    root: ".",
    base,
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
    },
    build: {
      outDir: "dist",
      assetsDir: "assets",
    },
  };
});
