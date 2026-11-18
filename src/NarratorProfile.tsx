import { parseNarratorTags } from './narratorTags'

export type NarratorReference = {
  id: number
  name: string | null
  arabic_name: string | null
}

export type NarratorRecord = NarratorReference & {
  aliases?: string
  biography?: string
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

export function narratorDate(display?: string, year?: number | null) {
  const recorded = recordedText(display)
  if (recorded || year == null) return recorded
  if (year < 0) return `${Math.abs(year)} BH`
  return String(year)
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
      <summary>{label} ({entries.length})</summary>
      {entries.length ? (
        <ul className="narrator-relations">
          {entries.map(entry => {
            const missing = entry.name === null && entry.arabic_name === null
            const labels = (
              <>
                <bdi>{recordedText(entry.name) || `Narrator #${entry.id}`}</bdi>
                {recordedText(entry.arabic_name) && <bdi lang="ar" dir="rtl">{entry.arabic_name}</bdi>}
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

export default function NarratorProfile({ record, status, onOpen, onRetry }: {
  record: NarratorRecord
  status: 'loading' | 'loaded' | 'error'
  onOpen: (reference: NarratorReference) => void
  onRetry: () => void
}) {
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

  const biography = recordedText(record.biography)
  const tags = parseNarratorTags(record.tags)
  const notes = [
    ['Aliases and kunyas', recordedText(record.aliases)],
    ['Parents and lineage', recordedText(record.parents)],
  ].filter(([, value]) => value)

  return (
    <div className="narrator-profile-details">
      {fields.length > 0 && (
        <dl className="narrator-facts">
          {fields.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd dir="auto">{value}</dd></div>
          ))}
        </dl>
      )}
      {status === 'loading' && <p role="status">Loading narrator details…</p>}
      {status === 'error' && (
        <p role="status">Could not load narrator details. <button type="button" onClick={onRetry}>Retry</button></p>
      )}
      {status === 'loaded' && (
        <>
          <section>
            <h3>{biography ? noteHeading(biography) : 'Biography'}</h3>
            <p className="narrator-source-text" dir="auto">
              {biography || 'No biographical notes stored for this narrator yet.'}
            </p>
          </section>
          {notes.map(([label, text]) => (
            <section key={label}>
              <h3>{label}</h3>
              <p className="narrator-source-text" dir="auto">{text}</p>
            </section>
          ))}
          {tags.length > 0 && (
            <section>
              <h3>Tags</h3>
              <ul className="narrator-tag-list" role="list">
                {tags.map(tag => <li key={tag} dir="auto">{tag}</li>)}
              </ul>
            </section>
          )}
          <section aria-label="Narrator relationships">
            <NarratorRelationships label="Teachers" entries={relationshipList(record.teachers, record.teachers_inds)} onOpen={onOpen} />
            <NarratorRelationships label="Catalog students" entries={relationshipList(record.students, record.students_inds)} onOpen={onOpen} />
            {!!record.transmission_students?.length && (
              <NarratorRelationships label="Narrators linked in imported Bukhari chains" entries={record.transmission_students} onOpen={onOpen} />
            )}
          </section>
        </>
      )}
    </div>
  )
}
