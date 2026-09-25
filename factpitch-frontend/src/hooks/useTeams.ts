import { useEffect, useState } from 'react';
import { ApiError, getTeams } from '../services/apiClient';
import type { Team } from '../types/api';

interface UseTeamsResult {
  teams: Team[];
  loading: boolean;
  error: string | null;
}

const cache = new Map<string, Team[]>();

function cacheKey(competition: string | null): string {
  return competition ?? '__any__';
}

/** Fetches the team list for a competition (or all competitions when null,
 * matching "Any competition" in the UI), caching per competition so
 * switching back and forth doesn't refetch. */
export function useTeams(competition: string | null): UseTeamsResult {
  const key = cacheKey(competition);
  const [teams, setTeams] = useState<Team[]>(cache.get(key) ?? []);
  const [loading, setLoading] = useState(!cache.has(key));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cache.has(key)) {
      setTeams(cache.get(key)!);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    getTeams(competition)
      .then((data) => {
        if (cancelled) return;
        cache.set(key, data);
        setTeams(data);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Could not load teams.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return { teams, loading, error };
}

/** Test-only escape hatch — resets the module-level cache between tests. */
export function __resetTeamsCache(): void {
  cache.clear();
}
