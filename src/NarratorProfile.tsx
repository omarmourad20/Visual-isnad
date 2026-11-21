import { parseNarratorTags } from './narratorTags'

export type NarratorReference = {
  id: number
  name: string | null
  arabic_name: string | null
}

export type NarratorRecord = NarratorReference & {
  aqwal?: { alemId: number; alem: string; qawl: string }[]
  aliases?: string
  biography?: string
  profile_source?: string
  catalog_source_url?: string
  knowledge_graph_profile?: NarratorReference
  birth_display?: string
  death_display?: string
  birth_year?: number | null
  death_year?: number | null
  birth_place?: string
  death_place?: string
  tabaqah?: string
  region?: string
  tawthiq?: string
  grade?: string
  tags?: string
  parents?: string
  teachers_inds?: string
  students_inds?: string
  teachers?: NarratorReference[]
  students?: NarratorReference[]
  transmission_students?: NarratorReference[]
}

export function recordedText(value?: string | null) {
  const text = value?.trim() ?? ''
  return /^(?:n\/?a|\[\]|[–—-])$/i.test(text) ? '' : text
}

function textDirection(value: string) {
  if (/\p{Script=Arabic}/u.test(value) && !/\p{Script=Latin}/u.test(value)) {
    return { lang: 'ar', dir: 'rtl' } as const
  }
  return { dir: 'auto' } as const
}

export function narratorDate(display?: string, year?: number | null) {
  const recorded = recordedText(display)
  if (recorded || year == null) return recorded
  if (year < 0) return `${Math.abs(year)} BH`
  return `${year} AH`
}

function noteHeading(text: string) {
  // The source includes structured specialties and grade annotations in
  // biography. A prose note containing these terms can still be a biography.
  const specialties = /^(?:(?:Tafsir|Recitation)\s*\/\s*Quran|Art\s*\/\s*Poetry|Hadith|Fiqh|Governor|Commander|Qadhi\s*\(Judge\)|Narrator\s*(?:\[[^\]]*\]\s*)*)(?:\s*[,;]\s*|\s*$)/i
  let remainder = text
  for (let match = specialties.exec(remainder); match; match = specialties.exec(remainder)) {
    remainder = remainder.slice(match[0].length).trim()
  }
  return !remainder ? 'Specialties and source notes' : 'Biography'
}

function relationshipList(resolved?: NarratorReference[], ids?: string) {
  if (resolved) return resolved
  return [...new Set((ids ?? '').split(',').map(value => Number(value.trim())))]
    .filter(id => Number.isSafeInteger(id) && id > 0)
    .map(id => ({ id, name: null, arabic_name: null }))
}

function NarratorRelationships({ label, entries, onOpen }: {
  label: string
  entries: NarratorReference[]
  onOpen: (reference: NarratorReference) => void
}) {
  return (
    <details className="narrator-relationships">
      <summary lang="en" dir="ltr">{label} ({entries.length})</summary>
      {entries.length ? (
        <ul className="narrator-relations">
          {entries.map(entry => {
            const name = recordedText(entry.name)
            const arabic = recordedText(entry.arabic_name)
            const missing = !name && !arabic
            const labels = (
              <>
                {name && <bdi {...textDirection(name)}>{name}</bdi>}
                {arabic && <bdi lang="ar" dir="rtl">{entry.arabic_name}</bdi>}
              </>
            )
            return (
              <li key={entry.id}>
                {missing ? <span>Narrator #{entry.id} · Profile unavailable</span> : (
                  <button type="button" onClick={() => onOpen(entry)}>{labels}</button>
                )}
              </li>
            )
          })}
        </ul>
      ) : <p>No records listed.</p>}
    </details>
  )
}

