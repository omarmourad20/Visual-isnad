# Read-only Bukhari database comparison

Run `python tools/compare-bukhari-readonly.py ACTIVE.sqlite3 CORRECTED.sqlite3`.
The script accepts existing files only, opens them with SQLite URI mode=ro,
and sets query_only before taking a read transaction on each database.
It uses the Python standard library and prints JSON to stdout. It does not
invoke Django or migrations. SQLite may use WAL shared-memory sidecars
when reading a live WAL database. For an audit during active writes or
when the source folder itself must stay untouched, use an existing consistent
SQLite backup of the active database. Do not copy just a live WAL database file.

The counts and deltas describe the records observed in the two snapshots.
The canonical edge comparison counts occurrences keyed by stored hadith
number and canonical student and teacher IDs. It excludes generated narrator
IDs and cannot establish route equivalence or historical authenticity.
A null indexed-route count means that schema has no chain_index column.

Profile differences list canonical narrator IDs and field names only.
They can arise from imports, normalization, or manual edits. Check the
prior import or an edit log before treating them as manual edits. An
active-only canonical ID also needs review. Account comparisons use
usernames internally and report counts only. Passwords and session data
are neither read nor printed.
