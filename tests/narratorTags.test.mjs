import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parseNarratorTags } from '../src/narratorTags.ts'

test('separates and cleans the tags recorded for Thawban', () => {
  const value = 'Ally B. Hasim [Ally%20B.%20Hasim] , Yemen [Yemen] , Freed Slave [Freed%20Slave] , Client [Client]'
  assert.deepEqual(parseNarratorTags(value), ['Ally B. Hasim', 'Yemen', 'Freed Slave', 'Mawla (مولى)'])
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
  assert.deepEqual(parseNarratorTags('Yemen, yemen [Yemen], Café, Cafe%CC%81, Client [Client]'), ['Yemen', 'Café', 'Mawla (مولى)'])
})

test('leaves malformed escapes and brackets readable without losing later entries', () => {
  assert.deepEqual(
    parseNarratorTags('Broken [note, Yemen [Yemen], Tag [%E0%A4], Invalid%ZZ'),
    ['Broken [note', 'Yemen', 'Tag [%E0%A4]', 'Invalid%ZZ'],
  )
  assert.deepEqual(parseNarratorTags('Unmatched ], Yemen'), ['Unmatched ]', 'Yemen'])
})

test('standardizes the recorded Client tag for al-Dawraqi as well as Thawban', () => {
  assert.deepEqual(
    parseNarratorTags("al-'Abdi [al-'Abdi] , Client [Client] , Baghdadi [Baghdadi]"),
    ["al-'Abdi", 'Mawla (مولى)', 'Baghdadi'],
  )
})

test('matches standalone Client after decoding and case folding', () => {
  for (const label of ['CLIENT', 'cLiEnT [Client]', '%43lient', '%63%6C%69%65%6E%74']) {
    assert.deepEqual(parseNarratorTags(label), ['Mawla (مولى)'])
  }
})

test('preserves longer phrases and meaningful notes containing Client', () => {
  assert.deepEqual(
    parseNarratorTags('Client of Tamim, Client [meaningful note], راوية [Client], Yemen, Freed Slave'),
    ['Client of Tamim', 'Client [meaningful note]', 'راوية [Client]', 'Yemen', 'Freed Slave'],
  )
})

test('deduplicates Client and the existing Mawla label in either order', () => {
  for (const value of ['Client, Mawla (مولى), CLIENT', 'Mawla%20(مولى), client [Client]']) {
    assert.deepEqual(parseNarratorTags(value), ['Mawla (مولى)'])
  }
})
