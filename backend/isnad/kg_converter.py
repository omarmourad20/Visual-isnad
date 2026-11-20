"""Convert Hadith Knowledge Graph chains into Visual Isnad graph data."""

def convert_kg_chain(sanad):
    """Convert one sanad without mixing it with other chains."""

    original_chain = sanad.get("chain", [])
    narrators = []
    edges = []

    # Reserve a separate numeric ID range for Knowledge Graph narrators.
    id_offset = 1000000

    for node in original_chain:
        rawi_id = int(node["rawiId"])
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
            "id": int(sanad["sanadId"]) * 100 + index,
            "teacher": int(teacher["rawiId"]) + id_offset,
            "student": int(student["rawiId"]) + id_offset,
            "terminology": "عن",
            "sequence": index + 1,
        })

    return {
        "sanad_id": sanad.get("sanadId"),
        "grade": sanad.get("grade"),
        "grade_reason": sanad.get("gradeReason"),
        "narrators": narrators,
        "edges": edges,
    }
