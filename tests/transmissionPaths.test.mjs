import assert from 'node:assert/strict'
import { test } from 'node:test'
import { graphNarratorIds, groupChains, orderChain } from '../src/transmissionPaths.ts'

function edge(sequence, student, teacher, chain_index) {
  return { id: sequence + 1, sequence, student, teacher, chain_index, terminology: 'عن' }
}
const ordered = routes => routes.map(route => orderChain(route.edges))

test('preserves both indexed paths sharing compiler and prophetic endpoint', () => {
  const routes = groupChains([edge(3, 12, 1, 1), edge(0, 30001, 11, 0), edge(2, 30001, 12, 1), edge(1, 11, 1, 0)])
  assert.deepEqual(ordered(routes), [[1, 11, 30001], [1, 12, 30001]])
  assert.deepEqual(routes.map(route => route.status), ['recorded', 'recorded'])
})

test('does not package a disconnected or cyclic indexed path as a route', () => {
  const split = groupChains([edge(0, 30001, 11, 0), edge(1, 22, 1, 0)])
  assert.deepEqual(ordered(split), [[11, 30001], [1, 22]])
  assert.deepEqual(split.map(route => route.status), ['unresolved', 'unresolved'])
  const cycle = groupChains([edge(0, 10, 11, 0), edge(1, 11, 10, 0)])
  assert.equal(cycle.length, 1)
  assert.equal(cycle[0].status, 'unresolved')
  assert.deepEqual(cycle[0].edges.map(e => e.id), [1, 2])
  assert.deepEqual(graphNarratorIds(cycle[0].edges), [10, 11])
})

test('shows contiguous unindexed edges together without classifying them as an isnad', () => {
  const routes = groupChains([edge(0, 30001, 11, 0), edge(1, 30001, 12, null), edge(2, 12, 1, null)])
  assert.deepEqual(ordered(routes), [[11, 30001], [1, 12, 30001]])
  assert.deepEqual(routes.map(route => route.status), ['recorded', 'unresolved'])
})

test('keeps both source-annotated Bukhari 15 segments in teaching order', () => {
  const first = [30001, 30400, 20208, 11295, 19, 1]
  const second = [30001, 20404, 20020, 11019, 19]
  const edges = []
  for (const path of [first, second]) {
    path.slice(1).forEach((teacher, index) => edges.push(edge(edges.length, path[index], teacher, null)))
  }
  const routes = groupChains(edges, [
    { edge_ids: [1, 2, 3, 4, 5], status: 'reviewed' },
    { edge_ids: [6, 7, 8, 9], status: 'legacy_segment' },
  ])
  assert.deepEqual(ordered(routes), [first.toReversed(), second.toReversed()])
  assert.deepEqual(routes.map(route => route.status), ['reviewed', 'legacy_segment'])
})

test('incomplete source annotations cannot swallow recorded edges', () => {
  const routes = groupChains([edge(0, 2, 1, null)], [{ edge_ids: [1, 8], status: 'reviewed' }])
  assert.equal(routes[0].status, 'unresolved')
  assert.equal(routes[0].edges[0].id, 1)
})

test('does not bridge sequence gaps, disconnected edges, or source-reviewed boundaries', () => {
  const edges = [edge(0, 10, 11), edge(2, 11, 12), edge(3, 20, 21), edge(4, 21, 22), edge(5, 22, 23)]
  const routes = groupChains(edges, [{ edge_ids: [5], status: 'reviewed' }])
  assert.deepEqual(routes.map(route => route.edges.map(e => e.id)), [[1], [3], [4], [5], [6]])
  assert.deepEqual(routes.map(route => route.status), ['unresolved', 'unresolved', 'unresolved', 'reviewed', 'unresolved'])
})
