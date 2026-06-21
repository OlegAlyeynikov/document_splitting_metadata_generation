from __future__ import annotations

import logging

from .models import PageInfo, Segment

logger = logging.getLogger(__name__)

_LABEL_FATTURA = "Fattura"
_LABEL_ALTRO = "Altro"
_LABEL_UNCLASSIFIED = "unclassified"

_MODE_DISCARD = "discard"
_MODE_SPLIT = "split"
_MODE_GROUP = "group"


def compute_segments(
    filename: str,
    page_map: dict[int, PageInfo],
    altro_mode: str,
    total_pdf_pages: int,
) -> list[Segment]:
    segments: list[Segment] = []

    current_invoice_pages: list[int] = []
    current_invoice_num: str | None = None

    # Pages that appear before the first Fattura page; transferred to the first invoice.
    # Without this buffer, they would create a ghost invoice segment with invoice_num=None.
    pre_invoice_pages: list[int] = []

    altro_run_pages: list[int] = []
    altro_group_pages: list[int] = []

    part_counter = 0
    altro_part_counter = 0

    def close_invoice() -> None:
        nonlocal current_invoice_pages, current_invoice_num, part_counter
        if not current_invoice_pages:
            return
        part_counter += 1
        segments.append(
            Segment(
                source_file=filename,
                pages=tuple(current_invoice_pages),
                segment_type="invoice",
                invoice_num=current_invoice_num,
                part_index=part_counter,
            )
        )
        current_invoice_pages = []
        current_invoice_num = None

    def close_altro_run() -> None:
        nonlocal altro_run_pages, altro_part_counter
        if not altro_run_pages:
            return
        altro_part_counter += 1
        segments.append(
            Segment(
                source_file=filename,
                pages=tuple(altro_run_pages),
                segment_type="altro",
                invoice_num=None,
                part_index=altro_part_counter,
            )
        )
        altro_run_pages = []

    for page_num in range(1, total_pdf_pages + 1):
        info = page_map.get(page_num, PageInfo(label=_LABEL_UNCLASSIFIED, invoice_num=None))

        if info.label == _LABEL_FATTURA:
            invoice_num = info.invoice_num

            if invoice_num is None:
                logger.warning(
                    "%s page %d: Fattura page without 'Numero fattura' — "
                    "attached to current invoice (%r)",
                    filename,
                    page_num,
                    current_invoice_num,
                )
                current_invoice_pages.append(page_num)

            elif invoice_num != current_invoice_num:
                close_invoice()
                if altro_mode == _MODE_SPLIT:
                    close_altro_run()
                current_invoice_num = invoice_num
                # Prepend any pages that arrived before the first invoice
                if pre_invoice_pages:
                    current_invoice_pages = pre_invoice_pages
                    pre_invoice_pages = []
                current_invoice_pages.append(page_num)

            else:
                current_invoice_pages.append(page_num)

        elif info.label == _LABEL_ALTRO:
            if altro_mode == _MODE_DISCARD:
                continue
            elif altro_mode == _MODE_SPLIT:
                altro_run_pages.append(page_num)
            elif altro_mode == _MODE_GROUP:
                altro_group_pages.append(page_num)

        else:
            if info.label != _LABEL_UNCLASSIFIED:
                logger.warning(
                    "%s page %d: unknown label %r — treated as unclassified",
                    filename,
                    page_num,
                    info.label,
                )
            else:
                logger.warning(
                    "%s page %d: not in Excel — attached to current segment",
                    filename,
                    page_num,
                )
            if current_invoice_num is None:
                pre_invoice_pages.append(page_num)
            else:
                current_invoice_pages.append(page_num)

    close_invoice()
    if altro_mode == _MODE_SPLIT:
        close_altro_run()

    # Pages that existed before any Fattura and no invoice ever opened
    if pre_invoice_pages:
        segments.append(
            Segment(
                source_file=filename,
                pages=tuple(pre_invoice_pages),
                segment_type="unclassified",
                invoice_num=None,
                part_index=1,
            )
        )

    if altro_mode == _MODE_GROUP and altro_group_pages:
        segments.append(
            Segment(
                source_file=filename,
                pages=tuple(altro_group_pages),
                segment_type="altro",
                invoice_num=None,
                part_index=1,
            )
        )

    if not segments:
        logger.warning("%s: no segments produced — file may have no Fattura pages", filename)

    return segments
