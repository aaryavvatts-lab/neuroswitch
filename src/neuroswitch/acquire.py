"""Fetch subjects from OpenNeuro (ds008162) anonymously, one at a time.

The dataset is public and CC0, so no credentials are needed -- plain anonymous
HTTPS against the S3 bucket.  We deliberately fetch only the modalities the
pipeline uses (T1w, draw/rest BOLD, events, behaviour), which is ~1.6 GB per
subject instead of ~2.6 GB, and we verify Content-Length against what we
received so a truncated download can never be mistaken for a good one.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .preprocess import BIDS

DS = "ds008162"
BUCKET = "https://s3.amazonaws.com/openneuro.org"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"

WANTED_SUFFIXES = (
    "_T1w.nii.gz", "_T1w.json",
    "_bold.nii.gz", "_bold.json",
    "_events.tsv", "_beh.tsv",
)
SKIP_TASKS = ()          # e.g. ("restingstate",) to defer resting-state


def list_keys(prefix: str) -> list[tuple[str, int]]:
    """List (key, size) under a prefix, following continuation tokens."""
    out, token = [], None
    while True:
        url = f"{BUCKET}/?list-type=2&prefix={prefix}&max-keys=1000"
        if token:
            from urllib.parse import quote
            url += f"&continuation-token={quote(token, safe='')}"
        xml = subprocess.run(["curl", "-sS", "--max-time", "120", url],
                             capture_output=True, text=True, check=True).stdout
        root = ET.fromstring(xml)
        for c in root.findall(f"{NS}Contents"):
            out.append((c.findtext(f"{NS}Key"), int(c.findtext(f"{NS}Size"))))
        if root.findtext(f"{NS}IsTruncated") != "true":
            break
        token = root.findtext(f"{NS}NextContinuationToken")
        if not token:
            break
    return out


def wanted(key: str) -> bool:
    if not any(key.endswith(s) for s in WANTED_SUFFIXES):
        return False
    if "/dwi/" in key or "/fmap/" in key or "_sbref" in key or "_T2w" in key:
        return False
    return not any(f"task-{t}" in key for t in SKIP_TASKS)


def _fetch_one(key: str, size: int, dest_root: Path, retries: int = 3) -> tuple[str, bool, str]:
    rel = key.split(f"{DS}/", 1)[1]
    dest = dest_root / rel
    if dest.is_file() and dest.stat().st_size == size:
        return rel, True, "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BUCKET}/{key}"
    for attempt in range(retries):
        r = subprocess.run(["curl", "-sS", "--fail", "--max-time", "1800",
                            "-o", str(dest), url], capture_output=True, text=True)
        if r.returncode == 0 and dest.is_file() and dest.stat().st_size == size:
            return rel, True, "ok"
        if dest.is_file():
            dest.unlink()
    return rel, False, f"failed after {retries} attempts"


def fetch_subject(sub: str, dest_root: Path | None = None, workers: int = 4) -> dict:
    dest_root = dest_root or BIDS
    keys = [(k, s) for k, s in list_keys(f"{DS}/{sub}/") if wanted(k)]
    if not keys:
        return {"sub": sub, "ok": False, "reason": "no matching keys on S3"}
    total = sum(s for _, s in keys)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch_one, k, s, dest_root) for k, s in keys]
        for f in futs:
            results.append(f.result())
    bad = [r for r in results if not r[1]]
    return {"sub": sub, "ok": not bad, "n_files": len(keys),
            "bytes": total, "failures": [r[0] for r in bad]}


def fetch_top_level(dest_root: Path | None = None) -> list[str]:
    """Small dataset-level files, including the phenotype/ directory."""
    dest_root = dest_root or BIDS
    got = []
    for prefix in (f"{DS}/phenotype/", f"{DS}/participants", f"{DS}/task-",
                   f"{DS}/dataset_description"):
        for k, s in list_keys(prefix):
            if k.endswith("/"):
                continue
            rel, ok, _ = _fetch_one(k, s, dest_root)
            if ok:
                got.append(rel)
    return got


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="*")
    ap.add_argument("--top-level", action="store_true", help="fetch phenotype/ etc.")
    ap.add_argument("--list-only", action="store_true")
    a = ap.parse_args()
    if a.top_level:
        got = fetch_top_level()
        print(f"top-level: {len(got)} files")
    for sub in a.subjects:
        if a.list_only:
            keys = [(k, s) for k, s in list_keys(f"{DS}/{sub}/") if wanted(k)]
            print(f"{sub}: {len(keys)} files, {sum(s for _, s in keys)/2**30:.2f} GiB")
            continue
        r = fetch_subject(sub)
        print(f"{sub}: {'ok' if r['ok'] else 'FAILED'} "
              f"{r.get('n_files')} files {r.get('bytes',0)/2**30:.2f} GiB "
              f"{r.get('failures') or ''}", flush=True)


if __name__ == "__main__":
    main()
