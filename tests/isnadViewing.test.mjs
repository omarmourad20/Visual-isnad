import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'
import { groupChains } from '../src/transmissionPaths.ts'

let server
let IsnadViewer
before(async () => {
  server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, ws: false } })
  ;({ IsnadViewer } = await server.ssrLoadModule('/src/App.tsx'))
})
after(async () => { await server?.close() })

const narrators = [1, 2, 3, 30001].map(id => ({
  id, initials: 'N', name: `Narrator ${id}`, arabic: 'راوٍ',
  role: 'Narrator', died: '', era: '', location: '', record: {},
}))
const edge = (id, student, teacher, chain_index) => ({ sequence: id, id, student, teacher, chain_index, terminology: 'عن' })
const evidence = { edge_ids: [1, 2], status: 'reviewed', source_url: 'https://sunnah.com/bukhari:15', note: 'First route' }
const segment = { ...evidence, edge_ids: [3], status: 'legacy_segment', note: 'Other route is incomplete' }
const routes = groupChains([edge(1, 30001, 2), edge(2, 2, 1), edge(3, 30001, 3)], [evidence, segment])

function render(chains, extra = {}) {
  return renderToStaticMarkup(createElement(IsnadViewer, {
    chains, chainIndex: 0, narrators, selectedId: null,
    hadithNumber: '15', onSelectChain() {}, onSelectNarrator() {},
    ...extra,
  }))
}
const renderedEdges = html => [...html.matchAll(/data-edge-id="(\d+)"/g)].map(match => Number(match[1]))

test('single mode renders the chosen route and only its original edges', () => {
  const first = render(routes)
  const second = render(routes, { chainIndex: 1 })
  assert.deepEqual(renderedEdges(first), [2, 1])
  assert.deepEqual(renderedEdges(second), [3])
  assert.match(first, /Source reviewed/)
  assert.match(second, /Incomplete route/)
  for (const html of [first, second]) {
    assert.equal((html.match(/class="network-svg"/g) ?? []).length, 1)
    assert.doesNotMatch(html, /All isnads|Single isnad|Isnad viewing mode/)
    assert.match(html, /aria-label="Select isnad"/)
    assert.match(html, /lang="ar" dir="rtl">راوٍ/)
    assert.match(html, /tabindex="0"/)
    assert.doesNotMatch(html, /Highlight Madar|madar-mark|svg-node madar/)
  }
  assert.match(second, /Other route is incomplete/)
  assert.match(second, /href="https:\/\/sunnah.com\/bukhari:15"/)
})

test('one route needs no selector, and connected recorded evidence is visible by default', () => {
  const html = render(routes.slice(0, 1))
  assert.doesNotMatch(html, /All isnads|Select isnad/)
  const isolated = groupChains([edge(4, 30001, 2), edge(5, 2, 1)])
  const unresolved = render(isolated)
  assert.match(unresolved, /Showing recorded transmissions/)
  assert.match(unresolved, /aria-label="Recorded segment 1: unverified recorded transmissions"/)
  assert.doesNotMatch(unresolved, /Inspect recorded transmission edges|isolated-transmissions/)
  assert.equal((unresolved.match(/class="network-svg"/g) ?? []).length, 1)
  assert.match(unresolved, /Unresolved transmission/)
  assert.doesNotMatch(unresolved, /Source reviewed/)
  assert.deepEqual(renderedEdges(unresolved), [5, 4])
  assert.doesNotMatch(unresolved, /Select isnad/)
  assert.doesNotMatch(render([], { emptyReason: 'The stored route is withheld.' }), /network-svg/)
})

test('an unresolved edge remains visibly unverified alongside a reviewed route', () => {
  const mixed = groupChains([edge(1, 30001, 2), edge(2, 2, 1), edge(3, 1, 3)], [evidence])
  const html = render(mixed, { chainIndex: 1 })
  assert.match(html, /Showing recorded transmissions/)
  assert.match(html, /Unresolved transmission/)
  assert.doesNotMatch(html, /Source reviewed|Highlight Madar/)
  assert.deepEqual(renderedEdges(html), [3])
})

test('does not infer Madar from the middle narrator on source-reviewed or incomplete routes', () => {
  for (const html of [render(routes), render(routes, { chainIndex: 1 })]) {
    assert.doesNotMatch(html, /Highlight Madar|madar-mark|svg-node madar/)
    assert.match(html, /Trace path/)
  }
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8')
  assert.doesNotMatch(app, /highlightMadar|madarId/)
})

test('profile count cards and the source proposal accordion are absent', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8')
  assert.doesNotMatch(app, /Direct teachers|Direct students|In this chain|External source proposals/)
})

test('Bukhari 7000 inspects all original cyclic edges without assigning eras', () => {
  const pairs = [
    [30001, 30020],
    [30020, 36033],
    [36033, 5650],
    [5650, 8194],
    [8194, 5121],
    [5121, 769],
    [769, 6],
    [6, 23557],
    [23557, 803739],
    [803739, 1],
    [1, 769],
    [769, 6],
    [6, 803740],
    [803740, 803741],
    [803741, 1],
    [1, 803742],
    [803742, 803743],
    [803743, 1],
  ]
  const edges = pairs.map(([student, teacher], sequence) => ({
    ...edge(37994 + sequence, student, teacher), sequence,
  }))
  const ids = new Set(pairs.flat())
  const records = [...ids].map(id => ({
    ...narrators[0], id, name: `Record ${id}`, grade: id >= 800000 ? 'Unmatched isnad name' : '',
  }))
  const html = render(groupChains(edges), { hadithNumber: '7000', narrators: records })
  assert.match(html, /15 narrator IDs · 18 recorded edges/)
  assert.match(html, /Unknown \/ unresolved/)
  assert.match(html, /Cycle/)
  assert.equal((html.match(/Repeated teacher–student pair/g) ?? []).length, 2)
  assert.equal((html.match(/Prophet endpoint · unverified/g) ?? []).length, 5)
  assert.deepEqual(renderedEdges(html), edges.map(e => e.id))
  assert.deepEqual([...html.matchAll(/data-teacher-id="(\d+)" data-student-id="(\d+)"/g)]
    .map(([, teacher, student]) => [Number(student), Number(teacher)]), pairs)
  assert.doesNotMatch(html, /network-svg|tier-bands|Source reviewed/)
})

test('a linear segment with an unmatched narrator draws its edges without era bands', () => {
  const unknown = { ...narrators[0], id: 800000, role: 'Unresolved', grade: 'Unmatched isnad name' }
  const html = render(groupChains([edge(4, 30001, 2), edge(5, 2, unknown.id)]), {
    narrators: [...narrators, unknown],
  })
  assert.deepEqual(renderedEdges(html), [5, 4])
  assert.match(html, /without an era assignment/)
  assert.doesNotMatch(html, /COMPANION|SUCCESSORS/)
})
