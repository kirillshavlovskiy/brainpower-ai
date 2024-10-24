FROM node:18.18.0

WORKDIR /app

# Install necessary tools
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV NODE_ENV=development
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true
ENV FAST_REFRESH=true
ENV BROWSER=none

# Install global packages
RUN yarn global add \
    create-react-app \
    typescript \
    serve \
    concurrently

# Create initialization script
RUN echo '#!/bin/bash\n\
\n\
# Initialize new CRA project\n\
if [ ! -f "package.json" ]; then\n\
    echo "Initializing new CRA project..."\n\
    create-react-app . --template typescript\n\
    \n\
    # Create development environment file\n\
    echo "BROWSER=none\n\
FAST_REFRESH=true\n\
SKIP_PREFLIGHT_CHECK=true\n\
TSC_COMPILE_ON_ERROR=true\n\
DISABLE_ESLINT_PLUGIN=true" > .env.development\n\
    \n\
    # Install additional dependencies\n\
    yarn add \
        @emotion/react@^11.11.0 \
        @emotion/styled@^11.11.0 \
        @mui/icons-material@^5.11.16 \
        @mui/material@^5.13.2 \
        lucide-react@^0.263.1 \
        react-icons@^4.2.0 \
        tailwindcss@^3.3.0 \
        @tailwindcss/forms@^0.5.6 \
        @tailwindcss/typography@^0.5.10 \
        @tailwindcss/aspect-ratio@^0.4.2 \
        clsx@^2.0.0 \
        html2canvas@^1.4.1 \
        tailwind-merge@^1.14.0 \
        @testing-library/jest-dom@^5.17.0 \
        @testing-library/react@^12.1.5 \
        @testing-library/user-event@^13.5.0 \
        web-vitals@^2.1.4 \
        react-error-boundary@^4.0.11 \
        postcss@^8.4.31 \
        postcss-cli@^10.1.0 \
        autoprefixer@^10.4.16\n\
    \n\
    # Add dev dependencies\n\
    yarn add -D \
        @typescript-eslint/eslint-plugin@^5.62.0 \
        @typescript-eslint/parser@^5.62.0 \
        eslint@^8.45.0 \
        eslint-plugin-react@^7.32.2 \
        eslint-plugin-react-hooks@^4.6.0 \
        prettier@^2.8.8 \
        prettier-plugin-tailwindcss@^0.4.1\n\
    \n\
    # Initialize Tailwind CSS\n\
    npx tailwindcss init -p\n\
    \n\
    # Configure Tailwind\n\
    echo '\''/** @type {import('\''tailwindcss'\'').Config} */\n\
module.exports = {\n\
    content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],\n\
    darkMode: "class",\n\
    theme: { extend: {} },\n\
    plugins: [\n\
        require("@tailwindcss/forms"),\n\
        require("@tailwindcss/typography"),\n\
        require("@tailwindcss/aspect-ratio")\n\
    ]\n\
}'\'' > tailwind.config.js\n\
    \n\
    # Update index.css with Tailwind imports\n\
    echo "@tailwind base;\n@tailwind components;\n@tailwind utilities;" > src/index.css\n\
    \n\
    # Update package.json scripts\n\
    sed -i '\''s/"start": "react-scripts start"/"start": "BROWSER=none HOST=0.0.0.0 react-scripts start"/g'\'' package.json\n\
    \n\
    # Create components directory\n\
    mkdir -p src/components\n\
fi\n\
\n\
# Start development server\n\
exec yarn start' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 3001

ENTRYPOINT ["/app/entrypoint.sh"]