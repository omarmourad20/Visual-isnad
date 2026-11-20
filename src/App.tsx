import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Landing from './Landing'
import { groupChains, orderChain, type EdgeRecord } from './transmissionPaths'
import NarratorProfile, { narratorDate, recordedText, type NarratorRecord, type NarratorReference } from './NarratorProfile'

type IconName =
  | 'branch' | 'arrow' | 'book' | 'chevron' | 'close'
  | 'menu' | 'minus' | 'plus'
  | 'search' | 'user'

type Narrator = {
  id: number
  initials: string
  name: string
  arabic: string
  era: string
  location: string
  role: string
  grade: string
  died: string
  record: NarratorRecord
}

const KG_NARRATOR_OFFSET = 1_000_000

type KnowledgeGraphChain = {
  sanad_id: number
  grade: string | null
  narrators: NarratorRecord[]
  edges: EdgeRecord[]
}

type SourceCandidate = {
  right_key: string
  right_id: string
  provider: string
  edition: string
  reference: string
  confidence: string
  isnad_agreement: string
  reason: string
  can_preview_routes: boolean
}

type KnowledgeGraphNarrator = {
  name: string
  nickname?: string
  nasab?: string
  rank?: string
  tabaka?: number
  iqama?: string
  birthYear?: number
  deathYear?: number
  deathPlace?: string
  aqwal?: NarratorRecord['aqwal']
  biography?: string
  teachers?: { id: number; name: string }[]
  students?: { id: number; name: string }[]
}

function mapKnowledgeGraphNarrator(id: number, raw: KnowledgeGraphNarrator) {
  const reference = (person: { id: number; name: string }): NarratorReference => ({
    id: KG_NARRATOR_OFFSET + person.id,
    name: person.name,
    arabic_name: null,
  })
  return mapNarrator({
    id,
    name: raw.nickname || raw.name,
    arabic_name: raw.name,
    aliases: [raw.nickname, raw.nasab].filter(Boolean).join(' · '),
    grade: raw.rank,
    tabaqah: raw.tabaka == null ? '' : String(raw.tabaka),
    region: raw.iqama,
    birth_year: raw.birthYear,
    death_year: raw.deathYear,
    death_place: raw.deathPlace,
    aqwal: raw.aqwal,
    biography: raw.biography,
    teachers: raw.teachers?.map(reference),
    students: raw.students?.map(reference),
  })
}

type ProfileDraft = {
  name: string
  arabic_name: string
  grade: string
  tabaqah: string
  tawthiq: string
  birth_display: string
  birth_place: string
  death_display: string
  death_place: string
  region: string
  biography: string
}

type HadithRecord = {
  id: number
  hadith_number: string
  in_book_reference?: string
  book_title?: string
  chapter_number?: string
  chapter_title?: string
  chapter_title_arabic?: string
  arabic_matn?: string
  arabic_isnad?: string
  arabic_full?: string
  english_matn?: string
  topic?: string
  grade?: string
  preview?: string
}

type BookRecord = {
  number: number
  title: string
  title_arabic: string
  count: number
}


const PRODUCTION_API_ORIGIN = 'https://visual-isnad.onrender.com'

function resolveApiOrigin() {
  const fromEnv = String(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')
  if (fromEnv) return fromEnv
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') return ''
  }
  return PRODUCTION_API_ORIGIN
}

const API_ORIGIN = resolveApiOrigin()
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api/v1` : '/api/v1'

function initialsFor(name: string) {
  const cleaned = name.replace(/[ﷺ()'"]/g, ' ').trim()
  if (cleaned.toLowerCase().includes('prophet')) return 'ﷺ'
  const parts = cleaned.split(/\s+/).filter(Boolean)
  if (!parts.length) return 'NA'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
}

function roleOf(raw: { id: number; name?: string; grade?: string; tabaqah?: string }) {
  const blob = `${raw.name || ''} ${raw.grade || ''} ${raw.tabaqah || ''}`.toLowerCase()
  if (raw.grade === "Unmatched isnad name") return "Unresolved"
  if (raw.id === 1 || blob.includes('rasool') || blob.includes('prophet')) return 'Prophet'
  if (blob.includes('comp.') || blob.includes('sahabi') || blob.includes('companion')) return 'Companion'
  if (raw.id === 30001 || blob.includes('compiler')) return 'Compiler'
  if (blob.includes('tabi') || blob.includes('follower') || blob.includes("taba'")) return 'Successor'
  return 'Narrator'
}

type Generation = 'prophet' | 'companion' | 'successor' | 'scholar'

const GENERATION_RANK: Record<Generation, number> = {
  prophet: 0,
  companion: 1,
  successor: 2,
  scholar: 3,
}

function deathYearAh(person: Narrator) {
  const match = /(^|\s)(\d+)\s*AH\b/i.exec(person.record.death_display ?? '')
  if (match) return Number(match[2])
  const year = person.record.death_year
  return !person.record.death_display && year != null && year > 0 ? year : null
}

function generationOf(person: Narrator, index: number, count: number): Generation {
  if (person.role === 'Prophet' || person.id === 1) return 'prophet'
  if (person.role === 'Companion') return 'companion'
  if (person.role === 'Compiler' || person.id === 30001) return 'scholar'
  if (person.role === 'Successor') return 'successor'
  const death = deathYearAh(person)
  if (death != null) {
    if (death <= 50) return 'companion'
    if (death <= 180) return 'successor'
    return 'scholar'
  }
  if (index >= count - 1) return 'scholar'
  const share = index / Math.max(1, count - 1)
  if (share < 0.28) return 'companion'
  if (share < 0.68) return 'successor'
  return 'scholar'
}

function cleanPlace(value?: string) {
  return (value || '')
    .replace(/[()[\]]/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\s*,\s*/g, ', ')
    .trim()
    .replace(/^,|,$/g, '')
}

function formatPlaces(value?: string) {
  const cleaned = cleanPlace(value)
  if (!cleaned || /^na$/i.test(cleaned)) return ''
  return cleaned
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part && !/^na$/i.test(part))
    .join(', ')
}

function joinYearAndPlace(year?: string, place?: string) {
  const displayYear = (year || '').trim()
  const displayPlace = formatPlaces(place)
  if (displayYear && displayPlace) return `${displayYear}, ${displayPlace}`
  return displayYear || displayPlace || '—'
}

function previewText(value: string, wordLimit: number) {
  const text = value.trim()
  if (!text) return { preview: '', truncated: false }
  const words = text.split(/\s+/).filter(Boolean)
  if (words.length <= wordLimit) return { preview: text, truncated: false }
  return { preview: `${words.slice(0, wordLimit).join(' ')}…`, truncated: true }
}

function mapNarrator(raw: NarratorRecord): Narrator {
  const english = recordedText(raw.name)
  const arabic = recordedText(raw.arabic_name)
  const name = english || arabic || `Narrator #${raw.id}`
  return {
    id: raw.id,
    initials: initialsFor(name),
    name,
    arabic,
    era: recordedText(raw.tabaqah) || recordedText(raw.grade) || 'Unknown',
    location: formatPlaces(raw.region) || formatPlaces(raw.birth_place) || 'Unknown',
    role: roleOf({ ...raw, name: english }),
    grade: recordedText(raw.grade) || recordedText(raw.tawthiq) || 'Unrated',
    died: joinYearAndPlace(narratorDate(raw.death_display, raw.death_year), raw.death_place),
    record: raw,
  }
}

