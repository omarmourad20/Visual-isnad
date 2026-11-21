"""Collection identifiers used by the local catalog and the pinned KG edition."""
from urllib.parse import urlsplit

BUKHARI_TITLE = "Sahih al-Bukhari"
BUKHARI_ARABIC_TITLE = "صحيح البخاري"
BUKHARI_TITLES = (BUKHARI_TITLE, BUKHARI_ARABIC_TITLE)

# Primary key of the Sahih al-Bukhari edition in the Hadith KG books table.
KG_BUKHARI_BOOK_ID = "1"


def is_bukhari_reference(reference):
    try:
        url = urlsplit(reference)
    except ValueError:
        return False
    return (
        url.scheme in {"http", "https"}
        and url.netloc.lower() in {"sunnah.com", "www.sunnah.com"}
        and url.path.startswith("/bukhari:")
    )
