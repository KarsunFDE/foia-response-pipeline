"""
index-foia-corpus.py — FOIA markdown corpus indexer (parse + chunk stage).

Reads FOIA authority markdown files, strips frontmatter, splits into
citation-traceable chunks, and writes JSONL for later Atlas insertion.

Corpus: docs/reference/foia/ is the authoritative managed corpus
(ADR-0003 + docs/retrieval-plan.md). The starter stubs at
data/seed/foia-precedent/ are frozen instructor-demo scaffolding — use
--corpus-dir to point at them only for demo purposes. Chunk-boundary
rules are specified in docs/corpus-chunking-rules.md.

Usage:
  python scripts/index-foia-corpus.py
  python scripts/index-foia-corpus.py --upsert --yes
  python scripts/index-foia-corpus.py --corpus-dir data/seed/foia-precedent \
      --out data/seed/foia-precedent-chunks.jsonl

Output JSONL schema per chunk:
  {
    "clause_id":    str,        # filename stem, e.g. "5usc552-a6A-time-limits"
    "cite":         str | null, # frontmatter cite field
    "title":        str | null, # H1 heading text
    "heading_path": list[str],  # breadcrumb from title → section label
    "far_part":     str | null, # "5 USC 552" or "28 CFR 16" derived from cite
    "agency_id":    str | null, # frontmatter agency_id; null = shared federal statute (all agencies)
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

# Overlap between forced sub-splits of a single over-limit paragraph, so a
# clause cut mid-thought stays retrievable from both sides.
CHUNK_OVERLAP_CHARS = 100

# Files to skip in the corpus directory.
SKIP_FILES = {"README.md"}

# Matches only the generator's provenance footer; legitimate trailing
# blockquotes (quoted statutory text) must survive.
STUB_FOOTER_RE = re.compile(r"^>\s*STARTER STUB\b")


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
    Remove only the '> STARTER STUB ...' provenance footer.

    Pops trailing blank lines and lines matching STUB_FOOTER_RE from the
    end of the text, stopping at the first non-blank line that does not
    match. Preserves legitimate trailing blockquotes (quoted statutory
    text), including ordinary '>' lines.
    """
    lines = text.splitlines()
    while lines:
        stripped = lines[-1].strip()
        if stripped == "" or STUB_FOOTER_RE.match(stripped):
            lines.pop()
        else:
            break
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

