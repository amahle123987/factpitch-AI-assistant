import { useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { CaseFileHeader } from './components/CaseFileHeader';
import { CaseIntake } from './components/CaseIntake';
import { ExhibitOpener } from './components/ExhibitOpener';
import type { TeamSelection } from './types/api';
import './theme.css';

function IconRail() {
  return (
    <nav
      aria-label="Primary"
      style={{
        width: 64,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: 20,
        borderRight: 'var(--border-width) solid var(--panel-border)',
        minHeight: '100vh',
      }}
    >
      <div
        className="display"
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: 'var(--border-width) solid var(--panel-border)',
          background: 'var(--panel)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 16,
        }}
        title="FactPitch"
      >
        F
      </div>
    </nav>
  );
}

function App() {
  const [competition, setCompetition] = useState<string | null>(null);
  const [selection, setSelection] = useState<TeamSelection | null>(null);
  const [windowDays, setWindowDays] = useState(60);

  return (
    <ThemeProvider>
      <div style={{ display: 'flex' }}>
        <IconRail />

        <main style={{ flex: 1, padding: '40px 24px', display: 'flex', justifyContent: 'center' }}>
          <div className="page" style={{ width: '100%', maxWidth: 760, padding: '28px 32px' }}>
            <CaseFileHeader selection={selection} />

            <hr
              style={{ border: 'none', borderTop: 'var(--border-width) solid var(--panel-border)', margin: '20px 0' }}
            />

            <CaseIntake
              competition={competition}
              onCompetitionChange={setCompetition}
              selection={selection}
              onSelectionChange={setSelection}
              windowDays={windowDays}
              onWindowDaysChange={setWindowDays}
            />

            <ExhibitOpener selection={selection} windowDays={windowDays} />

            <p style={{ color: 'var(--ink-muted)', fontSize: 12, marginTop: 24 }}>
              Phase 6 of 6 — contrast and accessibility pass complete. Card borders, the draw
              legend, and the dark-mode stamp/loss red now clear WCAG AA across all three themes,
              and rolling-form results use shape as well as color so the chart still reads for
              colorblind viewers.
            </p>
          </div>
        </main>
      </div>
    </ThemeProvider>
  );
}

export default App;
