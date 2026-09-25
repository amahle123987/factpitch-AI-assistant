import { useState } from 'react';
import type { AnalysisStatus } from '../hooks/useAnalysis';

interface StatusBoxProps {
  status: AnalysisStatus;
  stages: string[];
  errorMessage: string | null;
}

const LABELS: Record<AnalysisStatus, string> = {
  idle: '',
  running: 'Investigating…',
  done: 'Case Processed',
  error: 'Case Stalled',
};

export function StatusBox({ status, stages, errorMessage }: StatusBoxProps) {
  const [expanded, setExpanded] = useState(true);

  if (status === 'idle') return null;

  // Collapse automatically once it succeeds, same as the Streamlit version —
  // but let the user re-expand it to see the stage-by-stage log if they want.
  const isOpen = status !== 'done' || expanded;
  const borderColor = status === 'error' ? 'var(--loss)' : status === 'done' ? 'var(--win)' : 'var(--panel-border)';

  return (
    <div className="investigation-log" style={{ borderColor }} aria-live="polite">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="investigation-log-toggle"
        style={{ color: status === 'error' ? 'var(--loss)' : 'var(--ink)' }}
        aria-expanded={isOpen}
      >
        {status === 'running' && <span className="mono">⏳</span>}
        {status === 'done' && <span className="mono">✓</span>}
        {status === 'error' && <span className="mono">✕</span>}
        {LABELS[status]}
      </button>

      {isOpen && (
        <div className="investigation-log-entries">
          {stages.map((stage, i) => (
            <div key={i} className="mono" style={{ padding: '2px 0' }}>
              {String(i + 1).padStart(2, '0')}. {stage}
            </div>
          ))}
          {status === 'error' && errorMessage && (
            <div className="investigation-log-error">{errorMessage}</div>
          )}
        </div>
      )}
    </div>
  );
}
