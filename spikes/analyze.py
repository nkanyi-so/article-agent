"""Reads the saved spike responses and measures what Phase 1 set out to learn.

Needs no SDK, no key and no network:  python3 spikes/analyze.py
Writes spikes/results/summary.json and prints a table.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

RESULTS = Path(__file__).resolve().parent / "results"

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
QUOTED = re.compile(r"[\"“]([^\"”]{8,})[\"”]")
SENTENCE = re.compile(r"[^.?!]+[.?!]+")
# A capitalised word that does not start a sentence: a rough stand-in for "proper name".
# Used for the block-level pass only, where a block is a fragment and its first word is
# usually an ordinary word. The sentence-level pass uses `names_in` below.
NAME = re.compile(r"(?<![.?!]\s)(?<!^)\b[A-Z][a-z]+\b")
CAPITALISED = re.compile(r"\b[A-Z][a-z]+\b")
# Ordinary words that open a sentence. A sentence's first word counts as a name unless it is
# one of these, so "Tennant said..." is checked and "The two differ..." is not.
OPENERS = {
    "A", "According", "After", "All", "Also", "An", "And", "As", "Asked", "At", "Before", "Both",
    "But", "By", "Each", "Every", "Fertiliser", "For", "From", "He", "Head", "Her", "His", "However", "If",
    "In", "It", "Its", "Looking", "Meanwhile", "Most", "Next", "No", "Nobody", "Not", "Now", "Of", "On",
    "One", "Operations", "Other", "Previously", "Responding", "She", "Since", "So", "Some", "That", "The",
    "Their", "There", "These", "They", "This", "Those", "Three", "To", "Two", "Under", "When",
    "Where", "While", "With", "Yield",
}  # fmt: skip
MONTHS = {
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
}  # fmt: skip


def names_in(sentence: str) -> list[str]:
    found = CAPITALISED.findall(sentence)
    first = CAPITALISED.match(sentence.lstrip("\"“"))
    if first and first.group() in OPENERS:
        found = found[1:]
    return [n for n in found if n not in MONTHS]


def norm_number(raw: str) -> str:
    return raw.replace(",", "").rstrip(".")


def words(text: str) -> int:
    return len(text.split())


def cited_text(block: dict[str, Any]) -> str:
    return " ".join(c["cited_text"] for c in block["citations"])


def analyse_draft(saved: dict[str, Any]) -> dict[str, Any]:
    response = saved["response"]
    content = response["content"]
    usage = response["usage"]
    text_blocks = [b for b in content if b["type"] == "text"]
    cited = [b for b in text_blocks if b.get("citations")]
    uncited = [b for b in text_blocks if not b.get("citations")]
    uncited_wordy = [b for b in uncited if b["text"].strip()]
    article = "".join(b["text"] for b in text_blocks)
    headline = article.strip().split("\n", 1)[0]

    # Is any part of the headline line inside a cited block?
    seen = ""
    headline_cited = False
    for block in text_blocks:
        if "\n" in seen.lstrip():
            break
        if block.get("citations") and block["text"].strip():
            headline_cited = True
        seen += block["text"]

    number_fail, quote_fail, name_fail = [], [], []
    for block in cited:
        source = cited_text(block)
        source_numbers = {norm_number(n) for n in NUMBER.findall(source)}
        missing = [n for n in NUMBER.findall(block["text"]) if norm_number(n) not in source_numbers]
        if missing:
            number_fail.append({"text": block["text"].strip(), "missing": missing})
        for quote in QUOTED.findall(block["text"]):
            if quote.rstrip(".,") not in source:
                quote_fail.append({"text": block["text"].strip(), "quote": quote})
        missing_names = [
            n for n in NAME.findall(block["text"]) if n not in source and n not in MONTHS
        ]
        if missing_names:
            name_fail.append({"text": block["text"].strip(), "missing": missing_names})

    spans = [c["end_block_index"] - c["start_block_index"] for b in cited for c in b["citations"]]
    return {
        "label": saved["label"],
        "model_served": response["model"],
        "stop_reason": response["stop_reason"],
        "effort": saved["request"]["output_config"]["effort"],
        "thinking_requested": saved["request"]["thinking"]["type"],
        "thinking_blocks": sum(1 for b in content if b["type"] == "thinking"),
        "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cost_usd": saved["cost_usd"],
        "latency_s": saved["latency_s"],
        "article_words": words(article),
        "paragraphs": len([p for p in article.strip().split("\n\n") if p.strip()]) - 1,
        "text_blocks": len(text_blocks),
        "cited_blocks": len(cited),
        "uncited_blocks_with_words": len(uncited_wordy),
        "uncited_blocks_whitespace_only": len(uncited) - len(uncited_wordy),
        "share_of_words_uncited": round(sum(words(b["text"]) for b in uncited_wordy) / max(words(article), 1), 3),
        "headline": headline,
        "headline_cited": headline_cited,
        "sentences_per_cited_block_max": max((len(SENTENCE.findall(b["text"])) or 1) for b in cited),
        "cited_blocks_with_more_than_one_sentence": sum(1 for b in cited if len(SENTENCE.findall(b["text"])) > 1),
        "citations_per_cited_block_mean": round(statistics.mean(len(b["citations"]) for b in cited), 2),
        "span_blocks_max": max(spans),
        "span_blocks_mean": round(statistics.mean(spans), 2),
        "cited_text_words_mean": round(statistics.mean(words(cited_text(b)) for b in cited), 1),
        "cited_text_words_max": max(words(cited_text(b)) for b in cited),
        "cited_blocks_failing_number_check": number_fail,
        "cited_blocks_failing_quote_check": quote_fail,
        "cited_blocks_failing_name_check": name_fail,
        "uncited_text": [b["text"].strip() for b in uncited_wordy],
        "mentions_4800": [
            s.strip() for s in re.split(r"(?<=[.?!])\s+|\n+", article) if "4,800" in s
        ],
    }


def main() -> None:
    drafts = [
        analyse_draft(json.loads(p.read_text())) for p in sorted((RESULTS / "draft").glob("*.json"))
    ]
    others = []
    for kind in ("extract", "judge", "check400"):
        for path in sorted((RESULTS / kind).glob("*.json")):
            saved = json.loads(path.read_text())
            row: dict[str, Any] = {"kind": kind, "label": saved["label"], "cost_usd": saved["cost_usd"], "latency_s": saved["latency_s"]}
            if "response" in saved:
                usage = saved["response"]["usage"]
                row |= {
                    "model_served": saved["response"]["model"],
                    "stop_reason": saved["response"]["stop_reason"],
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
                }
            else:
                row |= {"error": saved["error"]}
            others.append(row)
    total = sum(d["cost_usd"] for d in drafts) + sum(o["cost_usd"] for o in others)
    summary = {"total_cost_usd": round(total, 4), "drafts": drafts, "other_calls": others}
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    head = "label | think tok | words | cited | uncited(words) | uncited share | headline cited | >1 sent | max span | cited words mean/max | num fail | name fail | quote fail | $ | s"
    print(head)
    for d in drafts:
        print(
            f"{d['label']} | {d['thinking_tokens']} | {d['article_words']} | {d['cited_blocks']} | "
            f"{d['uncited_blocks_with_words']} | {d['share_of_words_uncited']} | {d['headline_cited']} | "
            f"{d['cited_blocks_with_more_than_one_sentence']} | {d['span_blocks_max']} | "
            f"{d['cited_text_words_mean']}/{d['cited_text_words_max']} | "
            f"{len(d['cited_blocks_failing_number_check'])} | {len(d['cited_blocks_failing_name_check'])} | "
            f"{len(d['cited_blocks_failing_quote_check'])} | {d['cost_usd']:.4f} | {d['latency_s']}"
        )
    for o in others:
        print(o)
    print(f"total ${total:.4f}")




# ---------------------------------------------------------------- sentence as the unit
#
# The block-level numbers above treat one response text block as the unit. The responses show
# that a block is usually part of a sentence (an uncited "Vance said" followed by a cited
# clause), so this second pass asks what the ground check would do if the unit were the sentence.
#
# It applies two of the four rules in decisions/0003, roughly:
#   rule 1: the sentence overlaps at least one cited block;
#   rule 2: every number, and every capitalised word taken as a name, appears in the cited text.
#           Dates are checked through their digits only; month names are skipped.
# Rule 3 (quotations verbatim) is measured in the block-level pass. Rule 4 (corrections) is not
# implemented here; the transcript-2 drafts were read by hand for it.

SENTENCE_SPLIT = re.compile(r"(?:(?<=[.?!])|(?<=[.?!][\"”]))\s+(?=[A-Z\"“])")


def sentence_view(saved: dict[str, Any]) -> dict[str, Any]:
    blocks = [b for b in saved["response"]["content"] if b["type"] == "text"]
    article = "".join(b["text"] for b in blocks)
    title = saved["request"]["messages"][0]["content"][0]["title"]
    # Character range of each block in the article.
    ranges, pos = [], 0
    for block in blocks:
        ranges.append((pos, pos + len(block["text"]), block))
        pos += len(block["text"])

    body_start = article.index("\n") if "\n" in article else 0
    rows = []
    for para_match in re.finditer(r"[^\n]+", article[body_start:]):
        para_offset = body_start + para_match.start()
        cursor = 0
        for part in SENTENCE_SPLIT.split(para_match.group()):
            start = para_offset + para_match.group().index(part, cursor)
            end = start + len(part)
            cursor = end - para_offset
            cited_blocks = [b for (s, e, b) in ranges if b.get("citations") and s < end and e > start]
            source = " ".join(cited_text(b) for b in cited_blocks)
            source_numbers = {norm_number(n) for n in NUMBER.findall(source)}
            missing_numbers = [n for n in NUMBER.findall(part) if norm_number(n) not in source_numbers]
            missing_names = [n for n in names_in(part) if n not in source]
            missing_names_title_ok = [n for n in missing_names if n not in title]
            rows.append(
                {
                    "text": part,
                    "words": words(part),
                    "cited": bool(cited_blocks),
                    "missing_numbers": missing_numbers,
                    "missing_names": missing_names,
                    "missing_names_if_title_counts": missing_names_title_ok,
                }
            )

    def kept(row: dict[str, Any], title_counts: bool) -> bool:
        names = row["missing_names_if_title_counts"] if title_counts else row["missing_names"]
        return row["cited"] and not row["missing_numbers"] and not names

    total_words = sum(r["words"] for r in rows) or 1
    return {
        "label": saved["label"],
        "sentences": len(rows),
        "sentences_with_no_citation": sum(1 for r in rows if not r["cited"]),
        "sentences_failing_numbers": sum(1 for r in rows if r["cited"] and r["missing_numbers"]),
        "sentences_failing_names": sum(1 for r in rows if r["cited"] and r["missing_names"]),
        "sentences_failing_names_if_title_counts": sum(
            1 for r in rows if r["cited"] and r["missing_names_if_title_counts"]
        ),
        "kept_strict": sum(1 for r in rows if kept(r, False)),
        "kept_if_title_counts": sum(1 for r in rows if kept(r, True)),
        "words_kept_strict_share": round(sum(r["words"] for r in rows if kept(r, False)) / total_words, 3),
        "words_kept_if_title_counts_share": round(sum(r["words"] for r in rows if kept(r, True)) / total_words, 3),
        "removed_strict": [
            {k: r[k] for k in ("text", "cited", "missing_numbers", "missing_names")}
            for r in rows
            if not kept(r, False)
        ],
    }


def sentence_main() -> None:
    views = [sentence_view(json.loads(p.read_text())) for p in sorted((RESULTS / "draft").glob("*.json"))]
    summary_path = RESULTS / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["sentence_unit"] = views
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print("\nSentence as the unit")
    print("label | sentences | no citation | fail numbers | fail names | fail names (title counts) | kept strict | kept (title counts) | words kept strict | words kept (title counts)")
    for v in views:
        print(
            f"{v['label']} | {v['sentences']} | {v['sentences_with_no_citation']} | {v['sentences_failing_numbers']} | "
            f"{v['sentences_failing_names']} | {v['sentences_failing_names_if_title_counts']} | {v['kept_strict']} | "
            f"{v['kept_if_title_counts']} | {v['words_kept_strict_share']} | {v['words_kept_if_title_counts_share']}"
        )


if __name__ == "__main__":
    main()
    sentence_main()
