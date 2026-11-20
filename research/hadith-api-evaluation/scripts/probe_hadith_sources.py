"""Perform bounded read-only HTTP probes without credentials."""
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URLS = {
    "sunnah": "https://api.sunnah.com/v1/collections/bukhari/hadiths/1",
    "hadithapi": "https://hadithapi.com/api/hadiths",
    "fawaz": "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-bukhari/1.json",
    "hadeethenc": "https://hadeethenc.com/api/v1/categories/list/?language=en",
    "dorar": "https://dorar.net/dorar_api.json?" + urlencode({"skey": "إنما الأعمال بالنيات"}),
}
LIMIT = 2_000_000


def probe(url, timeout):
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=timeout) as response:
            data = response.read(LIMIT + 1)
            result = {"status": response.status, "content_type": response.headers.get("Content-Type")}
            if len(data) > LIMIT:
                return {**result, "error": "Response exceeded byte limit"}
            try:
                value = json.loads(data)
            except ValueError:
                return {**result, "json": False}
            result["json"] = True
            if isinstance(value, dict):
                result["keys"] = sorted(value)
                for key in ("sanads", "teachers", "students", "aqwal", "hadiths"):
                    if isinstance(value.get(key), list):
                        result[f"{key}_count"] = len(value[key])
                if isinstance(value.get("sanads"), list):
                    result["sanads"] = [{
                        "id": entry.get("sanadId"), "narrator_ids": [
                            node.get("rawiId") for node in entry.get("chain", [])],
                    } for entry in value["sanads"]]
                if url.endswith("/api/stats"):
                    result["stats"] = value
            elif isinstance(value, list):
                result["records"] = len(value)
            return result
    except HTTPError as error:
        with error:
            result = {"status": error.code, "content_type": error.headers.get("Content-Type")}
            try:
                value = json.loads(error.read(4096))
                if isinstance(value, dict) and isinstance(value.get("message"), str):
                    result["message"] = value["message"][:200]
            except ValueError:
                pass
            return result
    except (URLError, TimeoutError) as error:
        return {"status": None, "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kg", default="http://127.0.0.1:8077")
    parser.add_argument("--kg-hadith-id", type=int, default=17154, help="KG internal ID, not Bukhari numbering")
    parser.add_argument("--kg-rawi-id", type=int, default=3567)
    args = parser.parse_args()
    urls = {**URLS, **{
        f"kg_{label}": args.kg.rstrip("/") + "/api/" + route
        for label, route in (
            ("stats", "stats"), ("hadith", f"hadith/{args.kg_hadith_id}"), ("rawi", f"rawi/{args.kg_rawi_id}"),
        )
    }}
    print(json.dumps({key: probe(url, 8) for key, url in urls.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
