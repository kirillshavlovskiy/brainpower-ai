import React from 'react';
import ReactDOMServer from 'react-dom/server';
import babel from '@babel/core';
import fs from 'fs';
import path from 'path';

console.log('run_react.js is located at:', __filename);
console.log('Current working directory:', process.cwd());
console.log('Contents of current directory:', fs.readdirSync('.'));

try {
    const componentPath = path.join('/app', 'component.js');
    console.log('Reading component file from:', componentPath);
    const componentCode = fs.readFileSync(componentPath, 'utf8');

    console.log('Transpiling code');
    const transpiledCode = babel.transformSync(componentCode, {
        presets: ['@babel/preset-react']
    }).code;

    console.log('Evaluating transpiled code');
    eval(transpiledCode);

    const componentName = Object.keys(global).find(key =>
        typeof global[key] === 'function' &&
        /^[A-Z]/.test(key) &&
        /Component$/.test(key)
    );

    if (!componentName) {
        throw new Error('React component not found after evaluation');
    }

    console.log(`Found component: ${componentName}`);
    const Component = global[componentName];

    console.log('Rendering component to string');
    const html = ReactDOMServer.renderToString(React.createElement(Component));

    const fullHtml = `
    <!DOCTYPE html>
    <html>
      <head>
        <title>React Component</title>
      </head>
      <body>
        <div id="root">${html}</div>
        <script src="https://unpkg.com/react@17/umd/react.production.min.js"></script>
        <script src="https://unpkg.com/react-dom@17/umd/react-dom.production.min.js"></script>
        <script>
          ${transpiledCode}
          ReactDOM.hydrate(React.createElement(${componentName}), document.getElementById('root'));
        </script>
      </body>
    </html>
    `;

    const outputPath = path.join('/app', 'output.html');
    fs.writeFileSync(outputPath, fullHtml);
    console.log('HTML generated successfully');
    console.log('Output file path:', outputPath);
} catch (error) {
    console.error('Error occurred:', error);
    process.exit(1);
}