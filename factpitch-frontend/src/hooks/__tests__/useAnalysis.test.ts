import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useAnalysis } from '../useAnalysis';
import * as apiClient from '../../services/apiClient';

const SELECTION = { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' };
const FAKE_RESULT = {
  news: { query: 'q', key_events: [], primary_event: null, summary: 's' },
  stats: null,
  verdict: 'test verdict',
};

describe('useAnalysis', () => {
  it('starts idle', () => {
    const { result } = renderHook(() => useAnalysis());
    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();
  });

  it('transitions running -> done, collecting progress stages along the way', async () => {
    vi.spyOn(apiClient, 'runAnalysis').mockImplementation(async ({ onProgress }) => {
      onProgress?.('Researching: test');
      onProgress?.('Validating the narrative');
      return FAKE_RESULT;
    });

    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.run(SELECTION, 'test query', 60);
    });
    expect(result.current.status).toBe('running');

    await waitFor(() => expect(result.current.status).toBe('done'));
    expect(result.current.progressStages).toEqual(['Researching: test', 'Validating the narrative']);
    expect(result.current.result).toEqual(FAKE_RESULT);
  });

  it('transitions to error and surfaces the message on failure', async () => {
    vi.spyOn(apiClient, 'runAnalysis').mockRejectedValue(new apiClient.ApiError('pipeline exploded'));

    const { result } = renderHook(() => useAnalysis());
    act(() => {
      result.current.run(SELECTION, 'q', 60);
    });

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.errorMessage).toBe('pipeline exploded');
    expect(result.current.result).toBeNull();
  });

  it('a stale run does not overwrite state from a newer run', async () => {
    let resolveFirst!: (value: typeof FAKE_RESULT) => void;
    const firstCall = new Promise<typeof FAKE_RESULT>((resolve) => {
      resolveFirst = resolve;
    });

    vi.spyOn(apiClient, 'runAnalysis')
      .mockImplementationOnce(() => firstCall)
      .mockImplementationOnce(async () => ({ ...FAKE_RESULT, verdict: 'second run verdict' }));

    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.run(SELECTION, 'first query', 60);
    });
    act(() => {
      result.current.run(SELECTION, 'second query', 60); // fires before the first resolves
    });

    await waitFor(() => expect(result.current.result?.verdict).toBe('second run verdict'));

    // Now let the stale first call resolve — it must NOT clobber the
    // second run's result.
    act(() => {
      resolveFirst(FAKE_RESULT);
    });
    await new Promise((r) => setTimeout(r, 0));

    expect(result.current.result?.verdict).toBe('second run verdict');
  });

  it('reset clears status, stages, result, and error', async () => {
    vi.spyOn(apiClient, 'runAnalysis').mockResolvedValue(FAKE_RESULT);
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.run(SELECTION, 'q', 60);
    });
    await waitFor(() => expect(result.current.status).toBe('done'));

    act(() => {
      result.current.reset();
    });

    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();
    expect(result.current.progressStages).toEqual([]);
  });
});
