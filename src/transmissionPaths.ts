export type EdgeRecord = {
  id: number
  teacher: number
  student: number
  terminology: string
  sequence: number
  chain_index?: number | null
  correction?: { source_url: string; evidence: string; original_student: number; original_teacher: number }
}

export type RouteEvidence = {
  edge_ids: number[]
  status: 'reviewed' | 'legacy_segment'
  source_url: string
  note: string
}

type Route = {
  edges: EdgeRecord[]
  status: RouteEvidence['status'] | 'recorded' | 'unresolved'
  evidence?: RouteEvidence
}

function isOrderedPath(edges: EdgeRecord[]) {
  return edges.length > 0
    && edges.every((edge, index) => index === 0 || (
      edges[index - 1].teacher === edge.student && edges[index - 1].sequence < edge.sequence
    ))
    && new Set(orderChain(edges)).size === edges.length + 1
}

export function groupChains(edges: EdgeRecord[], evidence: RouteEvidence[] = []): Route[] {
  const ordered = [...edges].sort((a, b) => a.sequence - b.sequence || a.id - b.id)
  const byId = new Map(ordered.map(edge => [edge.id, edge]))
  const assigned = new Set<number>()
  const routes: Route[] = []
  for (const review of evidence) {
    const path = review.edge_ids.map(id => byId.get(id))
    if (!path.every((edge): edge is EdgeRecord => Boolean(edge && !assigned.has(edge.id))) || !isOrderedPath(path)) continue
    routes.push({ edges: path, status: review.status, evidence: review })
    path.forEach(edge => assigned.add(edge.id))
  }
  const indexed = new Map<number, EdgeRecord[]>()
  for (const edge of ordered) {
    if (assigned.has(edge.id)) continue
    if (edge.chain_index == null) {
      routes.push({ edges: [edge], status: 'unresolved' })
      continue
    }
    const group = indexed.get(edge.chain_index) ?? []
    group.push(edge)
    indexed.set(edge.chain_index, group)
  }
  for (const path of indexed.values()) {
    if (isOrderedPath(path)) {
      routes.push({ edges: path, status: 'recorded' })
    } else {
      routes.push(...path.map(edge => ({ edges: [edge], status: 'unresolved' as const })))
    }
  }
  return routes.sort((a, b) => a.edges[0].sequence - b.edges[0].sequence || a.edges[0].id - b.edges[0].id)
}

export function orderChain(edges: EdgeRecord[]) {
  if (!edges.length) return []
  return [edges[0].student, ...edges.map((edge) => edge.teacher)].reverse()
}
