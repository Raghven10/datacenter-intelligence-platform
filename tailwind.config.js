module.exports = {
    content: [
        "./app/templates/**/*.html",
        "./app/static/**/*.js",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                primary: {
                    50: '#f5f3ff',
                    100: '#ede9fe',
                    200: '#ddd6fe',
                    300: '#c4b5fd',
                    400: '#a78bfa',
                    500: '#8b5cf6',
                    600: '#7c3aed',
                    700: '#6d28d9',
                    800: '#5b21b6',
                    900: '#4c1d95',
                },
                accent: {
                    emerald: '#10b981',
                    rose: '#f43f5e',
                    amber: '#f59e0b',
                    sky: '#0ea5e9'
                }
            }
        }
    },
    plugins: [],
}
