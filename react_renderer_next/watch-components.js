const chokidar = require('chokidar');
const WebSocket = require('ws');
const path = require('path');

// Create WebSocket server
const wss = new WebSocket.Server({ port: 8000 });

// Watch dynamic components directory
const watcher = chokidar.watch([
  './components/dynamic',
  './styles/dynamic'
], {
  persistent: true,
  ignoreInitial: true,
  usePolling: true,
  interval: 1000
});

// Handle file changes
watcher.on('all', (event, filePath) => {
  const changeData = {
    event,
    path: path.relative(process.cwd(), filePath),
    timestamp: new Date().toISOString()
  };

  // Broadcast to all connected clients
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(changeData));
    }
  });

  console.log(`File ${event}: ${filePath}`);
});

// WebSocket connection handling
wss.on('connection', ws => {
  console.log('Client connected');

  ws.on('close', () => {
    console.log('Client disconnected');
  });
});

console.log('File watcher and WebSocket server started');