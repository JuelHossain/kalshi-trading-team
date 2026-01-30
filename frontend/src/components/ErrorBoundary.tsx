import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-black flex items-center justify-center p-6 bg-grid-pattern">
          <div className="glass-panel w-full max-w-lg p-8 rounded-2xl border-red-500/20 shadow-[0_0_50px_rgba(239,68,68,0.1)]">
            {/* Error Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-400 to-red-700 flex items-center justify-center shadow-[0_0_30px_rgba(239,68,68,0.3)]">
                <span className="text-white font-black font-tech text-3xl">!</span>
              </div>
            </div>

            {/* Title */}
            <h2 className="text-2xl font-tech font-bold text-center mb-2 text-red-400">
              SYSTEM ERROR
            </h2>
            <p className="text-gray-500 text-center text-[10px] mb-6 font-mono tracking-[0.2em] uppercase">
              An unexpected error occurred
            </p>

            {/* Error Details */}
            <div className="space-y-4 mb-6">
              {this.state.error && (
                <div className="p-4 bg-red-500/5 rounded-xl border border-red-500/20">
                  <p className="text-[10px] font-mono text-red-400/70 mb-1 uppercase tracking-wider">
                    Error Message
                  </p>
                  <p className="text-sm text-red-300 font-mono">{this.state.error.message}</p>
                </div>
              )}

              {this.state.errorInfo && (
                <details className="group">
                  <summary className="text-[10px] font-mono text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-400 transition-colors flex items-center gap-2">
                    <span className="group-open:rotate-90 transition-transform">▶</span>
                    Stack Trace
                  </summary>
                  <pre className="mt-2 p-4 bg-black/40 rounded-lg text-[9px] font-mono text-gray-500 overflow-auto max-h-40 no-scrollbar">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={this.handleReload}
                className="flex-1 py-3 px-4 bg-red-600 hover:bg-red-500 text-white rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                Reload Application
              </button>
              <button
                onClick={this.handleReset}
                className="flex-1 py-3 px-4 bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                Try Again
              </button>
            </div>

            {/* Footer */}
            <p className="text-[8px] text-gray-700 text-center mt-6 font-mono uppercase tracking-widest">
              If the problem persists, check the console for more details
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
