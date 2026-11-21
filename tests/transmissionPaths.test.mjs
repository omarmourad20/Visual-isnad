import assert from 'node:assert/strict'
import { test } from 'node:test'
import { groupChains, orderChain } from '../src/transmissionPaths.ts'

function edge(sequence, student, teacher, chain_index) {
  return { id: sequence + 1, sequence, student, teacher, chain_index, terminology: 'عن' }
}

test('preserves both paths when they share a compiler and prophetic endpoint', () => {
  const result = groupChains([edge(3, 12, 1, 1), edge(0, 30001, 11, 0), edge(2, 30001, 12, 1), edge(1, 11, 1, 0)])
  assert.deepEqual(result.map(orderChain), [[1, 11, 30001], [1, 12, 30001]])
})

test('preserves both endpoints of an explicitly indexed disconnected path', () => {
  const result = groupChains([edge(0, 30001, 11, 0), edge(1, 22, 1, 0)])
  assert.deepEqual(result.map(orderChain), [[11, 30001], [1, 22]])
})

test('keeps unindexed legacy paths separate from indexed paths', () => {
  const result = groupChains([edge(0, 30001, 11, 0), edge(1, 30001, 12, null), edge(2, 12, 1, null)])
  assert.deepEqual(result.map(orderChain), [[11, 30001], [1, 12, 30001]])
})

test('keeps corrected legacy Bukhari 15 segments separate in teacher-to-student order', () => {
  const first = [30001, 30400, 20208, 11295, 19, 1]
  const second = [30001, 20404, 20020, 11019, 19]
  const edges = []
  for (const path of [first, second]) {
    path.slice(1).forEach((teacher, index) => {
      edges.push(edge(edges.length, path[index], teacher, null))
    })
  }
  assert.deepEqual(groupChains(edges).map(orderChain), [
    [1, 19, 11295, 20208, 30400, 30001],
    [19, 11019, 20020, 20404, 30001],
  ])
})
