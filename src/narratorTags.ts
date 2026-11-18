function decodeTag(value: string) {
  return value.replace(/(?:%[\da-f]{2})+/gi, encoded => {
    try {
      return decodeURIComponent(encoded)
    } catch {
      return encoded
    }
  })
}

function comparisonKey(value: string) {
  return value.normalize('NFC').trim().replace(/\s+/g, ' ').toLowerCase()
}

export function parseNarratorTags(value?: string | null): string[] {
  if (!value) return []

  // Only balanced brackets protect commas. An unclosed bracket in one
  // entry should not swallow every tag that follows it.
  const openings: number[] = []
  const pairs = new Map<number, number>()
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === '[') openings.push(index)
    if (value[index] === ']') {
      const opening = openings.pop()
      if (opening !== undefined) pairs.set(opening, index)
    }
  }

  const tags = new Map<string, string>()
  let start = 0
  for (let index = 0; index <= value.length; index += 1) {
    const closing = pairs.get(index)
    if (closing !== undefined) {
      index = closing
      continue
    }
    if (index < value.length && value[index] !== ',' && value[index] !== '،') continue

    let label = decodeTag(value.slice(start, index)).trim()
    start = index + 1
    const bracket = label.lastIndexOf('[')
    if (bracket > 0 && label.endsWith(']')) {
      const name = label.slice(0, bracket).trim()
      const identifier = label.slice(bracket + 1, -1)
      if (comparisonKey(name) === comparisonKey(identifier)) label = name
    }

    if (comparisonKey(label) === 'client') label = 'Mawla (مولى)'

    const key = comparisonKey(label)
    if (key && !/^(?:n\/?a|\[\]|[–—-])$/.test(key) && !tags.has(key)) tags.set(key, label)
  }
  return [...tags.values()]
}
