export const KG_EXAMPLE = {
  id: 17154,
  bookId: 4,
  reference: '832',
  collection: 'Sunan Abi Dawud',
} as const

export function knowledgeGraphExampleRecord(data: {
  hadithId?: number
  bookId?: number
  noInBook?: number | string
  matnClean?: string
  nass?: string
  hukm?: string
}) {
  if ((data.hadithId != null && Number(data.hadithId) !== KG_EXAMPLE.id)
      || Number(data.bookId) !== KG_EXAMPLE.bookId || String(data.noInBook) !== KG_EXAMPLE.reference) {
    throw new Error('Knowledge Graph returned a different source reference')
  }
  return {
    id: KG_EXAMPLE.id,
    hadith_number: KG_EXAMPLE.reference,
    book_title: KG_EXAMPLE.collection,
    in_book_reference: `${KG_EXAMPLE.collection} ${KG_EXAMPLE.reference} · KG ID ${KG_EXAMPLE.id}`,
    arabic_matn: data.matnClean || data.nass || '',
    arabic_full: data.nass || '',
    grade: data.hukm || '',
  }
}

export function unavailableTranslation(external: boolean) {
  return external
    ? 'This Knowledge Graph record has no English translation.'
    : 'English translation is not available for this record.'
}
