// src/App.js
import React from 'react';
import { useCounter } from './hooks/useCounter';
import './App.css';

const App = () => {
  const { count, increment, reset } = useCounter(0);

  return (
    <main className="container">
      <h1 className="heading">Hello, World!</h1>
      <p>Welcome to your React playground.</p>
      <p>You've clicked the button {count} times.</p>
      <div>
        <button 
          onClick={increment}
          className="button"
          aria-label="Increment counter"
        >
          Click me
        </button>
        <button 
          onClick={reset}
          className="button button-reset"
          aria-label="Reset counter"
        >
          Reset
        </button>
      </div>
    </main>
  );
};

export default App;