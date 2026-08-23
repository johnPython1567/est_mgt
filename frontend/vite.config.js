import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
    plugins: [
        tailwindcss(),
    ],

    build: {
        outDir: "../static/dist",
        emptyOutDir: true,

        manifest: true,

        rollupOptions: {
            input: {
                css: "./src/css/input.css",
                js: "./src/js/main.js",
            },
        },
    },
});