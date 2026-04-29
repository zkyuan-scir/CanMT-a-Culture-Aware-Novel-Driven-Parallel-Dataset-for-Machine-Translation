# X-Cultural Translation Benchmark Public Seed Data

This release contains reconstructable seed metadata for a multilingual literary translation benchmark. It does **not** include full copyrighted source or target sentences. To reconstruct the benchmark text, users must provide their own lawful copies of the referenced books.

## Contents

```text
data/
  en2es.jsonl
  en2ja.jsonl
  en2zh.jsonl
  es2en.jsonl
  es2zh.jsonl
  ja2en.jsonl
  ja2zh.jsonl
  ru2zh.jsonl
  zh2en.jsonl
  zh2es.jsonl
  zh2ja.jsonl
  zh2ru.jsonl
manifest.json
README.md
README_zh.md
```

The release contains 1,470 records across 12 translation directions.

## JSONL Fields

Each line is a JSON object with:

- `id`: sample id within the original direction file.
- `src_lang`, `tgt_lang`: source and target language codes.
- `src_identifier`, `tgt_identifier`: book-version identifiers, such as ISBN-13, ISBN-10, or ASIN.
- `chapter_id`: 1-based chapter number in the prepared book JSON.
- `src_prefix`, `src_suffix`: compact-normalized source-side anchors.
- `src_anchor_chars`: number of compact characters used for each source anchor.
- `src_compact_chars`: optional compact source sentence length, present only when the maximum 20+20 anchors are still ambiguous.
- `tgt_prefix`, `tgt_suffix`: compact-normalized target-side anchors.
- `tgt_anchor_chars`: number of compact characters used for each target anchor.
- `tgt_compact_chars`: optional compact target sentence length, present only when the maximum 20+20 anchors are still ambiguous.
- `csi`: cultural-specific item(s) annotated for the sample.

## Normalization

Anchors are generated after applying this normalization:

1. Strip leading/trailing quote marks.
2. Apply Unicode NFKC normalization.
3. Remove all Unicode punctuation characters.
4. Remove all whitespace characters.

Anchor length counts characters after this compact normalization. The anchors do not contain punctuation or spaces.

Reference implementation:

```python
import unicodedata

QUOTE_CHARS = "\"'“”‘’«»‹›「」『』《》〈〉"
SPACE_TRANSLATION = str.maketrans({
    "\u00a0": " ",
    "\u1680": " ",
    "\u2000": " ",
    "\u2001": " ",
    "\u2002": " ",
    "\u2003": " ",
    "\u2004": " ",
    "\u2005": " ",
    "\u2006": " ",
    "\u2007": " ",
    "\u2008": " ",
    "\u2009": " ",
    "\u200a": " ",
    "\u202f": " ",
    "\u205f": " ",
    "\u3000": " ",
})

def strip_edge_quotes(text: str) -> str:
    stripped = str(text).strip()
    while True:
        next_stripped = stripped.strip(QUOTE_CHARS).strip()
        if next_stripped == stripped:
            return stripped
        stripped = next_stripped

def compact_normalize(text: str) -> str:
    text = strip_edge_quotes(text)
    text = unicodedata.normalize("NFKC", text).translate(SPACE_TRANSLATION)
    return "".join(
        ch for ch in text
        if not ch.isspace()
        and not unicodedata.category(ch).startswith("P")
    )
```

In this definition, quote marks are exactly the characters in `QUOTE_CHARS`. Unicode punctuation means any character whose Unicode category starts with `P`; hyphens and dashes are removed under this rule. Whitespace means Python `str.isspace()`, including tabs, newlines, non-breaking spaces, and full-width spaces after Unicode handling. Symbols and emoji are kept unless they are punctuation or whitespace. Japanese long vowel mark `ー` is kept because it is not Unicode punctuation.

## Chapter Ids

`chapter_id` is the 1-based chapter number copied from the internally prepared book JSON files, whose records have this schema:

```json
{
  "chapter_id": 1,
  "chapter_title": "CHAPTERI",
  "paragraph_id": 3,
  "text": "..."
}
```

For each `book_id`/language/chapter, the chapter text used for reconstruction is:

```python
" ".join(item["text"] for item in records if item["chapter_id"] == chapter_id)
```

using the original JSON order. `chapter_title` is metadata only; it is not separately added to the text unless the title also appears as a normal `text` record. Prologues, prefaces, afterwords, appendices, and multi-level structures such as part/chapter/section are treated as chapters only if they were assigned a 1-based `chapter_id` in the prepared JSON.

`manifest.json` contains `book_versions`, and each book version lists:

- `book_id`, `lang`, `identifier`, and `identifier_type`.
- all identifier candidates found in the metadata notes.
- `chapter_count`.

## Reconstruction

For each side (`src` or `tgt`):

1. Locate the book version using `*_identifier`.
2. Select `chapter_id`.
3. Normalize the chapter text using the rules above.
4. Find candidate spans that start with `*_prefix` and end with `*_suffix`.
5. If `*_compact_chars` is present, keep only candidates whose compact length equals that value.
6. The remaining candidate should be unique.

The anchors start at 5 compact characters per side, or the full compact sentence if it is shorter, and are automatically lengthened when needed. The configured maximum is 20 compact characters.

Candidate spans are defined on the compact-normalized full chapter text, not on pre-split sentences. No sentence tokenizer is required. The reference search procedure is:

```python
def recover_candidates(chapter_text: str, prefix: str, suffix: str) -> list[str]:
    candidates = []
    seen = set()
    start = chapter_text.find(prefix)
    while start != -1:
        suffix_start = chapter_text.find(suffix, start)
        if suffix_start != -1:
            candidate = chapter_text[start : suffix_start + len(suffix)]
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
        start = chapter_text.find(prefix, start + 1)
    return candidates
```

This recovers the compact sentence text. If you need an original-looking passage with punctuation and spacing, map the compact character offsets back to your local chapter text after reconstruction. Adjacent opening/closing quote marks may need to be expanded manually because edge quotes were intentionally removed from the anchor construction.

## Copyright Notice

This release provides identifiers and short normalized anchors only. It does not distribute full novel passages or full translations. Users are responsible for obtaining lawful copies of the referenced editions and for ensuring their own use complies with applicable law and license terms.
