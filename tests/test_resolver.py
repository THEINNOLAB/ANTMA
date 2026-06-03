from antma.resolver import resolve
from antma.schema import MemoryKind, MemoryRecord, MemoryStatus


def test_source_of_truth_outranks_external_backend():
    records = [
        MemoryRecord(
            id="external",
            kind=MemoryKind.EXTERNAL_BACKEND,
            title="Launch",
            body="launch decision",
            source="adapter",
            status=MemoryStatus.CURATED,
        ),
        MemoryRecord(
            id="truth",
            kind=MemoryKind.SOURCE_OF_TRUTH,
            title="Launch",
            body="launch decision",
            source="ssot/launch.md",
            status=MemoryStatus.CURATED,
        ),
    ]

    result = resolve(records, query="launch")

    assert result[0].id == "truth"