function draftFromNarrator(person?: Narrator): ProfileDraft {
  const record = person?.record
  return {
    name: record?.name ?? '',
    arabic_name: record?.arabic_name ?? '',
    grade: record?.grade ?? '',
    tabaqah: record?.tabaqah ?? '',
    tawthiq: record?.tawthiq ?? '',
    birth_display: record?.birth_display ?? '',
    birth_place: record?.birth_place ?? '',
    death_display: record?.death_display ?? '',
    death_place: record?.death_place ?? '',
    region: record?.region ?? '',
    biography: record?.biography ?? '',
  }
}

let sessionCsrf = ''
const EDITOR_TOKEN_KEY = 'visual-isnad-editor-token'

function editorToken() {
  try {
    return sessionStorage.getItem(EDITOR_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

function storeEditorToken(token: string) {
  try {
    if (token) sessionStorage.setItem(EDITOR_TOKEN_KEY, token)
    else sessionStorage.removeItem(EDITOR_TOKEN_KEY)
  } catch {
    /* ignore private-mode storage failures */
  }
}

function csrfToken() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)
  if (match) return decodeURIComponent(match[1])
  return sessionCsrf
}

async function fetchJson(path: string, init?: RequestInit) {
  const method = (init?.method || 'GET').toUpperCase()
  const mutating = method !== 'GET' && method !== 'HEAD'
  const needsSession = mutating || path.startsWith('/auth/')
  const token = editorToken()
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: needsSession || !API_ORIGIN ? 'include' : 'omit',
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(mutating && csrfToken() ? { 'X-CSRFToken': csrfToken() } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let detail = `${path} failed (${response.status})`
    try {
      const errorBody = await response.json()
      if (errorBody?.detail) detail = String(errorBody.detail)
    } catch {
      /* keep the status message */
    }
    throw new Error(detail)
  }
  if (response.status === 204) return null
  const data = await response.json()
  if (data && typeof data.csrfToken === 'string' && data.csrfToken) {
    sessionCsrf = data.csrfToken
    delete data.csrfToken
  }
  if (data && typeof data.token === 'string' && data.token) {
    storeEditorToken(data.token)
    delete data.token
  }
  return data
}

function unwrapList<T>(payload: any): T[] {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const TIER_ORDER: Generation[] = ['prophet', 'companion', 'successor', 'scholar']
const TIER_LABELS: Record<Generation, string> = {
  prophet: 'PROPHETIC ERA',
  companion: 'COMPANION',
  successor: 'SUCCESSORS · TĀBIʿŪN',
  scholar: 'HADITH SCHOLARS',
}

const NODE_HEIGHT = 58
const NODE_GAP = 42
const BAND_PAD = 16
const BAND_GAP = 8
const MIN_BAND_HEIGHT: Record<Generation, number> = {
  prophet: 72,
  companion: 72,
  successor: 96,
  scholar: 96,
}

type ChainLayout = {
  positions: { x: number; y: number }[]
  bands: { tier: Generation; top: number; height: number }[]
  height: number
}

function layoutChain(people: Narrator[]): ChainLayout {
  const count = people.length
  if (!count) {
    return { positions: [], bands: [], height: 620 }
  }

  let minRank = 0
  const tiers = people.map((person, index) => {
    const guessed = generationOf(person, index, count)
    const rank = Math.max(minRank, GENERATION_RANK[guessed])
    minRank = rank
    return TIER_ORDER[rank]
  })

  const grouped = new Map<Generation, number[]>()
  TIER_ORDER.forEach((tier) => grouped.set(tier, []))
  tiers.forEach((tier, index) => grouped.get(tier)?.push(index))

  const positions = Array.from({ length: count }, () => ({ x: 345, y: 20 }))
  const bands: ChainLayout['bands'] = []
  let cursor = 16

  TIER_ORDER.forEach((tier) => {
    const indexes = grouped.get(tier) || []
    const n = indexes.length
    const needed = n === 0
      ? MIN_BAND_HEIGHT[tier]
      : BAND_PAD + n * NODE_HEIGHT + Math.max(0, n - 1) * NODE_GAP + BAND_PAD
    const height = Math.max(MIN_BAND_HEIGHT[tier], needed)
    bands.push({ tier, top: cursor, height })

    indexes.forEach((personIndex, slot) => {
      const y = n === 1
        ? cursor + (height - NODE_HEIGHT) / 2
        : cursor + BAND_PAD + slot * (NODE_HEIGHT + NODE_GAP)
      const offset = n === 1 ? 0 : slot % 2 === 0 ? -150 : 150
      positions[personIndex] = { x: 345 + offset, y }
    })

    cursor += height + BAND_GAP
  })

  return { positions, bands, height: Math.max(620, cursor + 12) }
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    branch: <><path d="M6 3v8a4 4 0 0 0 4 4h8" /><path d="m15 12 3 3-3 3" /><path d="M6 8h5a4 4 0 0 0 4-4V3" /></>,
    search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11a2 2 0 0 1 2 2v15a2.5 2.5 0 0 0-2.5-2.5H4Z" /><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H15a2 2 0 0 0-2 2v15a2.5 2.5 0 0 1 2.5-2.5H20Z" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    minus: <><path d="M5 12h14" /></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    arrow: <><path d="M5 12h14M14 7l5 5-5 5" /></>,
    chevron: <><path d="m8 10 4 4 4-4" /></>,
  }

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  )
}

