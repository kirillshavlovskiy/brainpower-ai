import React, { useState } from 'react';

const App = () => {
  const [count, setCount] = useState(0);

  return (
<div style={{
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100vh',
  fontFamily: 'Arial, sans-serif',
  backgroundColor: '#f0f0f0'
}}>
  <h1 style={{ color: '#333' }}>Hello, World!</h1>
  <p>Welcome to your React playground.</p>
  <p>You've clicked the button {count} times.</p>
  <button 
    onClick={() => setCount(count + 1)}
    style={{
      padding: '10px 20px',
      fontSize: '16px',
      backgroundColor: '#007bff',
      color: 'white',
      border: 'none',
      borderRadius: '5px',
      cursor: 'pointer'
    }}
  >
    Click me
  </button>
</div>
  );
};

export default App;