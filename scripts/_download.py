"""Download a public file once, if it is not already on disk. No accounts, keys or payment involved."""

import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"}


def ensure(path: Path, url: str, what: str) -> bool:
    if path.exists():
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {what} ...")
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()
    except Exception as e:  # noqa: BLE001
        print(f"Could not download {what} ({e}).")
        return False
    path.write_bytes(data)
    return True


def fred(series_id: str, path: Path) -> bool:
    """FRED series as CSV; the first column is renamed to observation_date so every script reads it the same way."""
    ok = ensure(path, f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}", f"FRED {series_id}")
    if ok:
        text = path.read_text()
        head, _, rest = text.partition("\n")
        cols = head.split(",")
        if cols[0] != "observation_date":
            path.write_text("observation_date," + ",".join(cols[1:]) + "\n" + rest)
    return ok
