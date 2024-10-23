import dynamic from 'next/dynamic'
import { Suspense } from 'react'
import React from 'react'

const DynamicComponent = dynamic(
  () => import('../components/DynamicComponent'),
  {
    loading: () => <div>Loading component...</div>,
    ssr: false
  }
)

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

export default function Home() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<div>Loading...</div>}>
        <DynamicComponent />
      </Suspense>
    </ErrorBoundary>
  );
}