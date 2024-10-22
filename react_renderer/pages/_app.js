// pages/_app.js
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useEffect, useState } from 'react';

// Create theme outside component to prevent recreation on each render
const theme = createTheme();

function MyApp({ Component, pageProps }) {
  const [mounted, setMounted] = useState(false);

  // Handle client-side mounting
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <ThemeProvider theme={theme}>
      <Component {...pageProps} />
    </ThemeProvider>
  );
}

export default MyApp;