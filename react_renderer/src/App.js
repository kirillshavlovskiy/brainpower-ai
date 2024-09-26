import React, { useState, useEffect, Suspense } from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';

const DynamicComponent = () => {
  const [Component, setComponent] = useState(null);
  const [error, setError] = useState(null);
  const { userId, fileName } = useParams();

  useEffect(() => {
    const loadComponent = async () => {
      try {
        console.log(`Attempting to load component for user ${userId} and file ${fileName}`);
        // Use a relative path without the file extension
        const module = await import('./component');
        console.log('Module loaded:', module);
        if (module.default) {
          setComponent(() => module.default);
        } else {
          throw new Error('No default export found in component.js');
        }
      } catch (error) {
        console.error('Error loading dynamic component:', error);
        setError(`Failed to load component: ${error.message}`);
      }
    };

    loadComponent();
    // Set up an interval to check for changes
    const intervalId = setInterval(loadComponent, 5000);

    return () => clearInterval(intervalId);
  }, [userId, fileName]);

  if (error) {
    return <div>Error: {error}</div>;
  }

  return Component ? <Component /> : <div>Loading component for user {userId}... Please wait.</div>;
};

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <h1>Something went wrong: {this.state.error.toString()}</h1>;
    }
    return this.props.children;
  }
}
const theme = createTheme();

function App() {
  return (

    <ThemeProvider theme={theme}>
      <ErrorBoundary>
        <Suspense fallback={<div>Loading...</div>}>
          <DynamicComponent />
        </Suspense>
      </ErrorBoundary>
      </ThemeProvider>

  );
}

export default App;