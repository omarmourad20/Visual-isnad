import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parseNarratorTags } from '../src/narratorTags.ts'

test('separates and cleans the tags recorded for Thawban', () => {
  const value = 'Ally B. Hasim [Ally%20B.%20Hasim] , Yemen [Yemen] , Freed Slave [Freed%20Slave] , Client [Client]'
  assert.deepEqual(parseNarratorTags(value), ['Ally B. Hasim', 'Yemen', 'Freed Slave', 'Client'])
})

test('preserves Arabic, Unicode and bracketed information different from the label', () => {
  assert.deepEqual(
    parseNarratorTags('اليمن [%D8%A7%D9%84%D9%8A%D9%85%D9%86]، راوية [القرن الثاني، مختلف فيه], Café [Caf%C3%A9], Makkah [region [historical]]'),
    ['اليمن', 'راوية [القرن الثاني، مختلف فيه]', 'Café', 'Makkah [region [historical]]'],
  )
})

test('decodes escaped punctuation after separating entries and preserves literal plus signs', () => {
  assert.deepEqual(parseNarratorTags('Hadith%2C%20Fiqh, C++, Yemen%20%5BYemen%5D'), ['Hadith, Fiqh', 'C++', 'Yemen'])
})

test('drops placeholders and duplicates while retaining the first display label', () => {
  assert.deepEqual(parseNarratorTags(null), [])
  assert.deepEqual(parseNarratorTags(' , NA, n/a, [], —, '), [])
  assert.deepEqual(parseNarratorTags('Yemen, yemen [Yemen], Café, Cafe%CC%81, Client [Client]'), ['Yemen', 'Café', 'Client'])
})

test('leaves malformed escapes and brackets readable without losing later entries', () => {
  assert.deepEqual(
    parseNarratorTags('Broken [note, Yemen [Yemen], Tag [%E0%A4], Invalid%ZZ'),
    ['Broken [note', 'Yemen', 'Tag [%E0%A4]', 'Invalid%ZZ'],
  )
  assert.deepEqual(parseNarratorTags('Unmatched ], Yemen'), ['Unmatched ]', 'Yemen'])
})