def _hard_split(text: str, max_chars: int, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """
    Force-split a single over-limit paragraph into chunks within max_chars.

    First tries sentence boundaries: sentences are greedily packed into
    chunks no larger than max_chars. Any single sentence that still exceeds
    max_chars falls back to a fixed character window — slices of max_chars
    stepping by (max_chars - overlap), so adjacent slices share `overlap`
    characters and a clause cut mid-sentence stays retrievable from both
    sides. Never returns an empty list; no returned chunk exceeds max_chars.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+", text) if s.strip()]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_len
        if current_parts:
            chunks.append(" ".join(current_parts))
            current_parts = []
            current_len = 0

    for sentence in sentences:
        if len(sentence) > max_chars:
            # Sentence alone busts the budget: emit any pending pack, then
            # slice this sentence with a sliding character window.
            flush()
            step = max(1, max_chars - overlap)
            for start in range(0, len(sentence), step):
                piece = sentence[start:start + max_chars].strip()
                if piece:
                    chunks.append(piece)
            continue
        # +1 for the space separator when joined.
        if current_len + len(sentence) + 1 > max_chars and current_parts:
            flush()
            current_parts = [sentence]
            current_len = len(sentence)
        else:
            current_parts.append(sentence)
            current_len += len(sentence) + 1

    flush()

    return [c for c in (chunk.strip() for chunk in chunks) if c] or [text.strip()]


def split_by_paragraphs(text: str, max_chars: int = MAX_SECTION_CHARS) -> list[str]:
    """
    Split text by blank-line paragraph boundaries when it exceeds max_chars.

    Returns the original text as a single-element list if it is short
    enough. Paragraphs that on their own exceed max_chars are hard-split at
    sentence then character boundaries with CHUNK_OVERLAP_CHARS overlap, so
    no returned chunk exceeds max_chars. Never returns an empty list.
    """
    if len(text) <= max_chars:
        return [text]

    raw_paras = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_len
        if current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_len = 0

    for para in raw_paras:
        para = para.strip()
        if not para:
            continue
        if len(para) > max_chars:
            # A single paragraph over the budget cannot ride along in a pack;
            # emit the pending pack, then hard-split this paragraph.
            flush()
            chunks.extend(_hard_split(para, max_chars))
            continue
        # +2 for the \n\n separator when joined.
        if current_len + len(para) + 2 > max_chars and current_parts:
            flush()
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para) + 2

    flush()

    return chunks or _hard_split(text, max_chars)


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
    # null agency_id = shared federal statute (visible to all agencies); a
    # value scopes the chunk to one agency (multi-tenant boundary, REQ-RAG-3).
    agency_id: str | None = fm.get("agency_id") or None
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
                    "agency_id": agency_id,
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
    On a partial bulk-write failure the run's documents are deleted (by
    run_id) and the error re-raised — the collection is left without the
    affected source files until a clean re-run.
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

    try:
        coll.bulk_write([pymongo.InsertOne(c) for c in stamped], ordered=False)
    except pymongo.errors.BulkWriteError as exc:
        # Partial inserts would leave a mixed old/new corpus (the run's old
        # source_file docs are already deleted). Remove everything this run
        # wrote, then surface the failure — a clean re-run re-indexes the
        # affected files in full.
        coll.delete_many({"run_id": run_id})
        write_errors = exc.details.get("writeErrors", []) if exc.details else []
        raise RuntimeError(
            f"bulk insert failed ({len(write_errors)} write error(s)); "
            f"cleaned up partial run {run_id}. First errors: {write_errors[:3]}"
        ) from exc

    coll.create_index([("text", pymongo.TEXT)], name="foia_text_search")
    return coll.count_documents({})


def validate_corpus_coverage(md_files: list[Path], chunks: list[dict]) -> list[str]:
    """
    Validate parsed chunks against the corpus file set (ingestion gate per
    docs/implementation-task-breakdown.md "Corpus ingestion and metadata").

    Returns a list of human-readable errors; empty list means the corpus
    parsed cleanly. Checks: every corpus file produced at least one chunk
    (a zero-chunk file is a silent drop from retrieval), every chunk
    references a file in the corpus set, and no chunk has empty text.
    """
    errors: list[str] = []
    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk["source_file"]] = counts.get(chunk["source_file"], 0) + 1

    for path in md_files:
        if counts.get(path.name, 0) == 0:
            errors.append(
                f"{path.name}: produced 0 chunks — file would silently "
                f"vanish from retrieval (parse failure or empty body)"
            )

    known = {p.name for p in md_files}
    for name in sorted(set(counts) - known):
        errors.append(f"{name}: chunk references a file outside the corpus set")

    for chunk in chunks:
        if not chunk.get("text", "").strip():
            errors.append(
                f"{chunk['source_file']}#{chunk['chunk_index']}: empty chunk text"
            )

    return errors


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    # Authoritative corpus home per ADR-0003; the data/seed stubs are frozen
    # demo scaffolding reachable via --corpus-dir.
    default_corpus = repo_root / "docs" / "reference" / "foia"
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

    # Ingestion gate — refuse to write anything (JSONL or Mongo) from a
    # corpus run that dropped files or produced empty chunks.
    validation_errors = validate_corpus_coverage(md_files, all_chunks)
    if validation_errors:
        for err in validation_errors:
            print(f"VALIDATION: {err}", file=sys.stderr)
        print(
            f"ERROR: corpus validation failed ({len(validation_errors)} "
            f"error(s)); nothing written.",
            file=sys.stderr,
        )
        sys.exit(1)

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
