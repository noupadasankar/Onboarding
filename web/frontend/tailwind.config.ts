import type { Config } from 'tailwindcss';

/** Tailwind is the ONLY styling mechanism — no inline styles anywhere in the app. */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#0f766e',
          fg: '#ffffff',
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
