import { useCompetitions } from '../hooks/useCompetitions';
import { useTeams } from '../hooks/useTeams';
import { Combobox } from './Combobox';
import type { Team, TeamSelection } from '../types/api';

interface CaseIntakeProps {
  competition: string | null;
  onCompetitionChange: (competition: string | null) => void;
  selection: TeamSelection | null;
  onSelectionChange: (selection: TeamSelection | null) => void;
  windowDays: number;
  onWindowDaysChange: (days: number) => void;
}

const fieldLabelStyle: React.CSSProperties = { display: 'block', marginBottom: 6 };
const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '9px 11px',
  background: 'var(--panel)',
  color: 'var(--ink)',
  border: 'var(--border-width) solid var(--panel-border)',
  borderRadius: 2,
  fontSize: 14,
  fontFamily: 'Inter, sans-serif',
};

export function CaseIntake({
  competition,
  onCompetitionChange,
  selection,
  onSelectionChange,
  windowDays,
  onWindowDaysChange,
}: CaseIntakeProps) {
  const { competitions, error: competitionsError } = useCompetitions();
  const { teams, loading: teamsLoading, error: teamsError } = useTeams(competition);

  const apiUnreachable = Boolean(competitionsError || teamsError);
  const selectedTeam = selection ? teams.find((t) => t.id === selection.teamId) ?? null : null;

  function handleTeamChange(team: Team) {
    onSelectionChange({ teamId: team.id, teamName: team.name, competition: team.competition });
  }

  return (
    <div>
      <div className="label" style={{ marginBottom: 10 }}>
        Case Intake
      </div>

      {apiUnreachable && (
        <div className="exhibit" style={{ borderLeftColor: 'var(--stamp)', marginBottom: 14, fontSize: 13 }}>
          <span style={{ color: 'var(--stamp)' }}>Case file unreachable.</span>{' '}
          <span style={{ color: 'var(--ink-muted)' }}>
            Start the records office with: <code className="mono">uvicorn api.main:app --reload</code>
          </span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <div>
          <label htmlFor="jurisdiction-select" className="label" style={fieldLabelStyle}>
            Jurisdiction (optional)
          </label>
          <select
            id="jurisdiction-select"
            value={competition ?? ''}
            disabled={apiUnreachable}
            onChange={(e) => {
              onCompetitionChange(e.target.value || null);
              onSelectionChange(null);
            }}
            style={selectStyle}
          >
            <option value="">Any competition</option>
            {competitions.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label" style={fieldLabelStyle}>
            Subject
          </label>
          <Combobox
            options={teams}
            getKey={(t) => t.id}
            getLabel={(t) => t.name}
            value={selectedTeam}
            onChange={handleTeamChange}
            disabled={apiUnreachable || teamsLoading}
            placeholder={teamsLoading ? 'Loading file…' : 'Search for a team'}
            aria-label="Search for a team"
          />
        </div>
      </div>

      <label htmlFor="window-days" className="label" style={fieldLabelStyle}>
        Investigation window — {windowDays} days either side
      </label>
      <input
        id="window-days"
        type="range"
        min={15}
        max={180}
        step={15}
        value={windowDays}
        onChange={(e) => onWindowDaysChange(Number(e.target.value))}
        style={{ width: '100%', marginBottom: 16, accentColor: 'var(--stamp)' }}
      />

      {!apiUnreachable && (
        <p className="mono" style={{ fontSize: 13, color: selection ? 'var(--win)' : 'var(--ink-muted)', margin: 0 }}>
          {selection ? `Subject on file: ${selection.teamName}` : 'No subject selected.'}
        </p>
      )}
    </div>
  );
}
