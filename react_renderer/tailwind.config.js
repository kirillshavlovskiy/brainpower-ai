/** @type {import("tailwindcss").Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      // Colors for themes and components
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      // Border radius
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      // Clock-specific spacing
      spacing: {
        '0.5': '0.125rem',    // 2px
        '1': '0.25rem',       // 4px
        '1.5': '0.375rem',    // 6px
        '2': '0.5rem',        // 8px
        '3': '0.75rem',       // 12px
        '4': '1rem',          // 16px
        '20': '5rem',         // 80px
        '28': '7rem',         // 112px
        '32': '8rem',         // 128px
        '64': '16rem',        // 256px - clock size
      },
      // Width utilities
      width: {
        '0.5': '0.125rem',    // thin hand
        '1': '0.25rem',       // medium hand
        '1.5': '0.375rem',    // thick hand
        '2': '0.5rem',
        '3': '0.75rem',
        '4': '1rem',
        '64': '16rem',        // clock face
      },
      // Height utilities
      height: {
        '3': '0.75rem',
        '20': '5rem',         // hour hand
        '28': '7rem',         // minute hand
        '32': '8rem',         // second hand
        '64': '16rem',        // clock face
      },
      // Animation keyframes
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "fade-in": {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        "fade-out": {
          "0%": { opacity: 1 },
          "100%": { opacity: 0 },
        },
      },
      // Animation utilities
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.2s ease-out",
        "fade-out": "fade-out 0.2s ease-out",
      },
      // Font sizes
      fontSize: {
        'clock': ['4rem', { lineHeight: '1' }],
        'digital': ['6rem', { lineHeight: '1' }],
      },
      // Minimum dimensions
      minHeight: {
        'screen': '100vh',
      },
      // Z-index
      zIndex: {
        'hand': 10,
        'marker': 20,
        'center': 30,
      },
    },
  },
  // Plugins
  plugins: [
    require("tailwindcss-animate"), // For animations
  ],
}