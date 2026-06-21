from __future__ import annotations

from pipeline.models import PageInfo
from pipeline.segmentation import compute_segments


def _pmap(entries: dict[int, tuple[str, str | None]]) -> dict[int, PageInfo]:
    return {page: PageInfo(label=label, invoice_num=inv) for page, (label, inv) in entries.items()}


# --- discard mode ---

def test_discard_removes_altro_pages():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Altro", None),
        3: ("Fattura", "INV-2"),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 3)
    assert len(segs) == 2
    assert segs[0].pages == (1,)
    assert segs[1].pages == (3,)
    assert all(s.segment_type == "invoice" for s in segs)


def test_discard_keeps_unclassified_attached():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Fattura", "INV-2"),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 4)
    assert segs[0].pages == (1,)
    assert segs[1].pages == (2, 3, 4)


# --- split mode ---

def test_split_altro_becomes_own_segment():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Altro", None),
        3: ("Altro", None),
        4: ("Fattura", "INV-2"),
    })
    segs = compute_segments("f.pdf", page_map, "split", 4)
    invoice_segs = [s for s in segs if s.segment_type == "invoice"]
    altro_segs = [s for s in segs if s.segment_type == "altro"]
    assert len(invoice_segs) == 2
    assert len(altro_segs) == 1
    assert altro_segs[0].pages == (2, 3)


def test_split_multiple_altro_runs():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Altro", None),
        3: ("Fattura", "INV-2"),
        4: ("Altro", None),
        5: ("Altro", None),
    })
    segs = compute_segments("f.pdf", page_map, "split", 5)
    altro_segs = [s for s in segs if s.segment_type == "altro"]
    assert len(altro_segs) == 2
    assert altro_segs[0].pages == (2,)
    assert altro_segs[1].pages == (4, 5)


# --- group mode ---

def test_group_all_altro_in_one_segment():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Altro", None),
        3: ("Fattura", "INV-2"),
        4: ("Altro", None),
        5: ("Altro", None),
    })
    segs = compute_segments("f.pdf", page_map, "group", 5)
    altro_segs = [s for s in segs if s.segment_type == "altro"]
    assert len(altro_segs) == 1
    assert altro_segs[0].pages == (2, 4, 5)


def test_group_no_altro_pages_no_altro_segment():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Fattura", "INV-2"),
    })
    segs = compute_segments("f.pdf", page_map, "group", 2)
    assert all(s.segment_type == "invoice" for s in segs)


# --- edge cases ---

def test_fattura_without_invoice_num_attached_to_current():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Fattura", None),
        3: ("Fattura", "INV-2"),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 3)
    assert segs[0].pages == (1, 2)
    assert segs[0].invoice_num == "INV-1"
    assert segs[1].pages == (3,)


def test_file_with_no_fattura_pages_returns_empty():
    page_map = _pmap({
        1: ("Altro", None),
        2: ("Altro", None),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 2)
    assert segs == []


def test_file_starting_with_altro_split_mode():
    page_map = _pmap({
        1: ("Altro", None),
        2: ("Fattura", "INV-1"),
    })
    segs = compute_segments("f.pdf", page_map, "split", 2)
    altro_segs = [s for s in segs if s.segment_type == "altro"]
    assert altro_segs[0].pages == (1,)


def test_part_index_increments_per_invoice():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Fattura", "INV-2"),
        3: ("Fattura", "INV-3"),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 3)
    assert [s.part_index for s in segs] == [1, 2, 3]


def test_same_invoice_num_multipage_stays_one_segment():
    page_map = _pmap({
        1: ("Fattura", "INV-1"),
        2: ("Fattura", "INV-1"),
        3: ("Fattura", "INV-2"),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 3)
    assert len(segs) == 2
    assert segs[0].pages == (1, 2)


def test_unclassified_before_first_invoice_no_ghost_segment():
    # page 1 not in Excel, page 2 is first Fattura — must NOT produce a ghost invoice segment
    page_map = _pmap({
        2: ("Fattura", "INV-1"),
    })
    segs = compute_segments("f.pdf", page_map, "discard", 3)
    invoice_segs = [s for s in segs if s.segment_type == "invoice"]
    assert len(invoice_segs) == 1
    assert invoice_segs[0].invoice_num == "INV-1"
    assert 1 in invoice_segs[0].pages  # pre-invoice page attached to first invoice
    assert 2 in invoice_segs[0].pages


def test_unclassified_only_no_invoice_produces_unclassified_segment():
    # PDF with no classified pages at all
    page_map: dict = {}
    segs = compute_segments("f.pdf", page_map, "discard", 2)
    unclassified_segs = [s for s in segs if s.segment_type == "unclassified"]
    assert len(unclassified_segs) == 1
    assert unclassified_segs[0].pages == (1, 2)
