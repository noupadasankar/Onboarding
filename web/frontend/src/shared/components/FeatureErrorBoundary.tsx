import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface FeatureErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  featureName: string;
  onReset?: () => void;
}

interface FeatureErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Feature-level error boundary that catches render errors in a specific
 * feature area (e.g., Chat, Documents, Dashboard) and displays a recovery UI
 * without crashing the entire app.
 */
export class FeatureErrorBoundary extends Component<
  FeatureErrorBoundaryProps,
  FeatureErrorBoundaryState
> {
  constructor(props: FeatureErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): FeatureErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error(`[FeatureErrorBoundary:${this.props.featureName}]`, error, errorInfo);
    // Could send to error tracking service (Sentry, etc.)
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[300px] items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">
              Something went wrong in {this.props.featureName}
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              This section couldn't load. Your other features are still working.
            </p>
            <div className="flex gap-2 justify-center">
              <Button onClick={this.handleReset} variant="outline" className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
              <Button onClick={() => window.location.reload()} variant="ghost">
                Reload page
              </Button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-xs text-slate-400">
                  Error details (development)
                </summary>
                <pre className="mt-2 overflow-auto rounded bg-slate-100 p-2 text-xs text-slate-600">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
