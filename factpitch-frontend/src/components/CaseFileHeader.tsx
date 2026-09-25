import { useCompetitions } from '../hooks/useCompetitions';
import { useHeroData } from '../hooks/useHeroData';
import { ThemeToggle } from './ThemeToggle';
import type { TeamSelection } from '../types/api';

interface VitalsChipProps {
  label: string;
  value: string;
}

function VitalsChip({ label, value }: VitalsChipProps) {
  return (
    <div className="vitals-chip">
      <div className="label" style={{ marginBottom: 4 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 16, fontWeight: 600 }}>
        {value}
      </div>
    </div>
  );
}

interface CaseFileHeaderProps {
  selection: TeamSelection | null;
}

export function CaseFileHeader({ selection }: CaseFileHeaderProps) {
  const { crestUrl, headline } = useHeroData(selection);
  const { competitions } = useCompetitions();

  // Competitions are keyed by short code (e.g. "PL") everywhere else in the
  // app — team lookups, headline-stat requests — so TeamSelection carries
  // the code too. Here we just want the full name for display; fall back
  // to the code itself if the competitions list hasn't loaded yet (or the
  // lookup somehow misses), so the header never goes blank.
  const competitionName = selection
    ? (competitions.find((c) => c.code === selection.competition)?.name ?? selection.competition)
    : null;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div className="photo-frame" aria-hidden={!selection}>
            {selection && crestUrl ? (
              <img
                src={crestUrl}
                alt={`${selection.teamName} crest`}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : selection ? (
              <span className="display" style={{ fontSize: 28 }}>
                {selection.teamName[0]}
              </span>
            ) : (
              <span className="label" style={{ fontSize: 9, textAlign: 'center', lineHeight: 1.4 }}>
                No
                <br />
                Photo
                <br />
                On File
              </span>
            )}
          </div>

          <div>
            <div className="label" style={{ marginBottom: 6 }}>
              Case File{selection ? ` · ${competitionName}` : ''}
            </div>
            <h1 className="display" style={{ fontSize: 36, margin: 0, fontWeight: 600 }}>
              {selection ? selection.teamName : 'FactPitch'}
            </h1>
            <p style={{ color: 'var(--ink-muted)', fontSize: 14, margin: '6px 0 0 0', fontStyle: 'italic' }}>
              {selection
                ? 'Cross-referencing recent news against the performance record.'
                : 'Your form guide, verified.'}
            </p>
          </div>
        </div>

        <ThemeToggle />
      </div>

      {headline && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
          <VitalsChip label="Position" value={`#${headline.position}`} />
          <VitalsChip label="Played" value={String(headline.played ?? '—')} />
          <VitalsChip label="Record" value={`${headline.won}-${headline.draw}-${headline.lost}`} />
          <VitalsChip
            label="Goal Diff"
            value={
              headline.goal_difference !== null && headline.goal_difference > 0
                ? `+${headline.goal_difference}`
                : String(headline.goal_difference)
            }
          />
          <VitalsChip label="Points" value={String(headline.points ?? '—')} />
        </div>
      )}
    </>
  );
}
