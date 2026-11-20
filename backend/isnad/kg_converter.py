"""Convert Hadith Knowledge Graph chains into Visual Isnad graph data."""

def convert_kg_chain(sanad):
    """Convert one sanad without mixing it with other chains."""

    sanad_id = int(sanad["sanadId"])
    original_chain = sanad.get("chain", [])
    narrators = []
    edges = []

    # Reserve a separate numeric ID range for Knowledge Graph narrators.
    id_offset = 1000000

    if not isinstance(original_chain, list):
        raise ValueError("A sanad chain must be an ordered list")

    for node in original_chain:
        rawi_id = int(node["rawiId"])
        if not 0 < rawi_id < id_offset:
            raise ValueError("KG narrator ID is outside the supported namespace")
        internal_id = rawi_id + id_offset
        name = node.get("name") or "راوٍ غير معروف"
        rank = node.get("rank") or ""

        narrators.append({
            "id": internal_id,
            "kg_rawi_id": rawi_id,
            "name": name,
            "arabic_name": name,
            "grade": rank,
            "tawthiq": rank,
            "tabaqah": str(node.get("tabaka") or ""),
            "region": "",
            "birth_display": "",
            "death_display": "",
            "birth_place": "",
            "death_place": "",
        })

    # The source orders narrators from compiler toward the source.
    # Visual Isnad edges point from teacher toward student.
    for index in range(len(original_chain) - 1):
        student = original_chain[index]
        teacher = original_chain[index + 1]

        edges.append({
            "id": sanad_id * 100 + index,
            "teacher": int(teacher["rawiId"]) + id_offset,
            "student": int(student["rawiId"]) + id_offset,
            "terminology": student.get("terminology") or "",
            "sequence": index + 1,
        })

    return {
        "sanad_id": sanad_id,
        "source": {"provider": "hadith_kg", "status": "external_unreviewed", "native_sanad_id": sanad_id},
        "grade": sanad.get("grade"),
        "grade_reason": sanad.get("gradeReason"),
        "narrators": narrators,
        "edges": edges,
    }
