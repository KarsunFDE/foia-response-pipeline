"""
index-foia-corpus.py — FOIA markdown corpus indexer (parse + chunk stage).

Reads FOIA authority markdown files, strips frontmatter, splits into
citation-traceable chunks, and writes JSONL for later Atlas insertion.

NOTE: retrieval-plan.md mentions docs/reference/foia/ as the corpus dir;
that directory does not exist. The authoritative corpus seed is at
data/seed/foia-precedent/ per domain-mapping.md. Use --corpus-dir to
override when the expanded corpus path is created.

Usage:
  python scripts/index-foia-corpus.py
  python scripts/index-foia-corpus.py --corpus-dir docs/reference/foia
  python scripts/index-foia-corpus.py --corpus-dir data/seed/foia-precedent \
      --out data/seed/foia-precedent-chunks.jsonl

Output JSONL schema per chunk:
  {
    "clause_id":    str,        # filename stem, e.g. "5usc552-a6A-time-limits"
    "cite":         str | null, # frontmatter cite field
    "title":        str | null, # H1 heading text
    "heading_path": list[str],  # breadcrumb from title → section label
    "far_part":     str | null, # "5 USC 552" or "28 CFR 16" derived from cite
    "source_file":  str,        # filename, e.g. "5usc552-a6A-time-limits.md"
    "chunk_index":  int,        # 0-based position within the source file
    "topic":        str | null, # frontmatter topic or null
    "exemption":    str | null, # frontmatter exemption or null
    "text":         str,        # chunk body text (no frontmatter, no footer)
  }

No external dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Split a section into sub-chunks only if it exceeds this many characters.
# Keeps each chunk grounded to a precise regulatory passage.
MAX_SECTION_CHARS = 800

# Files to skip in the corpus directory.
SKIP_FILES = {"README.md"}


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split YAML frontmatter from body.

    Handles the --- delimited block at the top of file. Parses only
    simple key: value lines; does not handle nested YAML or multi-line
    values. Returns ({}, full_text) if no frontmatter found.
    """
    if not text.startswith("---"):
        return {}, text
    close = text.find("\n---", 3)
    if close == -1:
        return {}, text
    fm_block = text[3:close].strip()
    body = text[close + 4:].lstrip("\n")
    fm: dict = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, raw_val = line.partition(":")
        val: str | None = raw_val.strip()
        if val == "null" or val == "":
            val = None
        fm[key.strip()] = val
    return fm, body


# ---------------------------------------------------------------------------
# Body preparation
# ---------------------------------------------------------------------------

