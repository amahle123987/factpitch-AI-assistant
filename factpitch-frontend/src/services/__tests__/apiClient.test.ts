import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, getCompetitions, getCrest, getHeadlineStats, getTeams, runAnalysis } from '../apiClient';
import type { StreamEvent } from '../../types/api';

function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: async () => data,
  } as Response;
}

/** Builds a fetch Response whose body streams SSE-formatted events,
 * mirroring the real backend's `data: {...}\n\n` framing. */
function streamResponse(events: StreamEvent[], opts?: { splitMidEvent?: boolean }): Response {
  const text = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('');
  const encoder = new TextEncoder();

  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      if (opts?.splitMidEvent) {
        // Simulate a chunk boundary landing mid-event, to prove the
        // buffering logic in runAnalysis handles partial lines correctly.
        const mid = Math.floor(text.length / 2);
        controller.enqueue(encoder.encode(text.slice(0, mid)));
        controller.enqueue(encoder.encode(text.slice(mid)));
      } else {
        controller.enqueue(encoder.encode(text));
      }
      controller.close();
    },
  });

  return { ok: true, status: 200, statusText: 'OK', body } as Response;
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('getCompetitions', () => {
  it('returns parsed json', async () => {
    const fakeData = [{ code: 'PL', name: 'Premier League' }];
    vi.mocked(fetch).mockResolvedValue(jsonResponse(fakeData));

    const result = await getCompetitions();
    expect(result).toEqual(fakeData);
  });

  it('throws ApiError on connection failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('refused'));

    await expect(getCompetitions()).rejects.toThrow(ApiError);
    await expect(getCompetitions()).rejects.toThrow(/Could not reach the API/);
  });
});

describe('getTeams', () => {
  it('passes the competition param', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse([]));
    await getTeams('PL');

    const calledUrl = vi.mocked(fetch).mock.calls[0][0] as URL;
    expect(calledUrl.toString()).toContain('competition=PL');
  });

  it('sends no competition param when omitted', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse([]));
    await getTeams();

    const calledUrl = vi.mocked(fetch).mock.calls[0][0] as URL;
    expect(calledUrl.toString()).not.toContain('competition=');
  });

  it('throws ApiError on server error', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 500));
    await expect(getTeams('PL')).rejects.toThrow(ApiError);
  });
});

describe('getCrest', () => {
  it('returns the crest url', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ crest_url: 'https://x.com/c.png' }));
    expect(await getCrest(57)).toBe('https://x.com/c.png');
  });

  it('never throws on failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('refused'));
    await expect(getCrest(57)).resolves.toBeNull();
  });
});

describe('getHeadlineStats', () => {
  it('returns stats when available', async () => {
    const fakeData = { available: true, position: 3, goal_difference: 17 };
    vi.mocked(fetch).mockResolvedValue(jsonResponse(fakeData));
    expect(await getHeadlineStats(57, 'PL')).toEqual(fakeData);
  });

  it('returns null when unavailable', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ available: false, position: null }));
    expect(await getHeadlineStats(57, 'EC')).toBeNull();
  });

  it('never throws on connection failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('refused'));
    await expect(getHeadlineStats(57, 'PL')).resolves.toBeNull();
  });
});

describe('runAnalysis', () => {
  const baseParams = { teamId: 57, teamName: 'Arsenal FC', query: 'test query', windowDays: 60 };

  it('calls onProgress for each stage and resolves with the result', async () => {
    const events: StreamEvent[] = [
      { type: 'progress', stage: 'Researching: test' },
      { type: 'progress', stage: 'Validating the narrative' },
      { type: 'result', result: { verdict: 'test verdict', news: {} as never, stats: null } },
    ];
    vi.mocked(fetch).mockResolvedValue(streamResponse(events));

    const seenStages: string[] = [];
    const result = await runAnalysis({ ...baseParams, onProgress: (s) => seenStages.push(s) });

    expect(seenStages).toEqual(['Researching: test', 'Validating the narrative']);
    expect(result.verdict).toBe('test verdict');
  });

  it('works without an onProgress callback', async () => {
    const events: StreamEvent[] = [
      { type: 'progress', stage: 'Researching' },
      { type: 'result', result: { verdict: 'v', news: {} as never, stats: null } },
    ];
    vi.mocked(fetch).mockResolvedValue(streamResponse(events));

    const result = await runAnalysis(baseParams);
    expect(result.verdict).toBe('v');
  });

  it('throws ApiError when an error event arrives', async () => {
    const events: StreamEvent[] = [
      { type: 'progress', stage: 'Researching' },
      { type: 'error', detail: 'pipeline exploded' },
    ];
    vi.mocked(fetch).mockResolvedValue(streamResponse(events));

    await expect(runAnalysis(baseParams)).rejects.toThrow(/pipeline exploded/);
  });

  it('throws ApiError on connection failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('refused'));
    await expect(runAnalysis(baseParams)).rejects.toThrow(/Could not reach the API/);
  });

  it('throws ApiError if the stream ends without a result', async () => {
    const events: StreamEvent[] = [{ type: 'progress', stage: 'Researching' }];
    vi.mocked(fetch).mockResolvedValue(streamResponse(events));

    await expect(runAnalysis(baseParams)).rejects.toThrow(/ended without a result/);
  });

  it('correctly reassembles an event split across a chunk boundary', async () => {
    const events: StreamEvent[] = [
      { type: 'progress', stage: 'Researching' },
      { type: 'result', result: { verdict: 'split-chunk verdict', news: {} as never, stats: null } },
    ];
    vi.mocked(fetch).mockResolvedValue(streamResponse(events, { splitMidEvent: true }));

    const result = await runAnalysis(baseParams);
    expect(result.verdict).toBe('split-chunk verdict');
  });
});
