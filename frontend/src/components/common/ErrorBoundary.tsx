import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-lg border border-neutral-200 p-8 shadow-sm text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-semibold text-neutral-900 mb-2">Something went wrong</h1>
            <p className="text-sm text-neutral-500 mb-6">
              An unexpected client-side error occurred: {this.state.error?.message || 'Unknown error'}
            </p>
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 w-full"
            >
              <RefreshCcw className="w-4 h-4 mr-2" />
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
