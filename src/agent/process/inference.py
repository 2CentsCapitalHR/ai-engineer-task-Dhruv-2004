from __future__ import annotations

from collections import Counter
from typing import List


def infer_process(doc_types: List[str]) -> str:
    counts = Counter(doc_types)

    # AoA Amendment flow
    if counts["Shareholder Resolution"] >= 1 and counts["Articles of Association"] >= 1:
        return "AoA Amendment"

    # Company incorporation
    if (
        counts["Articles of Association"] >= 1
        and (counts["Shareholder Resolution"] >= 1 or counts["Board Resolution"] >= 1)
    ) or counts["Incorporation Application Form"] >= 1:
        return "Company Incorporation (Private Company)"

    # Employment compliance
    if counts["Employment Contract"] >= 1:
        return "Employment Compliance"

    # Data protection
    if counts["Appropriate Policy Document"] >= 1:
        return "Data Protection Compliance"

    return "Unknown"
