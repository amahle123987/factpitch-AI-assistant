/**
 * HTTP client for the FastAPI backend (api/main.py). Mirrors
 * ui/api_client.py's interface (same functions, same behavior) so the two
 * frontends stay easy to compare — the one real difference is
 * `runAnalysis`'s SSE consumption, which uses fetch + ReadableStream since
 * the browser has no equivalent of Python's `requests.iter_lines()`.
 */

import type { AnalyzeResult, Competition, HeadlineStats, StreamEvent, Team } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {}

async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }

  let response: Response;
  try {
    response = await fetch(url);
  } catch (err) {
    throw new ApiError(`Could not reach the API at ${API_BASE_URL}: ${(err as Error).message}`);
  }

  if (!response.ok) {
    throw new ApiError(`Could not reach the API at ${API_BASE_URL}: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export async function getCompetitions(): Promise<Competition[]> {
  return getJson<Competition[]>('/competitions');
}

export async function getTeams(competition?: string | null): Promise<Team[]> {
  return getJson<Team[]>('/teams', competition ? { competition } : undefined);
}

/** Never throws — a missing crest shouldn't block the page. */
export async function getCrest(teamId: number): Promise<string | null> {
  try {
    const data = await getJson<{ crest_url: string | null }>(`/teams/${teamId}/crest`);
    return data.crest_url;
  } catch {
    return null;
  }
}

/** Never throws — headline stats are supplementary hero context, not
 * something that should block the page. Returns null both when the
 * backend says the data isn't available (e.g. a cup competition) and
 * when the request itself fails. */
export async function getHeadlineStats(teamId: number, competition: string): Promise<HeadlineStats | null> {
  try {
    const data = await getJson<HeadlineStats>(`/teams/${teamId}/headline`, { competition });
    return data.available ? data : null;
  } catch {
    return null;
  }
}

interface RunAnalysisParams {
  teamId: number;
  teamName: string;
  query: string;
  windowDays: number;
  onProgress?: (stage: string) => void;
  /** Optional AbortSignal so a caller (e.g. a React effect cleanup) can
   * cancel an in-flight analysis — useful if the user navigates away or
   * changes team mid-request. Not part of the Python client, since that's
   * a synchronous CLI/Streamlit context without an equivalent concern. */
  signal?: AbortSignal;
}

/**
 * Calls the streaming POST /analyze/stream endpoint, invoking onProgress
 * for each stage as it arrives, and resolves with the final result once
 * the stream completes. Throws ApiError if the backend can't be reached,
 * the pipeline itself fails, or the stream ends without ever sending a
 * result.
 */
export async function runAnalysis({
  teamId,
  teamName,
  query,
  windowDays,
  onProgress,
  signal,
}: RunAnalysisParams): Promise<AnalyzeResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/analyze/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        team_id: teamId,
        team_name: teamName,
        query,
        window_days: windowDays,
      }),
      signal,
    });
  } catch (err) {
    throw new ApiError(`Could not reach the API at ${API_BASE_URL}: ${(err as Error).message}`);
  }

  if (!response.ok || !response.body) {
    throw new ApiError(`Could not reach the API at ${API_BASE_URL}: ${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line; a chunk boundary can land
    // mid-event, so only process complete lines and keep any trailing
    // partial line in the buffer for the next read.
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || !line.startsWith('data: ')) continue;

      const event = JSON.parse(line.slice('data: '.length)) as StreamEvent;

      if (event.type === 'progress') {
        onProgress?.(event.stage);
      } else if (event.type === 'result') {
        return event.result;
      } else if (event.type === 'error') {
        throw new ApiError(`Analysis failed: ${event.detail}`);
      }
    }
  }

  throw new ApiError('Stream ended without a result — the backend may have crashed mid-request.');
}