function Explorer({ onHome }: { onHome: () => void }) {
  const [books, setBooks] = useState<BookRecord[]>([])
  const [hadithsByBook, setHadithsByBook] = useState<Record<number, HadithRecord[]>>({})
  const [expandedBook, setExpandedBook] = useState<number | null>(1)
  const [currentHadith, setCurrentHadith] = useState<HadithRecord | null>(null)
  const [narrators, setNarrators] = useState<Narrator[]>([])
  const [chains, setChains] = useState<EdgeRecord[][]>([])
  const [chainIndex, setChainIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [selectedHadithId, setSelectedHadithId] = useState<number | null>(null)
  const [selectedHadithNumber, setSelectedHadithNumber] = useState<string | null>(null)
  const [kgChains, setKgChains] = useState<KnowledgeGraphChain[]>([])
  const [selectedKgSanadId, setSelectedKgSanadId] = useState<number | null>(null)
  const [kgHadithId, setKgHadithId] = useState<number | null>(null)
  const [sourceCandidates, setSourceCandidates] = useState<SourceCandidate[]>([])
  const [sourcePage, setSourcePage] = useState(1)
  const [hasMoreSources, setHasMoreSources] = useState(false)
  const [sourceError, setSourceError] = useState('')
  const [sourceStatus, setSourceStatus] = useState('loading')
  const [previewPending, setPreviewPending] = useState(false)
  const [previewingSource, setPreviewingSource] = useState<SourceCandidate | null>(null)
  const sourceHadithNumber = kgHadithId === null ? currentHadith?.hadith_number : undefined
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [searchHits, setSearchHits] = useState<Narrator[]>([])
  const [zoom, setZoom] = useState(100)
  const graphCanvasRef = useRef<HTMLDivElement>(null)
  const zoomRef = useRef(100)
  const graphCenteredRef = useRef(false)
  zoomRef.current = zoom
  const [panelOpen, setPanelOpen] = useState(() =>
    typeof window === 'undefined' ? true : window.matchMedia('(min-width: 1101px)').matches,
  )
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [highlightMadar, setHighlightMadar] = useState(false)
  const [tracePath, setTracePath] = useState(false)
  const [selectedEdge, setSelectedEdge] = useState<number | null>(null)
  const [editingProfile, setEditingProfile] = useState(false)
  const [profileDraft, setProfileDraft] = useState<ProfileDraft>(() => draftFromNarrator())
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileSaveError, setProfileSaveError] = useState('')
  const [editor, setEditor] = useState({ authenticated: false, can_edit_biographies: false, username: '', initials: '' })
  const [authOpen, setAuthOpen] = useState(false)
  const [loginUser, setLoginUser] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)
  const [hadithReaderOpen, setHadithReaderOpen] = useState(false)
  const [inspectedNarrator, setInspectedNarrator] = useState<Narrator | null>(null)
  const [narratorDetails, setNarratorDetails] = useState<Partial<Record<number, Narrator | 'error'>>>({})
  const requestedDetails = useRef(new Set<number>())
  const narratorDialog = useRef<HTMLElement>(null)

  const fetchNarratorDetails = useCallback((id: number) => {
    if (requestedDetails.current.has(id)) return
    requestedDetails.current.add(id)
    const fromKnowledgeGraph = id >= KG_NARRATOR_OFFSET
    const path = fromKnowledgeGraph
      ? `/knowledge-graph/rawis/${id - KG_NARRATOR_OFFSET}/`
      : `/narrators/${id}/`
    void fetchJson(path)
      .then(raw => {
        const detail = fromKnowledgeGraph ? mapKnowledgeGraphNarrator(id, raw) : mapNarrator(raw)
        setNarratorDetails(current => ({ ...current, [id]: detail }))
      })
      .catch(() => {
        requestedDetails.current.delete(id)
        setNarratorDetails(current => ({ ...current, [id]: 'error' }))
      })
  }, [])

  const hadithRequest = useRef(0)
  const localChain = useRef<{ narrators?: unknown; edges?: unknown }>({})
  const localSelection = useRef<{ index: number; narrator: number | null; edge: number | null } | null>(null)

  const applyChain = (payload: { narrators?: unknown; edges?: unknown }) => {
    const mapped = unwrapList<NarratorRecord>(payload?.narrators).map(mapNarrator)
    const chainEdges = unwrapList<EdgeRecord>(payload?.edges)
    const grouped = groupChains(chainEdges)
    setNarrators(mapped)
    setChains(grouped)
    setChainIndex(0)
    const ordered = orderChain(grouped[0] ?? [])
    setSelectedId(ordered[Math.floor(ordered.length / 2)] ?? mapped[0]?.id ?? null)
    setSelectedEdge(null)
  }

  useEffect(() => {
    setSourceCandidates([])
    setHasMoreSources(false)
    setSourceStatus('loading')
    setSourceError('')
    if (!sourceHadithNumber) return
    const controller = new AbortController()
    void fetchJson(`/hadiths/${encodeURIComponent(sourceHadithNumber)}/sources/?page=${sourcePage}&page_size=10`, {
      signal: controller.signal,
    }).then(data => {
      if (controller.signal.aborted) return
      setSourceCandidates(unwrapList<SourceCandidate>(data))
      setHasMoreSources(Boolean(data.next))
      setSourceStatus(data.status ?? 'available')
    }).catch(() => {
      if (!controller.signal.aborted) setSourceStatus('unavailable')
    })
    return () => controller.abort()
  }, [sourceHadithNumber, sourcePage])

  const previewSource = async (candidate: SourceCandidate) => {
    if (!sourceHadithNumber || previewPending) return
    setPreviewPending(true)
    const request = ++hadithRequest.current
    setSourceError('')
    try {
      const data = await fetchJson(
        `/hadiths/${encodeURIComponent(sourceHadithNumber ?? '')}/source-routes/?source_key=${encodeURIComponent(candidate.right_key)}`,
      )
      if (request !== hadithRequest.current) return
      const routes: KnowledgeGraphChain[] = data.routes ?? []
      if (!routes.length) {
        setSourceError('This external source has no stored routes.')
        return
      }
      if (!previewingSource) localSelection.current = { index: chainIndex, narrator: selectedId, edge: selectedEdge }
      setPreviewingSource(candidate)
      setKgChains(routes)
      setSelectedKgSanadId(routes[0].sanad_id)
      applyChain(routes[0])
    } catch {
      if (request === hadithRequest.current) {
        setSourceError('External chain unavailable or its text does not corroborate this proposal.')
      }
    } finally {
      if (request === hadithRequest.current) setPreviewPending(false)
    }
  }

  const loadKnowledgeGraphHadith = async (hadithId: number) => {
    const request = ++hadithRequest.current
    setLoadError('')
    setPreviewPending(false)
    try {
      const data = await fetchJson(`/knowledge-graph/hadiths/${hadithId}/`)
      if (request !== hadithRequest.current) return
      const paths: KnowledgeGraphChain[] = data.visual_isnad_chains ?? []
      const firstChain = paths.find(chain => chain.grade === 'صحيح') ?? paths[0]
      if (!firstChain) {
        setLoadError('No Isnad chains found for this Hadith.')
        return
      }

      setPreviewingSource(null)
      setKgChains(paths)
      setSelectedKgSanadId(firstChain.sanad_id)
      setKgHadithId(hadithId)
      setHadithReaderOpen(false)
      applyChain(firstChain)
      setSelectedHadithId(null)
      setSelectedHadithNumber(String(data.noInBook ?? hadithId))
      setCurrentHadith({
        id: hadithId,
        hadith_number: String(data.noInBook ?? hadithId),
        book_title: `Knowledge Graph Collection ${data.bookId}`,
        arabic_matn: data.matnClean || data.nass || '',
        arabic_full: data.nass || '',
        grade: data.hukm || firstChain.grade || '',
      })
    } catch {
      if (request === hadithRequest.current) setLoadError('Could not load Knowledge Graph Hadith.')
    }
  }

  const loadBookHadiths = async (bookNumber: number) => {
    const hadiths: HadithRecord[] = []
    let page = 1
    let payload
    do {
      payload = await fetchJson(`/hadiths/?book=${bookNumber}&compact=1&page_size=400&page=${page}`)
      hadiths.push(...unwrapList<HadithRecord>(payload))
      page += 1
    } while (payload?.next)
    setHadithsByBook((current) => ({ ...current, [bookNumber]: hadiths }))
    return hadiths
  }

  const selectHadith = async (hadith: Pick<HadithRecord, 'id' | 'hadith_number'>, bookNumber?: number) => {
    const request = ++hadithRequest.current
    setHadithReaderOpen(false)
    setPreviewPending(false)
    localSelection.current = null
    setCatalogOpen(false)
    setKgHadithId(null)
    setPreviewingSource(null)
    setSourcePage(1)
    setSourceError('')
    setSourceCandidates([])
    setHasMoreSources(false)
    setKgChains([])
    setSelectedKgSanadId(null)
    setSelectedHadithId(hadith.id)
    setSelectedHadithNumber(hadith.hadith_number)
    setCurrentHadith(null)
    applyChain({})
    if (bookNumber != null) setExpandedBook(bookNumber)
    try {
      const detail = await fetchJson(`/hadiths/${encodeURIComponent(hadith.hadith_number)}/?chain=1`)
      if (request !== hadithRequest.current) return
      setCurrentHadith(detail)
      localChain.current = detail
      applyChain(detail)
      setLoadError('')
    } catch (error) {
      if (request !== hadithRequest.current) return
      console.error('Hadith detail fetch error:', error)
      setLoadError('Could not load this hadith.')
    }
  }

  const toggleBook = async (bookNumber: number) => {
    if (expandedBook === bookNumber) {
      setExpandedBook(null)
      return
    }
    setExpandedBook(bookNumber)
    if (!hadithsByBook[bookNumber]) {
      try {
        await loadBookHadiths(bookNumber)
      } catch (error) {
        console.error('Book list fetch error:', error)
      }
    }
  }

  useEffect(() => {
    const loadCatalog = async () => {
      try {
        const boot = await fetchJson('/hadiths/bootstrap/')
        const bookList = Array.isArray(boot?.books) ? boot.books as BookRecord[] : []
        setBooks(bookList)
        const firstBook = bookList[0]?.number ?? 1
        setExpandedBook(firstBook)
        if (boot?.hadith) {
          setCurrentHadith(boot.hadith)
          setSelectedHadithId(boot.hadith.id)
          setSelectedHadithNumber(boot.hadith.hadith_number)
          localChain.current = {
            narrators: boot.narrators || boot.hadith.narrators,
            edges: boot.edges || boot.hadith.edges,
          }
          applyChain(localChain.current)
          setLoadError('')
        }
        setIsLoading(false)
        void loadBookHadiths(firstBook).catch((error) => {
          console.error('Book list fetch error:', error)
        })
      } catch (error) {
        console.error('API Fetch Error:', error)
        setLoadError(
          API_ORIGIN
            ? 'Could not reach the API. Please try again later.'
            : 'Could not reach the API. Start Django on port 8000.',
        )
        setIsLoading(false)
      }
    }
    loadCatalog()
  }, [])

  useEffect(() => {
    void fetchJson('/auth/me/')
      .then((payload) => setEditor(payload))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!query.trim()) {
      setSearchHits([])
      return
    }
    const handle = window.setTimeout(async () => {
      try {
        const payload = await fetchJson(`/narrators/?search=${encodeURIComponent(query.trim())}&page_size=12`)
        setSearchHits(unwrapList<NarratorRecord>(payload).map(mapNarrator))
      } catch {
        setSearchHits(
          narrators.filter((item) =>
            `${item.name} ${item.arabic} ${item.location}`.toLowerCase().includes(query.toLowerCase()),
          ),
        )
      }
    }, 250)
    return () => window.clearTimeout(handle)
  }, [query, narrators])

  useEffect(() => {
    setEditingProfile(false)
    setProfileSaveError('')
  }, [selectedId])

  useEffect(() => {
    if (!editor.can_edit_biographies) setEditingProfile(false)
  }, [editor.can_edit_biographies])

  useEffect(() => {
    if (!hadithReaderOpen && !inspectedNarrator && !catalogOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      if (inspectedNarrator) setInspectedNarrator(null)
      else if (hadithReaderOpen) setHadithReaderOpen(false)
      else setCatalogOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [hadithReaderOpen, inspectedNarrator, catalogOpen])

  useEffect(() => {
    const canvas = graphCanvasRef.current
    if (!canvas) return
    const pinch = { distance: 0, startZoom: 100 }
    const pan = { x: 0, y: 0, left: 0, top: 0, active: false }

    const touchDistance = (event: TouchEvent) => {
      const [first, second] = [event.touches[0], event.touches[1]]
      return Math.hypot(first.clientX - second.clientX, first.clientY - second.clientY)
    }

    const onTouchStart = (event: TouchEvent) => {
      if (event.touches.length === 2) {
        pinch.distance = touchDistance(event)
        pinch.startZoom = zoomRef.current
        pan.active = false
        event.preventDefault()
        return
      }
      if (event.touches.length === 1) {
        pan.active = true
        pan.x = event.touches[0].clientX
        pan.y = event.touches[0].clientY
        pan.left = canvas.scrollLeft
        pan.top = canvas.scrollTop
      }
    }

    const onTouchMove = (event: TouchEvent) => {
      if (event.touches.length === 2 && pinch.distance) {
        event.preventDefault()
        const next = Math.round(pinch.startZoom * (touchDistance(event) / pinch.distance))
        setZoom(Math.min(180, Math.max(70, next)))
        return
      }
      if (event.touches.length === 1 && pan.active) {
        canvas.scrollLeft = pan.left - (event.touches[0].clientX - pan.x)
        canvas.scrollTop = pan.top - (event.touches[0].clientY - pan.y)
      }
    }

    const onTouchEnd = () => {
      pinch.distance = 0
      pan.active = false
    }

    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return
      event.preventDefault()
      setZoom((current) => Math.min(180, Math.max(70, current + (event.deltaY > 0 ? -8 : 8))))
    }

    canvas.addEventListener('touchstart', onTouchStart, { passive: false })
    canvas.addEventListener('touchmove', onTouchMove, { passive: false })
    canvas.addEventListener('touchend', onTouchEnd)
    canvas.addEventListener('touchcancel', onTouchEnd)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      canvas.removeEventListener('touchstart', onTouchStart)
      canvas.removeEventListener('touchmove', onTouchMove)
      canvas.removeEventListener('touchend', onTouchEnd)
      canvas.removeEventListener('touchcancel', onTouchEnd)
      canvas.removeEventListener('wheel', onWheel)
    }
  }, [])

  const edges = chains[chainIndex] ?? []
  const chainIds = useMemo(() => {
    if ((kgHadithId !== null || previewingSource) && !edges.length) return narrators.map(person => person.id)
    return orderChain(edges)
  }, [edges, kgHadithId, narrators, previewingSource])
  const totalHadiths = books.reduce((sum, book) => sum + book.count, 0)
  const selectedBookNumber = Number(currentHadith?.in_book_reference?.match(/Book\s+(\d+)/i)?.[1] || expandedBook || 1)
  const activeBook = books.find((book) => book.number === selectedBookNumber)
  const chainNarrators = useMemo(
    () => chainIds
      .map((id) => narrators.find((item) => item.id === id))
      .filter((item): item is Narrator => Boolean(item)),
    [chainIds, narrators],
  )
  const chainLayout = useMemo(() => layoutChain(chainNarrators), [chainNarrators])
  const positions = chainLayout.positions
  const graphScale = zoom / 100

  useEffect(() => {
    graphCenteredRef.current = false
  }, [selectedHadithId, chainLayout.height])

  useEffect(() => {
    const canvas = graphCanvasRef.current
    if (!canvas) return

    const centerOnProphet = () => {
      const prophet = chainLayout.positions[0]
      if (!prophet) return
      const scale = zoomRef.current / 100
      canvas.scrollLeft = (prophet.x + 105) * scale - canvas.clientWidth / 2
      canvas.scrollTop = Math.max(0, prophet.y * scale - 12)
    }

    const frame = window.requestAnimationFrame(centerOnProphet)
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      if (graphCenteredRef.current) return
      graphCenteredRef.current = true
      centerOnProphet()
    }, { threshold: 0.2 })
    observer.observe(canvas)
    return () => {
      window.cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [chainLayout, selectedHadithId])
  const selectChain = (index: number) => {
    setChainIndex(index)
    const ordered = orderChain(chains[index] ?? [])
    setSelectedId(ordered[Math.floor(ordered.length / 2)] ?? null)
    setSelectedEdge(null)
  }
  const selectedSummary = narrators.find((item) => item.id === selectedId) ?? chainNarrators[0]
  const selectedDetail = selectedSummary && narratorDetails[selectedSummary.id]
  const selected = selectedDetail && selectedDetail !== 'error' ? selectedDetail : selectedSummary
  const inspectedDetail = inspectedNarrator && narratorDetails[inspectedNarrator.id]
  const inspected = inspectedDetail && inspectedDetail !== 'error' ? inspectedDetail : inspectedNarrator
  const selectedProfileId = selected?.id
  const inspectedProfileId = inspected?.id

  useEffect(() => {
    if (selectedProfileId != null) fetchNarratorDetails(selectedProfileId)
  }, [fetchNarratorDetails, selectedProfileId])

  useEffect(() => {
    if (inspectedProfileId == null) return
    fetchNarratorDetails(inspectedProfileId)
    if (narratorDialog.current) {
      narratorDialog.current.scrollTop = 0
      narratorDialog.current.focus()
    }
  }, [fetchNarratorDetails, inspectedProfileId])

  const retryNarratorDetails = (id: number) => {
    setNarratorDetails(current => ({ ...current, [id]: undefined }))
    fetchNarratorDetails(id)
  }
  const madarId = chainNarrators[Math.floor(chainNarrators.length / 2)]?.id

  const startEditingProfile = () => {
    if (!selectedDetail || selectedDetail === 'error' || !selected || selected.id >= KG_NARRATOR_OFFSET) return
    setProfileDraft(draftFromNarrator(selected))
    setProfileSaveError('')
    setEditingProfile(true)
  }

  const updateDraft = (field: keyof ProfileDraft, value: string) => {
    setProfileDraft((current) => ({ ...current, [field]: value }))
  }

  const saveProfile = async () => {
    if (!selected || selected.id >= KG_NARRATOR_OFFSET) return
    const { id } = selected
    const original = draftFromNarrator(selected)
    const changedFields = Object.fromEntries(
      (Object.keys(profileDraft) as (keyof ProfileDraft)[])
        .filter(field => profileDraft[field] !== original[field])
        .map(field => [field, profileDraft[field]]),
    )
    if (!Object.keys(changedFields).length) {
      setEditingProfile(false)
      return
    }
    setProfileSaving(true)
    setProfileSaveError('')
    try {
      const raw = await fetchJson(`/narrators/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(changedFields),
      })
      const mapped = mapNarrator({
        ...raw,
        teachers: selected.record.teachers,
        students: selected.record.students,
        transmission_students: selected.record.transmission_students,
      })
      setNarratorDetails(current => ({ ...current, [id]: mapped }))
      setNarrators((current) => {
        const remaining = current.filter((item) => item.id !== id)
        return [...remaining, mapped]
      })
      setEditingProfile(false)
    } catch {
      setProfileSaveError('Could not save this profile. Sign in as an editor first.')
    } finally {
      setProfileSaving(false)
    }
  }

  const selectNarrator = (id: number) => {
    setSelectedId(id)
    setCatalogOpen(false)
    setPanelOpen(true)
  }

  const openNarratorPage = (person: Narrator) => {
    setQuery('')
    setSearchHits([])
    setInspectedNarrator(person)
  }

  const openRelatedNarrator = (reference: NarratorReference) => {
    openNarratorPage(mapNarrator(reference))
  }

  const edgeByPair = (teacherId: number, studentId: number) =>
    edges.find((edge) => edge.teacher === teacherId && edge.student === studentId)

  const selectedEdgeRecord = edges.find((edge) => edge.id === selectedEdge)
  const englishTitle = currentHadith
    ? (currentHadith.chapter_title || currentHadith.topic || `Hadith ${currentHadith.hadith_number}`).replace(/^Chapter:\s*/i, '')
    : isLoading
      ? 'Loading Hadiths...'
      : 'Hadith not loaded'
  const arabicTitle = (currentHadith?.chapter_title_arabic || '').trim()
  const englishMatn = currentHadith?.english_matn || ''
  const arabicText = (currentHadith?.arabic_matn || '').replace(/^["«\s]+/, '').trim()
  const arabicIsnad = (currentHadith?.arabic_isnad || '').trim()
  const arabicFull = (
    currentHadith?.arabic_full
    || [arabicIsnad, arabicText].filter(Boolean).join('\n\n')
  ).trim()
  const englishPreview = previewText(englishMatn, 28)
  const arabicPreview = previewText(arabicText, 18)
  const hadithIsLong = englishPreview.truncated || arabicPreview.truncated

  const listPreview = (hadith: HadithRecord) => {
    if (hadith.preview) return hadith.preview
    const narrated = hadith.english_matn?.match(/^Narrated\s+([^:]+):/i)?.[1]
    if (narrated) return `Narrated ${narrated.trim()}`
    return `Hadith ${hadith.hadith_number}`
  }

  const nodeLocation = (value: string) => (value.length > 18 ? `${value.slice(0, 17)}…` : value)

  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="/"
          aria-label="Visual Isnad home"
          onClick={(event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
            event.preventDefault()
            onHome()
          }}
        >
          <span className="brand-mark"><span>سند</span></span>
          <span className="brand-copy">
            <strong>Visual Isnad</strong>
            <small>Explorer · Bukhari</small>
          </span>
        </a>

        <div className="search-wrap">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search narrators…"
            aria-label="Search narrators"
          />
          <Icon name="search" size={18} />
          {query && (
            <div className="search-results">
              {searchHits.length ? searchHits.map((item) => (
                <button key={item.id} onClick={() => openNarratorPage(item)}>
                  <span className="result-avatar">{item.initials}</span>
                  <span><strong>{item.name}</strong><small>{item.location} · {item.era}</small></span>
                  <Icon name="arrow" size={15} />
                </button>
              )) : <p>No narrators found</p>}
            </div>
          )}
        </div>

        <nav className="top-actions" aria-label="Editor access">
          <div className="auth-wrap">
            <button
              className="editor-button"
              aria-label={editor.authenticated ? `Signed in as ${editor.username}` : 'Editor sign in'}
              onClick={() => {
                setAuthOpen((open) => !open)
                setLoginError('')
              }}
            >
              {editor.authenticated ? editor.username : 'Editor'}
            </button>
            {authOpen && (
              <div className="auth-menu">
                {editor.authenticated ? (
                  <>
                    <p><strong>{editor.username}</strong><small>{editor.can_edit_biographies ? 'Can edit narrator profiles' : 'Signed in'}</small></p>
                    <button
                      type="button"
                      onClick={async () => {
                        const payload = await fetchJson('/auth/logout/', { method: 'POST' })
                        storeEditorToken('')
                        setEditor(payload)
                        setEditingProfile(false)
                        setAuthOpen(false)
                      }}
                    >
                      Sign out
                    </button>
                  </>
                ) : (
                  <form
                    onSubmit={async (event) => {
                      event.preventDefault()
                      setLoginBusy(true)
                      setLoginError('')
                      try {
                        await fetchJson('/auth/me/')
                        const payload = await fetchJson('/auth/login/', {
                          method: 'POST',
                          body: JSON.stringify({ username: loginUser, password: loginPassword }),
                        })
                        setEditor(payload)
                        setLoginPassword('')
                        setAuthOpen(false)
                      } catch (error) {
                        setLoginError(
                          error instanceof Error && error.message
                            ? error.message
                            : 'Staff username and password required.',
                        )
                      } finally {
                        setLoginBusy(false)
                      }
                    }}
                  >
                    <p><strong>Editor sign in</strong><small>Only staff can edit narrator profiles.</small></p>
                    <input
                      value={loginUser}
                      onChange={(event) => setLoginUser(event.target.value)}
                      placeholder="Username"
                      autoComplete="username"
                      aria-label="Username"
                    />
                    <input
                      type="password"
                      value={loginPassword}
                      onChange={(event) => setLoginPassword(event.target.value)}
                      placeholder="Password"
                      autoComplete="current-password"
                      aria-label="Password"
                    />
                    {loginError ? <small className="auth-error">{loginError}</small> : null}
                    <button type="submit" disabled={loginBusy}>{loginBusy ? 'Signing in…' : 'Sign in'}</button>
                  </form>
                )}
              </div>
            )}
          </div>
        </nav>
      </header>

      <div className="mobile-toolbar" aria-label="Mobile navigation">
        <button
          type="button"
          className={catalogOpen ? 'active' : ''}
          onClick={() => {
            setPanelOpen(false)
            setCatalogOpen((open) => !open)
          }}
        >
          <Icon name="book" />
          <span>Books &amp; hadiths</span>
        </button>
        <button
          type="button"
          className={panelOpen ? 'active' : ''}
          onClick={() => {
            setCatalogOpen(false)
            setPanelOpen(true)
          }}
        >
          <Icon name="user" />
          <span>Narrator</span>
        </button>
      </div>

      <div className="workspace">
        <aside className={`sidebar ${catalogOpen ? 'open' : ''}`}>
          <div className="sidebar-heading">
            <p>Collection</p>
            <button
              className="sidebar-close"
              type="button"
              aria-label="Close books"
              onClick={() => setCatalogOpen(false)}
            >
              <Icon name="close" />
            </button>
          </div>
          <button className="collection-select">
            <span className="collection-icon"><Icon name="book" /></span>
            <span><strong>Sahih al-Bukhari</strong><small>{totalHadiths.toLocaleString()} narrations</small></span>
            <Icon name="chevron" size={16} />
          </button>

          <div className="chapter-label"><span>Books</span><span>{books.length || '—'}</span></div>
          <div className="book-nav">
            {books.map((book) => {
              const open = expandedBook === book.number
              const items = hadithsByBook[book.number]
              return (
                <div key={book.number} className={`book-group ${open ? 'open' : ''}`}>
                  <button
                    className={`chapter-button ${open ? 'active' : ''}`}
                    onClick={() => toggleBook(book.number)}
                    aria-expanded={open}
                  >
                    <span className="chapter-number">{String(book.number).padStart(2, '0')}</span>
                    <span>
                      <strong>{book.title}</strong>
                      <small>{book.title_arabic}</small>
                    </span>
                    <em>{book.count}</em>
          </button>
                  {open && (
          <div className="hadith-list">
                      {items?.map((hadith) => (
                        <button
                          key={hadith.id}
                          className={hadith.id === selectedHadithId ? 'active' : ''}
                          onClick={() => selectHadith(hadith, book.number)}
                        >
                 <span>{hadith.hadith_number}</span>
                          <div>
                            <strong>{listPreview(hadith)}</strong>
                            <small>{hadith.in_book_reference || `Book ${book.number}`}</small>
                          </div>
               </button>
            ))}
                      {!items && <p className="book-loading">Loading hadiths…</p>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </aside>

        <main className="main-content">
          <section className="hadith-header">
            <div className="breadcrumb">
              <span>{kgHadithId === null ? 'Sahih al-Bukhari' : 'Knowledge Graph'}</span><b>/</b><span>{kgHadithId !== null ? currentHadith?.book_title : activeBook?.title || currentHadith?.chapter_title?.replace(/^Chapter:\s*/i, '') || 'Collection'}</span><b>/</b><strong>Hadith {currentHadith?.hadith_number || '—'}</strong>
            </div>
            <div className="hadith-title-row">
              <div className="hadith-title-copy">
                <p className="eyebrow">{currentHadith?.in_book_reference || 'DATABASE RECORD'} · {currentHadith?.hadith_number || '—'}</p>
                <h1>{loadError || englishTitle}</h1>
                {arabicTitle && !loadError ? (
                  <p className="hadith-arabic-title" dir="rtl" lang="ar">{arabicTitle}</p>
                ) : null}
              </div>
            </div>

            <div className="hadith-text">
              <div className="quote-rule"><span>{currentHadith?.hadith_number || '1'}</span></div>
              <div className="translation">
                <p>
                  {isLoading
                    ? 'Loading hadiths...'
                    : (hadithIsLong ? englishPreview.preview : englishMatn) || 'English translation is not available for this record.'}
                </p>
                <button type="button" onClick={() => setHadithReaderOpen(true)} disabled={!currentHadith || isLoading}>
                  Read full hadith <Icon name="arrow" size={15} />
                </button>
              </div>
              <div className="arabic-block" dir="rtl">
                <p className="arabic-text" lang="ar">
                  {isLoading ? 'Loading...' : (hadithIsLong ? arabicPreview.preview : arabicText)}
                </p>

                <button
                  className="arabic-read-button"
                  type="button"
                  lang="ar"
                  dir="rtl"
                  onClick={() => setHadithReaderOpen(true)}
                  disabled={!currentHadith || isLoading}
                >
                  قراءة الحديث كاملاً <span>←</span>
                </button>
              </div>
            </div>
          </section>

          <section className="visualizer">
            <div className="visualizer-toolbar">
              <div>
                <p className="eyebrow">{kgHadithId !== null || previewingSource
                  ? 'EXTERNAL · KNOWLEDGE GRAPH · UNREVIEWED'
                  : 'VISUAL ISNAD TRANSMISSION PATH'}</p>
                <h2>Chain of narration <span>{chainNarrators.length} nodes · {edges.length} transmissions</span></h2>
                {chains.length > 1 && (
                  <label>
                    Isnād{' '}
                    <select value={chainIndex} onChange={(event) => selectChain(Number(event.target.value))}>
                      {chains.map((chain, index) => (
                        <option key={chain[0].id} value={index}>Chain {index + 1} of {chains.length}</option>
                      ))}
                    </select>
                  </label>
                )}
                {!isLoading && currentHadith && !chainNarrators.length && <p>No chain was extracted for this hadith.</p>}
              </div>
              <button
                className="knowledge-graph-load"
                type="button"
                disabled={isLoading}
                onClick={() => void loadKnowledgeGraphHadith(17154)}
              >
                Load Knowledge Graph Hadith 17154
              </button>
              {(kgHadithId !== null || previewingSource) && (
                <label>
                  Knowledge Graph isnād{' '}
                  <select value={selectedKgSanadId ?? ''} onChange={(event) => {
                    const path = kgChains.find(chain => chain.sanad_id === Number(event.target.value))
                    if (!path) return
                    setSelectedKgSanadId(path.sanad_id)
                    applyChain(path)
                  }}>
                    {kgChains.map(path => (
                      <option key={path.sanad_id} value={path.sanad_id}>
                        Chain {path.sanad_id} · {path.grade || 'Unrated'} · {path.narrators.length} narrators
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>

            {sourceError && <p role="status">{sourceError}</p>}
            {previewingSource && currentHadith && (
              <button className="knowledge-graph-load" type="button" onClick={() => {
                hadithRequest.current += 1
                setPreviewingSource(null)
                setKgChains([])
                setSelectedKgSanadId(null)
                setSourceError('')
                setPreviewPending(false)
                applyChain(localChain.current)
                if (localSelection.current) {
                  setChainIndex(localSelection.current.index)
                  setSelectedId(localSelection.current.narrator)
                  setSelectedEdge(localSelection.current.edge)
                  localSelection.current = null
                }
              }}>
                Restore Visual Isnad chains
              </button>
            )}
            {sourceHadithNumber && (
              <details className="source-proposals">
                <summary>External source proposals</summary>
                {sourceStatus === 'loading' && <p role="status">Loading source proposals…</p>}
                {sourceStatus === 'not_configured' && <p>External source proposals have not been configured.</p>}
                {sourceStatus === 'stale' && <p>The local hadith text has changed. Rebuild the source crosswalk.</p>}
                {sourceStatus === 'not_applicable' && <p>Source matching is available for Sahih al-Bukhari.</p>}
                {sourceStatus === 'unavailable' && <p role="status">External source proposals are unavailable.</p>}
                {sourceStatus === 'available' && !sourceCandidates.length && <p>No matching source proposals for this hadith.</p>}
                {previewPending && <p role="status">Loading external routes…</p>}
                {sourceCandidates.length > 0 && <p>These proposals are unreviewed. Text agreement cannot establish an equivalent transmission chain.</p>}
                <ul>
                  {sourceCandidates.map(candidate => (
                    <li key={candidate.right_key}>
                      <strong>{candidate.provider === 'hadith_kg' ? 'Knowledge Graph' : candidate.provider}</strong>
                      {' · '}{candidate.edition} · {candidate.reference || candidate.right_id}
                      {' · '}{candidate.confidence.replace(/_/g, ' ')}
                      <p>{candidate.reason}
                        {candidate.isnad_agreement === 'text_differs' && ' The recorded isnad text differs.'}
                      </p>
                      {candidate.can_preview_routes && (
                        <button className="knowledge-graph-load" type="button" disabled={previewPending} onClick={() => void previewSource(candidate)}>
                          Preview external chains
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                {sourcePage > 1 && <button type="button" onClick={() => setSourcePage(page => page - 1)}>Previous</button>}
                {hasMoreSources && <button type="button" onClick={() => setSourcePage(page => page + 1)}>Next</button>}
              </details>
            )}

            <div className="graph-legend-row">
              <div className="graph-legend">
                <span><i className="legend-path" /> Selected isnad</span>
                <span><i className="legend-madar" /> Common link (Madar)</span>
                <span><i className="legend-direction" /> Direction of transmission</span>
              </div>
              <div className="graph-actions">
                <button className={tracePath ? 'active' : ''} onClick={() => setTracePath(!tracePath)}><Icon name="branch" size={14} /> Trace path</button>
                <button className={highlightMadar ? 'active gold' : ''} onClick={() => setHighlightMadar(!highlightMadar)}><span className="radar-dot" /> Highlight Madar</button>
              </div>
              </div>

            <div className="graph-canvas" ref={graphCanvasRef}>
              <div
                className="network-stage"
                style={{ width: 900 * graphScale, height: chainLayout.height * graphScale }}
              >
                <svg
                  className="network-svg"
                  width={900 * graphScale}
                  height={chainLayout.height * graphScale}
                  viewBox={`0 0 900 ${chainLayout.height}`}
                  role="img"
                  aria-label="Directed chain of narration"
                >
                  <defs>
                    <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto">
                      <path d="M0,0 L0,6 L6,3 z" fill={tracePath ? '#2b6a5e' : '#8ca49e'} />
                    </marker>
                    <filter id="node-shadow" x="-20%" y="-20%" width="140%" height="150%">
                      <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#243c37" floodOpacity=".08" />
                    </filter>
                  </defs>

                  <g className="tier-bands">
                    {chainLayout.bands.map((band) => (
                      <g key={band.tier}>
                        <rect
                          x="22"
                          y={band.top}
                          width="856"
                          height={band.height}
                          rx="11"
                          className={band.tier === 'prophet' ? 'tier-prophet' : undefined}
                        />
                        <text x="42" y={band.top + 26}>{TIER_LABELS[band.tier]}</text>
                      </g>
                    ))}
                  </g>

                  <g className={`transmission-edges ${tracePath ? 'tracing' : ''}`}>
                    {chainNarrators.slice(0, -1).map((teacher, index) => {
                      const student = chainNarrators[index + 1]
                      const from = positions[index]
                      const to = positions[index + 1]
                      const edge = edgeByPair(teacher.id, student.id)
                      if (!edge) return null
                      const startX = from.x + 105
                      const startY = from.y + 58
                      const endX = to.x + 105
                      const endY = to.y
                      const path = `M${startX} ${startY} C${startX} ${(startY + endY) / 2}, ${endX} ${(startY + endY) / 2}, ${endX} ${endY}`
                      return (
                        <g
                          key={edge?.id ?? `${teacher.id}-${student.id}`}
                          onClick={() => setSelectedEdge(edge?.id ?? null)}
                          className={selectedEdge === edge?.id ? 'selected' : ''}
                        >
                          <path className="edge-hit" d={path} />
                          <path d={path} markerEnd="url(#arrowhead)" />
                          <text x={(startX + endX) / 2 + 8} y={(startY + endY) / 2}>{edge?.terminology || 'عن'}</text>
                        </g>
                      )
                    })}
                  </g>

                  {chainNarrators.map((narrator, index) => {
                    const position = positions[index]
                    const isMadar = narrator.id === madarId
                    return (
                      <g
                        key={narrator.id}
                        className={`svg-node ${selectedId === narrator.id ? 'selected' : ''} ${isMadar && highlightMadar ? 'madar' : ''}`}
                        transform={`translate(${position.x} ${position.y})`}
                        onClick={() => selectNarrator(narrator.id)}
                        role="button"
                        tabIndex={0}
                      >
                        <rect width="210" height="58" rx="10" filter="url(#node-shadow)" />
                        <circle cx="28" cy="29" r="18" />
                        <text className="initials" x="28" y="32" textAnchor="middle">{narrator.initials}</text>
                        <text className="node-name" x="56" y="22">{narrator.name.length > 22 ? `${narrator.name.slice(0, 21)}…` : narrator.name}</text>
                        <text className="node-meta" x="56" y="38">{narrator.died.split(',')[0]} · {nodeLocation(narrator.location)}</text>
                        <rect className="role-pill" x="148" y="10" width="52" height="15" rx="4" />
                        <text className="role-text" x="174" y="20" textAnchor="middle">{narrator.role}</text>
                        {isMadar && highlightMadar && <><circle className="pulse" cx="205" cy="5" r="7" /><text className="madar-mark" x="205" y="8" textAnchor="middle">M</text></>}
                      </g>
                    )
                  })}
                </svg>
              </div>

              {selectedEdgeRecord && (
                <div className="edge-evidence">
                  <div className="evidence-icon"><Icon name="branch" /></div>
                  <div>
                    <span>TRANSMISSION EVIDENCE</span>
                    <strong>
                      {narrators.find((item) => item.id === selectedEdgeRecord.teacher)?.name}
                      {' narrated to '}
                      {narrators.find((item) => item.id === selectedEdgeRecord.student)?.name}
                    </strong>
                    <small>Hadith {currentHadith?.hadith_number} · Terminology: {selectedEdgeRecord.terminology}</small>
                  </div>
                  <button onClick={() => setSelectedEdge(null)} aria-label="Close evidence"><Icon name="close" size={15} /></button>
                </div>
              )}

              <div className="graph-dock">
              <div className="zoom-controls">
                  <button onClick={() => setZoom(Math.min(180, zoom + 10))} aria-label="Zoom in"><Icon name="plus" /></button>
                <span>{zoom}%</span>
                  <button onClick={() => setZoom(Math.max(70, zoom - 10))} aria-label="Zoom out"><Icon name="minus" /></button>
              </div>
                <div className="graph-hint">Pinch or scroll to zoom · Drag to pan</div>
              </div>
            </div>
          </section>
        </main>

        {selected && <aside className={`detail-panel ${panelOpen ? 'open' : ''}`}>
          <div className="panel-top">
            <span>Narrator profile</span>
            <button onClick={() => setPanelOpen(false)} aria-label="Close profile"><Icon name="close" /></button>
          </div>
          {editingProfile ? (
            <form
              className="profile-edit"
              onSubmit={(event) => {
                event.preventDefault()
                void saveProfile()
              }}
            >
              <label>
                <span>English name</span>
                <input value={profileDraft.name} onChange={(event) => updateDraft('name', event.target.value)} />
              </label>
              <label>
                <span>Arabic name</span>
                <input dir="rtl" value={profileDraft.arabic_name} onChange={(event) => updateDraft('arabic_name', event.target.value)} />
              </label>
              <label>
                <span>Grade</span>
                <input value={profileDraft.grade} onChange={(event) => updateDraft('grade', event.target.value)} />
              </label>
              <label>
                <span>Generation</span>
                <input value={profileDraft.tabaqah} onChange={(event) => updateDraft('tabaqah', event.target.value)} />
              </label>
              <label>
                <span>Reliability</span>
                <input value={profileDraft.tawthiq} onChange={(event) => updateDraft('tawthiq', event.target.value)} />
              </label>
              <label>
                <span>Born</span>
                <input value={profileDraft.birth_display} onChange={(event) => updateDraft('birth_display', event.target.value)} placeholder="e.g. 194 AH" />
              </label>
              <label>
                <span>Birth place</span>
                <input value={profileDraft.birth_place} onChange={(event) => updateDraft('birth_place', event.target.value)} />
              </label>
              <label>
                <span>Died</span>
                <input value={profileDraft.death_display} onChange={(event) => updateDraft('death_display', event.target.value)} placeholder="e.g. 256 AH" />
              </label>
              <label>
                <span>Death place</span>
                <input value={profileDraft.death_place} onChange={(event) => updateDraft('death_place', event.target.value)} />
              </label>
              <label>
                <span>Region</span>
                <input value={profileDraft.region} onChange={(event) => updateDraft('region', event.target.value)} />
              </label>
              <label>
                <span>Biography</span>
                <textarea
                  className="profile-bio-editor"
                  value={profileDraft.biography}
                  onChange={(event) => updateDraft('biography', event.target.value)}
                  rows={7}
                  dir="auto"
                />
              </label>
              {profileSaveError ? <p className="profile-bio-error">{profileSaveError}</p> : null}
              <div className="profile-bio-actions">
                <button type="submit" disabled={profileSaving}>{profileSaving ? 'Saving…' : 'Save profile'}</button>
                <button type="button" onClick={() => setEditingProfile(false)} disabled={profileSaving}>Cancel</button>
              </div>
            </form>
          ) : (
            <>
          <div className="profile-intro">
            <span className="profile-avatar">{selected.initials}</span>
            {selected.arabic && <p className="profile-arabic" lang="ar" dir="rtl">{selected.arabic}</p>}
            <h2 dir="auto">{selected.name}</h2>
            <div className="profile-tags"><span>{selected.role}</span><span>{selected.grade}</span></div>
          </div>

          <NarratorProfile
            record={selected.record}
            status={selectedDetail === 'error' ? 'error' : selectedDetail ? 'loaded' : 'loading'}
            onOpen={openRelatedNarrator}
            onRetry={() => retryNarratorDetails(selected.id)}
          />
          {editor.can_edit_biographies && selected.id < KG_NARRATOR_OFFSET && selectedDetail && selectedDetail !== 'error' && (
            <div className="profile-section">
              <button type="button" onClick={startEditingProfile}>
                Edit profile <Icon name="arrow" size={15} />
              </button>
            </div>
          )}
            </>
          )}

          <div className="profile-section relationship-grid">
            <button>
              <small>Direct teachers</small>
              <strong>{edges.filter((edge) => edge.student === selected.id).length || '—'}</strong>
              <span>In this chain</span>
            </button>
            <button>
              <small>Direct students</small>
              <strong>{edges.filter((edge) => edge.teacher === selected.id).length || '—'}</strong>
              <span>In this chain</span>
            </button>
            <button>
              <small>Chain position</small>
              <strong>{Math.max(1, chainIds.indexOf(selected.id) + 1)} / {chainIds.length || 1}</strong>
              <span>This narration</span>
            </button>
          </div>
        </aside>}

        {(catalogOpen || (panelOpen && Boolean(selected))) && (
          <button
            type="button"
            className="mobile-overlay"
            aria-label={catalogOpen ? 'Close books' : 'Close narrator profile'}
            onClick={() => {
              setCatalogOpen(false)
              if (window.matchMedia('(max-width: 1100px)').matches) setPanelOpen(false)
            }}
          />
        )}

        {!panelOpen && selected && (
          <button className="reopen-panel" type="button" onClick={() => setPanelOpen(true)}>
            <Icon name="user" /> Narrator profile
          </button>
        )}
      </div>

      {inspected && (
        <div className="hadith-reader" role="dialog" aria-modal="true" aria-labelledby="narrator-reader-title">
          <button
            type="button"
            className="hadith-reader-backdrop"
            aria-label="Close narrator profile"
            onClick={() => setInspectedNarrator(null)}
          />
          <article className="hadith-reader-page narrator-reader-page" ref={narratorDialog} tabIndex={-1}>
            <header className="hadith-reader-top">
              <div className="narrator-reader-intro">
                <span className="profile-avatar">{inspected.initials}</span>
                <p className="eyebrow">Narrator</p>
                {inspected.arabic && <p className="profile-arabic" lang="ar" dir="rtl">{inspected.arabic}</p>}
                <h2 id="narrator-reader-title" dir="auto">{inspected.name}</h2>
                <div className="profile-tags">
                  <span>{inspected.role}</span>
                  <span>{inspected.grade}</span>
                </div>
              </div>
              <button type="button" onClick={() => setInspectedNarrator(null)} aria-label="Close">
                <Icon name="close" />
              </button>
            </header>
            <NarratorProfile
              key={inspected.id}
              record={inspected.record}
              status={inspectedDetail === 'error' ? 'error' : inspectedDetail ? 'loaded' : 'loading'}
              onOpen={openRelatedNarrator}
              onRetry={() => retryNarratorDetails(inspected.id)}
            />
          </article>
        </div>
      )}

      {hadithReaderOpen && currentHadith && (
        <div className="hadith-reader" role="dialog" aria-modal="true" aria-labelledby="hadith-reader-title">
          <button
            type="button"
            className="hadith-reader-backdrop"
            aria-label="Close full hadith"
            onClick={() => setHadithReaderOpen(false)}
          />
          <article className="hadith-reader-page">
            <header className="hadith-reader-top">
              <div>
                <p className="eyebrow">Sahih al-Bukhari</p>
                <h2 id="hadith-reader-title">{englishTitle}</h2>
                {arabicTitle ? <p className="hadith-arabic-title" dir="rtl" lang="ar">{arabicTitle}</p> : null}
              </div>
              <button type="button" onClick={() => setHadithReaderOpen(false)} aria-label="Close">
                <Icon name="close" />
              </button>
            </header>
            <dl className="hadith-reader-meta">
              <div><dt>Book</dt><dd>{activeBook ? `${activeBook.number}. ${activeBook.title}` : (currentHadith.book_title || 'Sahih al-Bukhari')}</dd></div>
              <div><dt>Reference</dt><dd>{currentHadith.in_book_reference || `Hadith ${currentHadith.hadith_number}`}</dd></div>
              <div><dt>Hadith no.</dt><dd>{currentHadith.hadith_number}</dd></div>
              {currentHadith.grade ? <div><dt>Grade</dt><dd>{currentHadith.grade}</dd></div> : null}
            </dl>
            <div className="hadith-reader-body">
              {arabicFull ? (
                <section>
                  <h3>Arabic</h3>
                  <p className="arabic-text" lang="ar" dir="rtl">{arabicFull}</p>
                </section>
              ) : null}
              <section>
                <h3>English</h3>
                <p>{englishMatn || 'English translation is not available for this record.'}</p>
              </section>
            </div>
          </article>
        </div>
      )}
    </div>
  )
}

function isExplorerPath(pathname: string) {
  const path = pathname.replace(/\/+$/, '') || '/'
  return path === '/explore' || path === '/explorer'
}

function App() {
  const [path, setPath] = useState(() => window.location.pathname)

  useEffect(() => {
    const sync = () => setPath(window.location.pathname)
    window.addEventListener('popstate', sync)
    return () => window.removeEventListener('popstate', sync)
  }, [])

  const navigate = (to: string) => {
    if (window.location.pathname !== to) {
      window.history.pushState({}, '', to)
    }
    setPath(to)
    window.scrollTo(0, 0)
  }

  if (isExplorerPath(path)) {
    return <Explorer onHome={() => navigate('/')} />
  }

  return <Landing onExplore={() => navigate('/explore')} />
}

export default App
