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

function appendRecordedSegment(routes: Route[], segment: EdgeRecord[] | undefined, edge: EdgeRecord) {
  const previous = segment?.at(-1)
  if (segment && previous?.teacher === edge.student && previous.sequence + 1 === edge.sequence) {
    segment.push(edge)
    return segment
  }
  const edges = [edge]
  routes.push({ edges, status: 'unresolved' })
  return edges
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
  let unindexedSegment: EdgeRecord[] | undefined
  for (const edge of ordered) {
    if (assigned.has(edge.id)) {
      unindexedSegment = undefined
      continue
    }
    if (edge.chain_index == null) {
      unindexedSegment = appendRecordedSegment(routes, unindexedSegment, edge)
      continue
    }
    unindexedSegment = undefined
    const group = indexed.get(edge.chain_index) ?? []
    group.push(edge)
    indexed.set(edge.chain_index, group)
  }
  for (const path of indexed.values()) {
    if (isOrderedPath(path)) {
      routes.push({ edges: path, status: 'recorded' })
    } else {
      let segment: EdgeRecord[] | undefined
      for (const edge of path) segment = appendRecordedSegment(routes, segment, edge)
    }
  }
  return routes.sort((a, b) => a.edges[0].sequence - b.edges[0].sequence || a.edges[0].id - b.edges[0].id)
}

export function orderChain(edges: EdgeRecord[]) {
  if (!edges.length) return []
  return [edges[0].student, ...edges.map((edge) => edge.teacher)].reverse()
}

// A recorded segment can revisit a narrator. Use one node per identity while
// retaining all original edges, including repeated and reciprocal pairs.
export function graphNarratorIds(edges: EdgeRecord[]) {
  return [...new Set(orderChain(edges))]
}

/** For the evidence inspector, retain every row and mark directed cycle membership. */
export function describeRecordedEdges(edges: EdgeRecord[]) {
  const studentsByTeacher = new Map<number, Set<number>>()
  const counts = new Map<string, number>()
  for (const edge of edges) {
    const students = studentsByTeacher.get(edge.teacher) ?? new Set<number>()
    students.add(edge.student)
    studentsByTeacher.set(edge.teacher, students)
    const pair = `${edge.teacher}:${edge.student}`
    counts.set(pair, (counts.get(pair) ?? 0) + 1)
  }

  const reachableByStart = new Map<number, Set<number>>()
  return edges.map(edge => {
    let reachable = reachableByStart.get(edge.student)
    if (!reachable) {
      reachable = new Set([edge.student])
      const pending = [edge.student]
      while (pending.length) {
        for (const next of studentsByTeacher.get(pending.pop()!) ?? []) {
          if (reachable.has(next)) continue
          reachable.add(next)
          pending.push(next)
        }
      }
      reachableByStart.set(edge.student, reachable)
    }
    return {
      edge,
      cycle: reachable.has(edge.teacher),
      repeated: (counts.get(`${edge.teacher}:${edge.student}`) ?? 0) > 1,
    }
  })
}
