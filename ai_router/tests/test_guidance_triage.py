"""Unit tests for the Set 064 D6 backlog-triage helper
(:mod:`ai_router.guidance_triage`).

Covers the deterministic surface -- block extraction over a mixed
``##``/``###`` file (the real day-one over-budget shape), JSON response
parsing (clean, fenced, malformed, out-of-range, duplicate, merge
without target), size projection, the reference-graph archive guard, and
ASCII-only rendering -- plus the batched, truncation-aware
:func:`run_triage` driver with an injected fake ``route_fn`` (no paid
calls).

Bare-filename imports per the package test convention.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

import pytest

import guidance_triage as gt
from guidance_triage import (
    ARCHIVE,
    DROP,
    KEEP,
    MERGE,
    PROMOTE,
    Block,
    Classification,
    build_reference_graph,
    build_triage_prompt,
    extract_blocks,
    flag_referenced_archives,
    parse_triage_response,
    project_size,
    render_report,
    run_triage,
)


# A mixed-heading file like the harvester's: a preamble, two ## section
# headers, ### lessons under them, and one ## lesson synced from canonical
# (with a D2 trailer). #### sub-points inside a lesson stay in its block.
MIXED = """# Lessons Learned

> Purpose preamble line.
> Read before every session.

## Seeded Lessons

Intro prose for the section.

### Do Not Run Build And Test In Parallel

- **Context:** Windows worktree.
- **Lesson:** Run them sequentially.

### Old COM Quirk That Was Fixed

- **Context:** legacy subsystem now retired.

#### A sub-point under the COM lesson

still part of the COM block.

## Harvester-Specific Lessons

### Probe Output Value Earlier

- **Lesson:** Validate substrates before sinking budget.

## A Synced Portable Lesson
<!-- lesson: id="L-064-1" added-set="030" last-used-set="064" status="active" scope="portable" -->

