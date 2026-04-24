// @ts-check

const config = {
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./styles/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1A56DB",
        accent: "#7E3AF2",
        success: "#0E9F6E",
        warning: "#C27803",
        danger: "#E02424",
        surface: "#F9FAFB",
      },
    },
  },
  plugins: [],
};

export default config;
