import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        surface: {
          DEFAULT: "#111113",
          hover: "#18181b",
          subtle: "#141416",
        },
        border: {
          DEFAULT: "#27272a",
          subtle: "#1e1e22",
        },
      },
    },
  },
  plugins: [],
};
export default config;