- **Lesson:** Persist routed output before display.
"""


def test_extract_blocks_handles_mixed_h2_h3_and_preamble():
    ext = extract_blocks(MIXED, min_level=2, max_level=3)
    titles = [b.title for b in ext.blocks]
    assert titles == [
        "Seeded Lessons",
        "Do Not Run Build And Test In Parallel",
        "Old COM Quirk That Was Fixed",
        "Harvester-Specific Lessons",
        "Probe Output Value Earlier",
        "A Synced Portable Lesson",
    ]
    # Preamble is everything before the first ## heading.
    assert "Purpose preamble line." in ext.preamble
    assert ext.preamble_char_size > 0
    # Levels recorded correctly (## = 2, ### = 3).
    levels = {b.title: b.level for b in ext.blocks}
    assert levels["Seeded Lessons"] == 2
    assert levels["Do Not Run Build And Test In Parallel"] == 3


def test_extract_blocks_keeps_h4_subpoints_inside_their_lesson():
    ext = extract_blocks(MIXED)
    com = next(b for b in ext.blocks if b.title == "Old COM Quirk That Was Fixed")
    # The #### sub-point is NOT its own block; it stays in the COM block text.
    assert "A sub-point under the COM lesson" in com.text
    assert "still part of the COM block." in com.text


def test_extract_blocks_parses_existing_trailer():
    ext = extract_blocks(MIXED)
    synced = next(b for b in ext.blocks if b.title == "A Synced Portable Lesson")
    assert synced.meta is not None
    assert synced.meta.id == "L-064-1"
    # A no-trailer day-one lesson has meta None.
    probe = next(b for b in ext.blocks if b.title == "Probe Output Value Earlier")
    assert probe.meta is None


def test_extract_blocks_char_and_byte_sizes():
    ext = extract_blocks(MIXED)
    b = ext.blocks[0]
    assert b.char_size == len(b.text)
    assert b.byte_size == len(b.text.encode("utf-8"))


def test_extract_blocks_no_headings_returns_all_preamble():
    ext = extract_blocks("# Title only\n\njust prose, no level-2 headings\n")
    assert ext.blocks == []
    assert "just prose" in ext.preamble


def test_extract_blocks_size_accounting_is_exact():
    # The byte-exact partition invariant: preamble + every block re-create
    # the source length with no dropped boundary newline (the D1 fix).
    ext = extract_blocks(MIXED)
    total = ext.preamble_char_size + sum(b.char_size for b in ext.blocks)
    assert total == len(MIXED)
    # And the concatenation reproduces the original text exactly.
    assert ext.preamble + "".join(b.text for b in ext.blocks) == MIXED


def test_extract_blocks_size_accounting_exact_without_trailing_newline():
    text = "pre\n## A\n\n- body\n## B\n\n- body2"  # no trailing newline
    ext = extract_blocks(text)
    total = ext.preamble_char_size + sum(b.char_size for b in ext.blocks)
    assert total == len(text)
    assert ext.preamble + "".join(b.text for b in ext.blocks) == text


# --- response parsing --------------------------------------------------------


def _valid_response(n: int) -> str:
    return json.dumps(
        [
            {
                "index": i,
                "classification": KEEP,
                "reason_code": "live",
                "merge_target": None,
                "rationale": "still relevant",
                "confidence": "high",
            }
            for i in range(n)
        ]
    )


def test_parse_clean_response():
    cls, errs = parse_triage_response(_valid_response(3), frozenset({0, 1, 2}))
    assert errs == []
    assert [c.index for c in cls] == [0, 1, 2]
    assert all(c.classification == KEEP for c in cls)


def test_parse_fenced_response_with_prose():
    raw = "Here is the triage:\n```json\n" + _valid_response(1) + "\n```\nDone."
    cls, errs = parse_triage_response(raw, frozenset({0}))
    assert errs == []
    assert len(cls) == 1


def test_parse_unparseable_response():
    cls, errs = parse_triage_response("no json here at all", frozenset({0}))
    assert cls == []
    assert errs and "unparseable" in errs[0]


def test_parse_rejects_out_of_range_and_bad_class_and_duplicate():
    raw = json.dumps(
        [
            {"index": 0, "classification": KEEP},
            {"index": 9, "classification": KEEP},            # out of range
            {"index": 1, "classification": "frobnicate"},     # bad class
            {"index": 0, "classification": ARCHIVE},          # duplicate
        ]
    )
    cls, errs = parse_triage_response(raw, frozenset({0, 1}))
    assert [c.index for c in cls] == [0]
    joined = " ".join(errs)
    assert "out of range" in joined
    assert "invalid classification" in joined
    assert "duplicate" in joined


def test_parse_merge_without_target_is_rejected_not_kept():
    # A merge with no valid target cannot be acted on; it must NOT remain a
    # returned MERGE (that would make the projection over-optimistic). It is
    # dropped so the block falls through to unclassified -> retained.
    raw = json.dumps([{"index": 0, "classification": MERGE, "merge_target": None}])
    cls, errs = parse_triage_response(raw, frozenset({0}))
    assert cls == []
    assert any("valid merge_target" in e for e in errs)


def test_parse_merge_to_self_is_rejected():
    raw = json.dumps([{"index": 0, "classification": MERGE, "merge_target": 0}])
    cls, errs = parse_triage_response(raw, frozenset({0}))
    assert cls == []
    assert any("itself" in e for e in errs)


def test_parse_valid_merge_is_kept():
    raw = json.dumps([{"index": 1, "classification": MERGE, "merge_target": 0}])
    cls, errs = parse_triage_response(raw, frozenset({0, 1}))
    assert len(cls) == 1 and cls[0].merge_target == 0
    assert errs == []


# --- projection --------------------------------------------------------------


def _blocks(sizes: List[int]) -> gt.Extraction:
    blocks = [
        Block(index=i, level=3, title=f"L{i}", text="x" * s, char_size=s, byte_size=s)
        for i, s in enumerate(sizes)
    ]
    return gt.Extraction(preamble="P" * 100, preamble_char_size=100, preamble_byte_size=100, blocks=blocks)


def test_project_size_keep_archive_promote_merge_drop():
    ext = _blocks([1000, 1000, 1000, 1000, 1000])
    cls = [
        Classification(0, KEEP),
        Classification(1, ARCHIVE),
        Classification(2, PROMOTE),
        Classification(3, MERGE, merge_target=0),
        Classification(4, DROP),
    ]
    proj = project_size(ext, cls, ceiling_tokens=10000, pointer_chars=500)
    # current = preamble(100) + 5*1000 = 5100
    assert proj.current_chars == 5100
    # projected = preamble(100) + keep(1000) + 1 promote pointer(500) = 1600
    assert proj.projected_chars == 1600
    assert proj.counts[KEEP] == 1
    assert proj.counts[ARCHIVE] == 1
    assert proj.counts[PROMOTE] == 1
    assert proj.counts[MERGE] == 1
    assert proj.counts[DROP] == 1


def test_project_size_unclassified_is_retained_conservatively():
    ext = _blocks([1000, 1000])
    proj = project_size(ext, [Classification(0, KEEP)], ceiling_tokens=10000)
    # block 1 unclassified -> retained at full size
    assert proj.counts["unclassified"] == 1
    assert proj.projected_chars == 100 + 1000 + 1000


def test_project_size_merge_without_target_is_retained_defensively():
    # Even if a merge-without-target slips past the parser, project_size
    # must retain it rather than over-count the savings.
    ext = _blocks([1000, 1000])
    cls = [Classification(0, KEEP), Classification(1, MERGE, merge_target=None)]
    proj = project_size(ext, cls, ceiling_tokens=10000)
    assert proj.projected_chars == 100 + 1000 + 1000  # block 1 retained
    # A valid merge (target set) DOES remove the block.
    cls2 = [Classification(0, KEEP), Classification(1, MERGE, merge_target=0)]
    proj2 = project_size(ext, cls2, ceiling_tokens=10000)
    assert proj2.projected_chars == 100 + 1000


def test_project_size_merge_into_nonsurviving_target_is_retained():
    # A merge only saves bytes if it folds into a SURVIVING block.
    ext = _blocks([1000, 1000, 1000])
    # block 2 merges into an out-of-range target -> retained
    cls = [
        Classification(0, KEEP),
        Classification(1, ARCHIVE),
        Classification(2, MERGE, merge_target=99),
    ]
    proj = project_size(ext, cls, ceiling_tokens=10000)
    assert proj.projected_chars == 100 + 1000 + 1000  # block 0 + block 2 retained
    # block 2 merges into block 1, which is ITSELF archived -> retained
    cls2 = [
        Classification(0, KEEP),
        Classification(1, ARCHIVE),
        Classification(2, MERGE, merge_target=1),
    ]
    proj2 = project_size(ext, cls2, ceiling_tokens=10000)
    assert proj2.projected_chars == 100 + 1000 + 1000
    # block 2 merges into surviving block 0 -> removed
    cls3 = [
        Classification(0, KEEP),
        Classification(1, ARCHIVE),
        Classification(2, MERGE, merge_target=0),
    ]
    proj3 = project_size(ext, cls3, ceiling_tokens=10000)
    assert proj3.projected_chars == 100 + 1000


def test_projection_over_ceiling_flags():
    ext = _blocks([60000])  # ~15000 tokens, over a 10000 ceiling
    proj_keep = project_size(ext, [Classification(0, KEEP)], ceiling_tokens=10000)
    assert proj_keep.over_ceiling_before is True
    assert proj_keep.over_ceiling_after is True
    proj_archive = project_size(ext, [Classification(0, ARCHIVE)], ceiling_tokens=10000)
    assert proj_archive.over_ceiling_after is False


# --- reference graph + archive guard ----------------------------------------


def test_reference_graph_and_flag_referenced_archive():
    ext = extract_blocks(MIXED)
    pg = "Some project guidance text mentioning L-064-1 as a convention."
    refs = build_reference_graph(ext.blocks, pg)
    assert "project-guidance.md" in refs["L-064-1"]
    # Propose archiving the referenced synced lesson -> flagged.
    synced_idx = next(b.index for b in ext.blocks if b.title == "A Synced Portable Lesson")
    flags = flag_referenced_archives(
        ext, [Classification(synced_idx, ARCHIVE)], refs
    )
    assert any("L-064-1" in f and "project-guidance.md" in f for f in flags)


def test_no_flag_when_no_ids():
    # Day-one no-trailer file: build_reference_graph is empty, nothing flagged.
    text = "# L\n\n## A Lesson\n\n- body\n"
    ext = extract_blocks(text)
    refs = build_reference_graph(ext.blocks, "")
    assert refs == {}
    flags = flag_referenced_archives(ext, [Classification(0, ARCHIVE)], refs)
    assert flags == []


# --- rendering ---------------------------------------------------------------


def test_render_report_folds_real_non_ascii_titles_for_stdout():
    # Real over-budget files carry em-dashes / arrows in titles. The
    # rendered report keeps them (UTF-8 file), but the stdout-facing fold
    # (_to_ascii) must be safe for a cp1252 console.
    text = "# L\n\n## Notify The Human — Consider Switching\n\n- body\n"
    ext = extract_blocks(text)
    cls = [Classification(0, KEEP, confidence="high")]
    proj = project_size(ext, cls, ceiling_tokens=10000)
    report = render_report(ext, cls, proj, [], [], "lessons-learned.md")
    # The report itself preserves the em-dash (UTF-8 fidelity)...
    assert "—" in report
    # ...but the stdout fold is pure ASCII and never raises.
    folded = gt._to_ascii(report)
    folded.encode("ascii")
    assert "—" not in folded
    assert "Counts:" in folded
    assert "archive != delete" in folded
    assert "PROPOSAL" in folded or "PROPOSED" in folded


def test_to_ascii_replaces_non_encodable():
    assert gt._to_ascii("a—b→c") == "a?b?c"


def test_flag_referenced_archive_ignores_reference_from_removed_block():
    # L-2 references L-1 via superseded-by, but L-2 is itself being
    # archived -> that reference is NOT a live conflict.
    text = (
        "# L\n\n"
        '## One\n<!-- lesson: id="L-064-1" status="active" -->\n\n- body\n'
        '## Two\n<!-- lesson: id="L-064-2" status="active" superseded-by="L-064-1" -->\n\n- body\n'
    )
    ext = extract_blocks(text)
    refs = build_reference_graph(ext.blocks, "")
    assert "L-064-2" in refs["L-064-1"]
    # Archive BOTH: the only reference to L-1 comes from L-2, which is also
    # removed -> no live conflict for L-1.
    cls = [Classification(0, ARCHIVE), Classification(1, ARCHIVE)]
    flags = flag_referenced_archives(ext, cls, refs)
    assert flags == []
    # But if L-2 survives (keep-active), archiving L-1 IS a live conflict.
    cls2 = [Classification(0, ARCHIVE), Classification(1, KEEP)]
    flags2 = flag_referenced_archives(ext, cls2, refs)
    assert any("L-064-1" in f for f in flags2)


def test_reference_graph_token_match_avoids_id_prefix_false_positive():
    text = "# L\n\n## One\n<!-- lesson: id=\"L-064-1\" status=\"active\" -->\n\n- body\n"
    ext = extract_blocks(text)
    # project-guidance mentions L-064-12, NOT L-064-1; must not match.
    refs = build_reference_graph(ext.blocks, "see L-064-12 for details")
    assert refs["L-064-1"] == []
    refs2 = build_reference_graph(ext.blocks, "the rule L-064-1 applies")
    assert "project-guidance.md" in refs2["L-064-1"]


# --- batched, truncation-aware driver ---------------------------------------


@dataclass
class FakeRR:
    content: str
    truncated: bool = False
    total_cost_usd: float = 0.01
    model_name: str = "fake-model"


class _Recorder:
    """A fake route_fn that records prompts and returns canned responses."""

    def __init__(self, responder):
        self.responder = responder
        self.calls: List[str] = []

    def __call__(self, content, task_type, max_tier=3, session_set=None, complexity_hint=None):
        self.calls.append(content)
        return self.responder(content)


def test_run_triage_single_batch(monkeypatch):
    ext = _blocks([100, 100, 100])

    def respond(prompt):
        # Classify whatever indices are present in the prompt.
        idxs = [int(s.split()[0]) for s in prompt.split("BLOCK ")[1:]]
        return FakeRR(content=_resp_for(idxs))

    rec = _Recorder(respond)
    run = run_triage(ext, route_fn=rec, batch_size=25)
    assert sorted(c.index for c in run.classifications) == [0, 1, 2]
    assert run.parse_errors == []
    assert len(rec.calls) == 1  # all three fit one batch
    assert run.total_cost_usd == pytest.approx(0.01)
    assert run.models_used == ["fake-model"]


def test_run_triage_respects_batch_size():
    ext = _blocks([100, 100, 100, 100, 100])

    def respond(prompt):
        idxs = [int(s.split()[0]) for s in prompt.split("BLOCK ")[1:]]
        return FakeRR(content=_resp_for(idxs))

    rec = _Recorder(respond)
    run = run_triage(ext, route_fn=rec, batch_size=2)
    assert sorted(c.index for c in run.classifications) == [0, 1, 2, 3, 4]
    assert len(rec.calls) == 3  # 2 + 2 + 1


def test_run_triage_splits_on_truncation():
    ext = _blocks([100, 100, 100, 100])

    def respond(prompt):
        idxs = [int(s.split()[0]) for s in prompt.split("BLOCK ")[1:]]
        # Truncate any multi-block batch; succeed only at size 1.
        if len(idxs) > 1:
            return FakeRR(content="[", truncated=True)  # truncated, unparseable
        return FakeRR(content=_resp_for(idxs))

    rec = _Recorder(respond)
    run = run_triage(ext, route_fn=rec, batch_size=25)
    assert sorted(c.index for c in run.classifications) == [0, 1, 2, 3]
    # Each leaf is a single-block call; the recursion produced > 1 raw response.
    assert len(run.raw_responses) > 1


def test_run_triage_reports_unclassified_blocks():
    ext = _blocks([100, 100])

    def respond(prompt):
        # Only ever classify index 0, drop the rest.
        return FakeRR(content=_resp_for([0]))

    rec = _Recorder(respond)
    run = run_triage(ext, route_fn=rec, batch_size=25)
    assert any("no classification returned" in e for e in run.parse_errors)


def _resp_for(idxs: List[int]) -> str:
    return json.dumps(
        [{"index": i, "classification": KEEP, "confidence": "high"} for i in idxs]
    )


def test_build_triage_prompt_lists_every_block_and_excerpts():
    ext = _blocks([5000])
    prompt = build_triage_prompt(ext.blocks, excerpt_chars=100)
    assert "BLOCK 0" in prompt
    assert "truncated for triage" in prompt  # 5000 > 100 excerpt cap
    assert "keep-active" in prompt and "merge_target" in prompt
