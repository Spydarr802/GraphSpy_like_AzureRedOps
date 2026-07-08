
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#121212',
        panel: '#1e1e2e',
        accent: '#3498db',
        success: '#2ecc71',
        danger: '#e74c3c',
        purple: '#9b59b6',
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
      boxShadow: {
        glow: '0 0 20px rgba(52, 152, 219, 0.4)',
        'glow-success': '0 0 20px rgba(46, 204, 113, 0.4)',
        'glow-purple': '0 0 20px rgba(155, 89, 182, 0.4)',
        'glow-danger': '0 0 20px rgba(231, 76, 60, 0.4)',
      },
    },
  },
  plugins: [],
}