export default function NarratorProfile({ record, source, status, onOpen, onRetry }: {
  record: NarratorRecord
  source: 'local' | 'knowledge_graph'
  status: 'loading' | 'loaded' | 'error'
  onOpen: (reference: NarratorReference) => void
  onRetry: () => void
}) {
  const linkedProfile = record.knowledge_graph_profile
  const fields = [
    ['Birth date', narratorDate(record.birth_display, record.birth_year)],
    ['Birth place', recordedText(record.birth_place)],
    ['Death date', narratorDate(record.death_display, record.death_year)],
    ['Death place', recordedText(record.death_place)],
    ['Tabaqah', recordedText(record.tabaqah)],
    ['Region', recordedText(record.region)],
    ['Tawthiq', recordedText(record.tawthiq)],
    ['Grade', recordedText(record.grade)],
  ].filter(([, value]) => value)

  const hasBiography = Boolean(recordedText(record.biography))
  const biography = hasBiography ? record.biography ?? '' : ''
  const tags = parseNarratorTags(record.tags)
  const notes = [
    ['Aliases and kunyas', recordedText(record.aliases)],
    ['Parents and lineage', recordedText(record.parents)],
  ].filter(([, value]) => value)

  return (
    <div className="narrator-profile-details" lang="en" dir="ltr">
      {fields.length > 0 && (
        <section>
          <h3>Profile facts</h3>
          <dl className="narrator-facts">
            {fields.map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd {...textDirection(value)}>{value}</dd></div>
            ))}
          </dl>
        </section>
      )}
      {status === 'loading' && <p role="status">Loading narrator details…</p>}
      {status === 'error' && (
        <p role="status">Could not load narrator details. <button type="button" onClick={onRetry}>Retry</button></p>
      )}
      {status === 'loaded' && (
        <>
          <section>
            <p>Profile source: {source === 'knowledge_graph' ? 'Hadith Knowledge Graph' : 'Visual Isnad catalog'}</p>
            {record.catalog_source_url && <a href={record.catalog_source_url}>Open catalog entry</a>}
            {linkedProfile && (
              <p><button type="button" onClick={() => onOpen(linkedProfile)}>
                Open Hadith Knowledge Graph profile
              </button></p>
            )}
          </section>
          <section>
            <h3>{biography ? noteHeading(biography.trim()) : 'Biography'}</h3>
            <p className="narrator-source-text" {...textDirection(biography)}>
              {biography || (source === 'knowledge_graph'
                ? 'No prose biography available in this source.'
                : 'No biographical notes stored for this narrator yet.')}
            </p>
          </section>
          {notes.map(([label, text]) => (
            <section key={label}>
              <h3>{label}</h3>
              <p className="narrator-source-text" {...textDirection(text)}>{text}</p>
            </section>
          ))}
          {tags.length > 0 && (
            <section>
              <h3>Tags</h3>
              <ul className="narrator-tag-list" role="list">
                {tags.map(tag => <li key={tag} {...textDirection(tag)}>{tag}</li>)}
              </ul>
            </section>
          )}
          {!!record.aqwal?.length && (
            <section>
              <h3>Scholarly evaluations ({record.aqwal.length})</h3>
              <ul className="narrator-evaluations">
                {record.aqwal.map((item, index) => (
                  <li key={`${item.alemId}-${index}`}>
                    <strong {...textDirection(item.alem ?? '')}>{item.alem}</strong>
                    <blockquote className="narrator-source-text" {...textDirection(item.qawl ?? '')}>
                      {item.qawl}
                    </blockquote>
                    {source === 'knowledge_graph' && <small>Hadith Knowledge Graph</small>}
                  </li>
                ))}
              </ul>
            </section>
          )}
          {source === 'knowledge_graph' && !record.aqwal?.length && (
            <section><h3>Scholarly evaluations</h3><p>No evaluations listed by this source.</p></section>
          )}
          <section aria-label="Narrator relationships">
            <p>{source === 'knowledge_graph'
              ? 'Teachers and students are general Knowledge Graph observations and may come from other collections.'
              : 'Teachers and students come from the narrator catalog.'}</p>
            <NarratorRelationships label={source === 'knowledge_graph' ? 'Teachers in KG routes' : 'Teachers'} entries={relationshipList(record.teachers, record.teachers_inds)} onOpen={onOpen} />
            <NarratorRelationships label={source === 'knowledge_graph' ? 'Students in KG routes' : 'Students'} entries={relationshipList(record.students, record.students_inds)} onOpen={onOpen} />
            {!!record.transmission_students?.length && (
              <NarratorRelationships label="Students listed in imported Bukhari edges (unreviewed)" entries={record.transmission_students} onOpen={onOpen} />
            )}
          </section>
        </>
      )}
    </div>
  )
}
