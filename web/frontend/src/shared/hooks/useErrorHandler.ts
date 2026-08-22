import { useState } from 'react';

/**
 * Hook for catching async errors (promises, event handlers) in function components.
 * Usage: const captureError = useErrorHandler(); then wrap async functions.
 */
export function useErrorHandler() {
  const [error, setError] = useState<Error | null>(null);

  const captureError = (err: Error) => {
    setError(err);
    console.error('Async error captured:', err);
  };

  const clearError = () => setError(null);

  return { error, captureError, clearError };
}

/**
 * Wrapper to make any async function error-safe.
 */
export function withErrorCapture<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  onError: (err: Error) => void,
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args);
    } catch (err) {
      onError(err instanceof Error ? err : new Error(String(err)));
      throw err;
    }
  }) as T;
}