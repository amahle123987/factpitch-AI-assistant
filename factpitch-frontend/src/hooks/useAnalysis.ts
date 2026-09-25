import { useCallback, useRef, useState } from 'react';
import { ApiError, runAnalysis } from '../services/apiClient';
import type { AnalyzeResult } from '../types/api';
import type { TeamSelection } from '../types/api';

export type AnalysisStatus = 'idle' | 'running' | 'done' | 'error';

interface UseAnalysisResult {
  status: AnalysisStatus;
  progressStages: string[];
  result: AnalyzeResult | null;
  errorMessage: string | null;
  run: (selection: TeamSelection, query: string, windowDays: number) => void;
  reset: () => void;
}

export function useAnalysis(): UseAnalysisResult {
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [progressStages, setProgressStages] = useState<string[]>([]);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Guards against a stale in-flight request setting state after a newer
  // run has started (e.g. the user clicks Analyze again before the first
  // call resolves).
  const runId = useRef(0);

  const run = useCallback((selection: TeamSelection, query: string, windowDays: number) => {
    const thisRun = ++runId.current;
    setStatus('running');
    setProgressStages([]);
    setResult(null);
    setErrorMessage(null);

    runAnalysis({
      teamId: selection.teamId,
      teamName: selection.teamName,
      query,
      windowDays,
      onProgress: (stage) => {
        if (runId.current !== thisRun) return;
        setProgressStages((prev) => [...prev, stage]);
      },
    })
      .then((res) => {
        if (runId.current !== thisRun) return;
        setResult(res);
        setStatus('done');
      })
      .catch((err) => {
        if (runId.current !== thisRun) return;
        setErrorMessage(err instanceof ApiError ? err.message : 'Something went wrong running the analysis.');
        setStatus('error');
      });
  }, []);

  const reset = useCallback(() => {
    runId.current += 1; // invalidate any in-flight request
    setStatus('idle');
    setProgressStages([]);
    setResult(null);
    setErrorMessage(null);
  }, []);

  return { status, progressStages, result, errorMessage, run, reset };
}
