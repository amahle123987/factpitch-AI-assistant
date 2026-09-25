import type { KeyEvent, NewsResearch, PrimaryEvent } from '../types/api';

interface ExhibitCardProps {
  number: number;
  date: string;
  headline: string;
  body: string;
  primary?: boolean;
}

function ExhibitCard({ number, date, headline, body, primary }: ExhibitCardProps) {
  return (
    <article className={primary ? 'exhibit primary' : 'exhibit'}>
      <div className="exhibit-tag">
        <span className="label">Exhibit {String(number).padStart(2, '0')}</span>
        {primary && <span className="exhibit-primary-flag label">Primary evidence</span>}
        <span className="mono exhibit-date">{date}</span>
      </div>
      <h3 className="display exhibit-headline">{headline}</h3>
      <p className="exhibit-body">{body}</p>
    </article>
  );
}

interface VerdictStampProps {
  verdict: string;
}

/** The case's closing ruling, stamped like a document sign-off. */
function VerdictStamp({ verdict }: VerdictStampProps) {
  return (
    <div className="verdict-block">
      <div className="label" style={{ marginBottom: 10 }}>
        Verdict
      </div>
      <p className="verdict-text">{verdict}</p>
      <span className="stamp">On the record</span>
    </div>
  );
}

interface NewsExhibitsProps {
  news: NewsResearch;
  verdict: string;
}

function isSamePrimaryEvent(primary: PrimaryEvent | null, event: KeyEvent): boolean {
  return Boolean(primary && primary.date === event.date && primary.headline === event.headline);
}

/** Renders the news research as numbered exhibits — the primary event first
 * (if the backend identified one), then the remaining key events in order —
 * followed by the summary and closing verdict stamp. */
export function NewsExhibits({ news, verdict }: NewsExhibitsProps) {
  const primary = news.primary_event;
  const remaining = primary ? news.key_events.filter((e) => !isSamePrimaryEvent(primary, e)) : news.key_events;

  let exhibitNumber = 0;

  return (
    <section className="results-section" aria-labelledby="news-exhibits-title">
      <div className="label">Evidence on file</div>
      <h2 id="news-exhibits-title" className="display results-section-title">
        News exhibits
      </h2>

      {news.key_events.length === 0 ? (
        <p className="exhibit-opener-intro">No news events turned up for this window — the record is quiet.</p>
      ) : (
        <div className="exhibit-stack">
          {primary && (
            <ExhibitCard
              number={++exhibitNumber}
              date={primary.date}
              headline={primary.headline}
              body={primary.reason}
              primary
            />
          )}
          {remaining.map((event) => (
            <ExhibitCard
              key={`${event.date}-${event.headline}`}
              number={++exhibitNumber}
              date={event.date}
              headline={event.headline}
              body={event.detail}
            />
          ))}
        </div>
      )}

      {news.summary && (
        <div className="case-summary">
          <div className="label" style={{ marginBottom: 6 }}>
            Summary for the file
          </div>
          <p className="exhibit-body">{news.summary}</p>
        </div>
      )}

      <VerdictStamp verdict={verdict} />
    </section>
  );
}
