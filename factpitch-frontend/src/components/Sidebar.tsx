import { useCompetitions } from '../hooks/useCompetitions';
import { useTeams } from '../hooks/useTeams';
import { Combobox } from './Combobox';
import type { Team } from '../types/api';

export interface TeamSelection {
  teamId: number;
  teamName: string;
  competition: string;
}

interface SidebarProps {
  competition: string | null;
  onCompetitionChange: (competition: string | null) => void;
  selection: TeamSelection | null;
  onSelectionChange: (selection: TeamSelection | null) => void;
  windowDays: number;
  onWindowDaysChange: (days: number) => void;
}

export function Sidebar({
  competition,
  onCompetitionChange,
  selection,
  onSelectionChange,
  windowDays,
  onWindowDaysChange,
}: SidebarProps) {
  const { competitions, error: competitionsError } = useCompetitions();
  const { teams, loading: teamsLoading, error: teamsError } = useTeams(competition);

  const apiUnreachable = Boolean(competitionsError || teamsError);
  const selectedTeam = selection ? teams.find((t) => t.id === selection.teamId) ?? null : null;

  function handleTeamChange(team: Team) {
    onSelectionChange({ teamId: team.id, teamName: team.name, competition: team.competition });
  }

  return (
    <aside style={{ width: 280, flexShrink: 0 }}>
      <div className="eyebrow">Team</div>

      {apiUnreachable && (
        <div
          className="card"
          style={{ borderColor: 'var(--loss)', marginBottom: 12, fontSize: 13, color: 'var(--text-muted)' }}
        >
          Can't reach the API backend.
          <br />
          <br />
          Start it with: <code className="mono">uvicorn api.main:app --reload</code>
        </div>
      )}

      <label htmlFor="competition-select" style={{ display: 'block', fontSize: 13, marginBottom: 6 }}>
        Restrict to a competition (optional)
      </label>
      <select
        id="competition-select"
        value={competition ?? ''}
        disabled={apiUnreachable}
        onChange={(e) => {
          onCompetitionChange(e.target.value || null);
          onSelectionChange(null); // switching leagues invalidates the current pick
        }}
        style={{
          width: '100%',
          padding: '10px 12px',
          marginBottom: 16,
          background: 'var(--panel)',
          color: 'var(--text)',
          border: 'var(--border-width) solid var(--panel-border)',
          borderRadius: 6,
          fontSize: 14,
          fontFamily: 'Inter, sans-serif',
        }}
      >
        <option value="">Any competition</option>
        {competitions.map((c) => (
          <option key={c.code} value={c.code}>
            {c.name}
          </option>
        ))}
      </select>

      <div style={{ marginBottom: 16 }}>
        <Combobox
          options={teams}
          getKey={(t) => t.id}
          getLabel={(t) => t.name}
          value={selectedTeam}
          onChange={handleTeamChange}
          disabled={apiUnreachable || teamsLoading}
          placeholder={teamsLoading ? 'Loading teams…' : 'Search for a team'}
          aria-label="Search for a team"
        />
      </div>

      <label htmlFor="window-days" style={{ display: 'block', fontSize: 13, marginBottom: 6 }}>
        Days before/after to compare
      </label>
      <div className="mono" style={{ color: 'var(--accent)', fontSize: 14, marginBottom: 4 }}>
        {windowDays}
      </div>
      <input
        id="window-days"
        type="range"
        min={15}
        max={180}
        step={15}
        value={windowDays}
        onChange={(e) => onWindowDaysChange(Number(e.target.value))}
        style={{ width: '100%', marginBottom: 16, accentColor: 'var(--accent)' }}
      />

      {!apiUnreachable && (
        <div
          className="card"
          style={{
            borderColor: selection ? 'var(--win)' : 'var(--panel-border)',
            fontSize: 13,
            color: selection ? 'var(--win)' : 'var(--text-muted)',
          }}
        >
          {selection ? `Team: ${selection.teamName}` : 'Select a team above to get started.'}
        </div>
      )}
    </aside>
  );
}
