import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

let server
let NarratorProfile
before(async () => {
  server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, ws: false } })
  const module = await server.ssrLoadModule('/src/NarratorProfile.tsx')
  NarratorProfile = module.default
})
after(async () => { await server?.close() })

const record = { id: 20208, name: 'Ismail', arabic_name: 'إسماعيل' }

function profile(data = {}, source = 'local') {
  return renderToStaticMarkup(createElement(NarratorProfile, {
    record: { ...record, ...data }, source, status: 'loaded', onOpen() {}, onRetry() {},
  }))
}

test('displays a source-specific message for a missing biography', () => {
  assert.match(profile(), /No biographical notes stored for this narrator yet\./)
  assert.match(profile({ biography: ' ' }, 'knowledge_graph'), /No prose biography available in this source\./)
})

test('preserves Arabic biography wording and uses bidi isolation for mixed values', () => {
  const biography = '  إسماعيل بن إبراهيم\nأبو بشر  '
  const html = profile({ biography, region: 'Basra · البصرة' })
  assert.ok(html.includes(`lang="ar" dir="rtl">${biography}</p>`))
  assert.match(html, /lang="en" dir="ltr"/)
  assert.ok(html.includes('<dd dir="auto">Basra · البصرة</dd>'))
})

test('keeps evaluation order, count, original Arabic wording and KG attribution', () => {
  const aqwal = [
    { alemId: 7, alem: 'أبو أحمد', qawl: 'ثِقَةٌ  حافظ' },
    { alemId: 7, alem: 'أبو أحمد', qawl: 'روى عنه الناس.' },
  ]
  const html = profile({ aqwal }, 'knowledge_graph')
  assert.match(html, /Scholarly evaluations \(2\)/)
  assert.equal(html.match(/<small>Hadith Knowledge Graph<\/small>/g)?.length, 2)
  const statements = [...html.matchAll(/<blockquote class="narrator-source-text" lang="ar" dir="rtl">(.*?)<\/blockquote>/g)]
  assert.deepEqual(statements.map(([, quote]) => quote), aqwal.map(({ qawl }) => qawl))
})

test('separates KG route relationships and catalog relationships', () => {
  const related = [{ id: 5, name: 'Teacher', arabic_name: 'شيخ' }]
  const kg = profile({ teachers: related, students: related }, 'knowledge_graph')
  const local = profile({
    teachers: related, students: related, transmission_students: related,
    catalog_source_url: 'https://muslimscholars.info/manage.php?ID=20020',
  })
  assert.match(kg, /Profile source: Hadith Knowledge Graph/)
  assert.match(kg, /Teachers in KG routes \(1\)/)
  assert.match(kg, /Students in KG routes \(1\)/)
  assert.match(local, /Profile source: Visual Isnad catalog/)
  assert.match(local, /Open catalog entry/)
  assert.match(local, /Narrators linked in imported Bukhari chains \(1\)/)
})
