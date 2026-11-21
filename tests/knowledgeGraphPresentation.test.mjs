import assert from 'node:assert/strict'
import { test } from 'node:test'
import { knowledgeGraphExampleRecord, unavailableTranslation } from '../src/knowledgeGraphPresentation.ts'

test('Abu Dawud 832 has its own reference and keeps exact Arabic without borrowing English', () => {
  const nass = ' نَصّ عربي\nمِنَ المَصْدَر '
  const record = knowledgeGraphExampleRecord({ hadithId: 17154, bookId: 4, noInBook: 832, nass, matnClean: 'مختصر' })
  assert.equal(record.id, 17154)
  assert.match(record.in_book_reference, /Sunan Abi Dawud 832 · KG ID 17154/)
  assert.equal(record.arabic_full, nass)
  assert.equal(record.arabic_matn, 'مختصر')
  assert.equal(record.english_matn, undefined)
  assert.match(unavailableTranslation(true), /Knowledge Graph record/)
})

test('matching printed numbers do not make Bukhari and Abu Dawud the same source', () => {
  assert.throws(() => knowledgeGraphExampleRecord({ hadithId: 17154, bookId: 1, noInBook: 832 }))
  assert.throws(() => knowledgeGraphExampleRecord({ hadithId: 832, bookId: 4, noInBook: 832 }))
})
