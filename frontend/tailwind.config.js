/** Colours come from the Dr. Feysel clinic flyer: leaf green, lime, royal blue and navy ink. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        leaf: { DEFAULT: '#36902A', dark: '#2A7421', tint: '#EEF7EC' },
        lime: { DEFAULT: '#7CC242', soft: '#B8E08A' },
        royal: '#0A4FA8',
        sky: { DEFAULT: '#2C9AD1', tint: '#EAF4FD' },
        ink: { DEFAULT: '#0D2D5A', deep: '#0A2A55' },
        muted: '#56687F',
        line: '#DFE9F3',
        canvas: '#F3F8FC',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        script: ['"Kaushan Script"', 'cursive'],
      },
      backgroundImage: {
        'hero-blue': 'linear-gradient(135deg,#0a2a55 0%,#0a4a8c 55%,#1367a5 100%)',
      },
      boxShadow: {
        lift: '0 20px 50px rgba(13,45,90,.15)',
        pill: '0 14px 40px rgba(5,25,55,.25)',
      },
    },
  },
  plugins: [],
}
