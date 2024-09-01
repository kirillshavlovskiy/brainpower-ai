// render.js
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const Component = require('./dist/component').default;

const html = ReactDOMServer.renderToString(React.createElement(Component));
console.log(html);