def extract_h1(body: str) -> tuple[str | None, str]:
    """
    Pull the first H1 heading from body.

    Returns (title_text, remaining_body). If no H1 found, returns
    (None, original_body).
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            remaining = "\n".join(lines[i + 1:]).lstrip("\n")
            return title, remaining
    return None, body


def strip_stub_footer(text: str) -> str:
    """
    Remove trailing blockquote lines (the '> STARTER STUB...' footer).

    Strips from the last contiguous run of '>' lines at the end of text.
    """
    lines = text.splitlines()
    while lines and lines[-1].strip().startswith(">"):
        lines.pop()
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

# Matches H2–H6 markdown headings.
_HEADING_RE = re.compile(r"^(#{2,})\s+(.+)$", re.MULTILINE)

# Matches paragraphs that open with a bold label, e.g. "**§ 16.5 (Timing).**"
# Used in 28 CFR files as inline section markers instead of proper headings.
_BOLD_LABEL_RE = re.compile(r"^\*\*([^*\n]+)\*\*", re.MULTILINE)


def _find_split_points(body: str) -> list[tuple[int, str]]:
    """
    Collect (char_offset, label) for every structural break in body.

    Structural breaks are H2+ headings and leading bold labels. Sorted
    by position so callers can slice sequentially.
    """
    points: list[tuple[int, str]] = []
    for m in _HEADING_RE.finditer(body):
        points.append((m.start(), m.group(2).strip()))
    for m in _BOLD_LABEL_RE.finditer(body):
        # Only treat as a section break if it starts a line (col 0).
        line_start = body.rfind("\n", 0, m.start()) + 1
        if m.start() == line_start:
            points.append((m.start(), m.group(1).strip()))
    points.sort(key=lambda x: x[0])
    # Deduplicate offsets that matched both patterns at the same position.
    seen: set[int] = set()
    deduped = []
    for offset, label in points:
        if offset not in seen:
            seen.add(offset)
            deduped.append((offset, label))
    return deduped


def split_into_sections(body: str) -> list[tuple[str, str]]:
    """
    Split body into [(section_label, section_text), ...].

    If no structural breaks are found, returns [("", body)].
    The section_text retains the full raw text of that section (including
    its heading line, so callers can normalise as needed).
    """
    points = _find_split_points(body)
    if not points:
        return [("", body)]

    sections: list[tuple[str, str]] = []

    # Text before the first section break.
    prefix = body[: points[0][0]].strip()
    if prefix:
        sections.append(("", prefix))

    for i, (start, label) in enumerate(points):
        end = points[i + 1][0] if i + 1 < len(points) else len(body)
        raw = body[start:end].strip()
        # Remove the heading marker line itself from the text so it is not
        # duplicated in the chunk (the label is preserved in heading_path).
        raw = _HEADING_RE.sub("", raw, count=1).strip()
        sections.append((label, raw))

    return sections


# ---------------------------------------------------------------------------
# Paragraph-level sub-chunking
# ---------------------------------------------------------------------------

def split_by_paragraphs(text: str, max_chars: int = MAX_SECTION_CHARS) -> list[str]:
    """
    Split text by blank-line paragraph boundaries when it exceeds max_chars.

    Returns the original text as a single-element list if it is short
    enough. Never returns an empty list.
    """
    if len(text) <= max_chars:
        return [text]

    raw_paras = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in raw_paras:
        para = para.strip()
        if not para:
            continue
        # +2 for the \n\n separator when joined.
        if current_len + len(para) + 2 > max_chars and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para) + 2

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks or [text]


# ---------------------------------------------------------------------------
# Metadata derivation
# ---------------------------------------------------------------------------

def derive_far_part(cite: str | None) -> str | None:
    """
    Return the top-level citation prefix from a cite string.

    "5 USC 552(a)(6)(A)" → "5 USC 552"
    "28 CFR 16.5–16.6"   → "28 CFR 16"
    Anything else         → null (do not guess)
    """
    if not cite:
        return None
    c = cite.upper()
    if "5 USC" in c:
        return "5 USC 552"
    if "28 CFR" in c:
        return "28 CFR 16"
    return None


# ---------------------------------------------------------------------------
# Per-file chunking
# ---------------------------------------------------------------------------

def chunk_file(path: Path) -> list[dict]:
    """
    Parse one FOIA markdown file and return a list of chunk dicts.

    Each dict is ready for JSONL output and later Atlas upsert.
    """
    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    title, body = extract_h1(body)
    body = strip_stub_footer(body)

    cite: str | None = fm.get("cite")
    topic: str | None = fm.get("topic") or None
    exemption: str | None = fm.get("exemption") or None
    far_part = derive_far_part(cite)
    clause_id = path.stem

    sections = split_into_sections(body)
    chunks: list[dict] = []
    chunk_index = 0

    for section_label, section_text in sections:
        if not section_text.strip():
            continue
        sub_chunks = split_by_paragraphs(section_text)
        heading_path = [h for h in (title, section_label or None) if h]

        for sub_text in sub_chunks:
            sub_text = sub_text.strip()
            if not sub_text:
                continue
            chunks.append(
                {
                    "clause_id": clause_id,
                    "cite": cite,
                    "title": title,
                    "heading_path": heading_path,
                    "far_part": far_part,
                    "source_file": path.name,
                    "chunk_index": chunk_index,
                    "topic": topic,
                    "exemption": exemption,
                    "text": sub_text,
                }
            )
            chunk_index += 1

    return chunks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _upsert_to_mongo(chunks: list[dict], mongo_url: str, db_name: str,
                     collection_name: str = "foia_precedent", *,
                     replace: bool = False) -> int:
    """
    Load chunks into the target collection, then create a text index.

    Delete-then-insert, scoped to the source files present in this run:
    stale chunks (a file that shrank from 5 chunks to 3, or whose content
    moved) are removed before the fresh chunks are inserted, so re-runs are
    idempotent for re-indexed files. Chunks from source files that were
    deleted or renamed since the last run are only removed by replace=True,
    which clears the entire collection first.

    Every document is stamped with a shared run_id (uuid4 hex) and an
    indexed_at UTC timestamp so a corpus run can be identified and audited.
    Returns the count of documents in the collection after the load.
    """
    import uuid
    from datetime import datetime, timezone

    import pymongo

    run_id = uuid.uuid4().hex
    indexed_at = datetime.now(timezone.utc).isoformat()
    stamped = [{**c, "run_id": run_id, "indexed_at": indexed_at} for c in chunks]

    client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
    coll = client[db_name][collection_name]

    if replace:
        coll.delete_many({})
    else:
        source_files = sorted({c["source_file"] for c in stamped})
        coll.delete_many({"source_file": {"$in": source_files}})

    coll.bulk_write([pymongo.InsertOne(c) for c in stamped], ordered=False)
    coll.create_index([("text", pymongo.TEXT)], name="foia_text_search")
    return coll.count_documents({})


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    default_corpus = repo_root / "data" / "seed" / "foia-precedent"
    default_out = repo_root / "data" / "seed" / "foia-precedent-chunks.jsonl"

    parser = argparse.ArgumentParser(
        description="Parse and chunk FOIA markdown corpus into JSONL."
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=default_corpus,
        help=f"Directory containing FOIA markdown files (default: {default_corpus})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help=f"Output JSONL path (default: {default_out})",
    )
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Load chunks into MongoDB and create text index. Requires --yes.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="With --upsert: clear the ENTIRE target collection before "
             "loading (removes chunks from deleted/renamed source files). "
             "Requires --yes.",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("MONGO_DB", "foia_response_pipeline"),
        help="Target MongoDB database (default: $MONGO_DB or foia_response_pipeline).",
    )
    parser.add_argument(
        "--collection",
        default="foia_precedent",
        help="Target MongoDB collection (default: foia_precedent).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm the MongoDB write. Without it, --upsert prints the "
             "target summary and exits without writing.",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Permit writing to a non-localhost MongoDB host. Refused "
             "otherwise so a stray MONGO_URL cannot hit a shared/production "
             "instance.",
    )
    args = parser.parse_args()

    corpus_dir: Path = args.corpus_dir
    out_path: Path = args.out

    if not corpus_dir.is_dir():
        print(f"ERROR: corpus dir not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(
        p for p in corpus_dir.glob("*.md") if p.name not in SKIP_FILES
    )
    if not md_files:
        print(f"WARNING: no markdown files found in {corpus_dir}", file=sys.stderr)
        sys.exit(0)

    all_chunks: list[dict] = []
    for path in md_files:
        file_chunks = chunk_file(path)
        all_chunks.extend(file_chunks)
        print(f"  {path.name}: {len(file_chunks)} chunk(s)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for chunk in all_chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\n{len(all_chunks)} chunks from {len(md_files)} files -> {out_path}")

    if args.replace and not args.upsert:
        print("ERROR: --replace only makes sense with --upsert", file=sys.stderr)
        sys.exit(2)

    if args.upsert:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://app:app_dev_password@localhost:27017")
        host = urlparse(mongo_url).hostname or "?"

        # Show exactly what would be written where BEFORE touching the DB —
        # the URL may carry credentials, so only the hostname is echoed.
        source_files = sorted({c["source_file"] for c in all_chunks})
        print(
            f"\nMongoDB write target:\n"
            f"  host:        {host}\n"
            f"  database:    {args.db}\n"
            f"  collection:  {args.collection}\n"
            f"  chunks:      {len(all_chunks)} from {len(source_files)} source file(s)\n"
            f"  mode:        {'REPLACE (clear entire collection first)' if args.replace else 'reindex listed source files only'}"
        )

        if host not in ("localhost", "127.0.0.1", "::1") and not args.allow_remote:
            print(
                f"ERROR: refusing to write to non-local MongoDB host {host!r} "
                f"without --allow-remote",
                file=sys.stderr,
            )
            sys.exit(2)

        if not args.yes:
            print(
                "Dry run — no write performed. Re-run with --yes to confirm.",
                file=sys.stderr,
            )
            sys.exit(0)

        try:
            count = _upsert_to_mongo(
                all_chunks, mongo_url, args.db, args.collection,
                replace=args.replace,
            )
            print(f"{count} documents in {args.db}.{args.collection}, text index created.")
        except Exception as exc:
            print(f"ERROR: upsert failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
