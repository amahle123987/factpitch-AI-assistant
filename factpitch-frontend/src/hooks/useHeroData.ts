import { useEffect, useState } from 'react';
import { getCrest, getHeadlineStats } from '../services/apiClient';
import type { HeadlineStats } from '../types/api';
import type { TeamSelection } from '../types/api';

interface HeroData {
  crestUrl: string | null;
  headline: HeadlineStats | null;
}

export function useHeroData(selection: TeamSelection | null): HeroData {
  const [crestUrl, setCrestUrl] = useState<string | null>(null);
  const [headline, setHeadline] = useState<HeadlineStats | null>(null);

  useEffect(() => {
    if (!selection) {
      setCrestUrl(null);
      setHeadline(null);
      return;
    }

    let cancelled = false;

    getCrest(selection.teamId).then((url) => {
      if (!cancelled) setCrestUrl(url);
    });
    getHeadlineStats(selection.teamId, selection.competition).then((stats) => {
      if (!cancelled) setHeadline(stats);
    });

    return () => {
      cancelled = true;
    };
  }, [selection]);

  return { crestUrl, headline };
}
