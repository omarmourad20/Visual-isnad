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

test('profile count cards and the source proposal accordion are absent', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8')
  assert.doesNotMatch(app, /Direct teachers|Direct students|In this chain|External source proposals/)
})

test('draws all original arrows across cycles and parallel edges using one node per narrator', () => {
  const route = groupChains([edge(1, 2, 1), edge(2, 1, 2), edge(3, 2, 1), edge(4, 1, 1)])
  const html = render(route)
  assert.match(html, /revisits a narrator/)
  assert.deepEqual(renderedEdges(html), [4, 3, 2, 1])
  assert.equal((html.match(/class="svg-node/g) ?? []).length, 2)
  const paths = [...html.matchAll(/class="edge-hit" d="([^"]+)"/g)].map(match => match[1])
  assert.equal(new Set(paths).size, 4)
})
