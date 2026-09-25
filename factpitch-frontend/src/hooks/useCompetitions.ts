import { useEffect, useState } from 'react';
import { ApiError, getCompetitions } from '../services/apiClient';
import type { Competition } from '../types/api';

interface UseCompetitionsResult {
  competitions: Competition[];
  loading: boolean;
  /** Non-null exactly when the API couldn't be reached — mirrors
   * ui/app.py's api_unreachable flag, which drives disabling the rest of
   * the sidebar. */
  error: string | null;
}

let cache: Competition[] | null = null;

export function useCompetitions(): UseCompetitionsResult {
  const [competitions, setCompetitions] = useState<Competition[]>(cache ?? []);
  const [loading, setLoading] = useState(cache === null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cache !== null) return;

    let cancelled = false;
    setLoading(true);

    getCompetitions()
      .then((data) => {
        if (cancelled) return;
        cache = data;
        setCompetitions(data);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Could not load competitions.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { competitions, loading, error };
}

/** Test-only escape hatch — resets the module-level cache between tests. */
export function __resetCompetitionsCache(): void {
  cache = null;
}
