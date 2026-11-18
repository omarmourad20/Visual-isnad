export type EdgeRecord = {
  id: number
  teacher: number
  student: number
  terminology: string
  sequence: number
  chain_index?: number | null
}

export function groupChains(edges: EdgeRecord[]) {
  const paths: EdgeRecord[][] = []
  const byIndex = new Map<number | null, EdgeRecord[]>()
  for (const edge of [...edges].sort((a, b) => a.sequence - b.sequence || a.id - b.id)) {
    const index = edge.chain_index ?? null
    let path = byIndex.get(index)
    if (!path || path[path.length - 1].teacher !== edge.student) {
      // Preserve disconnected runs as selectable paths instead of flattening
      // them into a route that drops the later run's first student.
      path = []
      paths.push(path)
      byIndex.set(index, path)
    }
    path.push(edge)
  }
  return paths
}

export function orderChain(edges: EdgeRecord[]) {
  if (!edges.length) return []
  return [edges[0].student, ...edges.map((edge) => edge.teacher)].reverse()
}
