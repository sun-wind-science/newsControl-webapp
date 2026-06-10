import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F7F5F0",
        panel: "#EEECE7",
        ink: "#1A1A18",
        muted: "#6B6860",
        line: "#D8D5CE",
        accent: "#C4622D",
        success: "#4A7C59",
        danger: "#B0390E",
        cold: "#A09D96"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
        serif: ["Georgia", "Times New Roman", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular"]
      },
      boxShadow: {
        soft: "0 10px 30px rgba(26, 26, 24, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
