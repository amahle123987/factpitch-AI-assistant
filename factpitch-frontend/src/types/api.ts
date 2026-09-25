// Mirrors api/schemas.py and agents/schemas.py. Kept in one file since the
// backend keeps its equivalents together too (api/schemas.py imports
// NewsResearch from agents/schemas.py).

export interface Competition {
  code: string;
  name: string;
}

export interface Team {
  id: number;
  name: string;
  competition: string;
}

export interface KeyEvent {
  date: string;
  headline: string;
  detail: string;
}

export interface PrimaryEvent {
  date: string;
  headline: string;
  reason: string;
}

export interface NewsResearch {
  query: string;
  key_events: KeyEvent[];
  primary_event: PrimaryEvent | null;
  summary: string;
}

export interface RollingPoint {
  date: string;
  opponent: string;
  result: 'W' | 'D' | 'L';
  rolling_win_rate: number;
}

/** Matches agents/data_analyst.py's _summarize() output. Fields beyond
 * `matches` are absent when there are zero matches in that half of the
 * split, and the opponent-strength fields are absent whenever standings
 * data wasn't available for that competition. */
export interface SplitStats {
  matches: number;
  wins?: number;
  draws?: number;
  losses?: number;
  win_rate?: number;
  avg_goals_for?: number;
  avg_goals_against?: number;
  avg_opponent_position?: number;
  opponent_position_coverage?: string;
  opponent_position_note?: string;
}

export interface AnalysisStats {
  pivot_date: string;
  pre: SplitStats;
  post: SplitStats;
  series: RollingPoint[];
  chart_path: string | null;
  error?: string;
}

export interface AnalyzeResult {
  news: NewsResearch;
  stats: AnalysisStats | null;
  verdict: string;
}

export interface HeadlineStats {
  available: boolean;
  position: number | null;
  played: number | null;
  won: number | null;
  draw: number | null;
  lost: number | null;
  goals_for: number | null;
  goals_against: number | null;
  goal_difference: number | null;
  points: number | null;
}

/** A team chosen by the user, along with which competition it was found
 * under (needed for headline-stats lookups, which are competition-scoped). */
export interface TeamSelection {
  teamId: number;
  teamName: string;
  competition: string;
}

export type StreamEvent =
  | { type: 'progress'; stage: string }
  | { type: 'result'; result: AnalyzeResult }
  | { type: 'error'; detail: string };
