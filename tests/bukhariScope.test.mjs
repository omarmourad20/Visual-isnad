import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'

test('the explorer offers no external hadith reader or graph entry point', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8')
  assert.doesNotMatch(app, /17154|Sunan Abi Dawud|knowledge-graph\/hadiths|source-routes/)
  assert.match(app, /className="eyebrow">Sahih al-Bukhari<\/p>/)
  assert.match(app, /knowledge-graph\/rawis\//)
})
