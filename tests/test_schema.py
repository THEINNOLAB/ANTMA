from antma.schema import MemoryKind, MemoryRecord, MemoryStatus


def test_memory_record_serializes_enum_values():
    record = MemoryRecord(
        id="1",
        kind=MemoryKind.SOURCE_OF_TRUTH,
        title="Decision",
        body="The current decision is reviewed.",
        source="ssot/decision.md",
        status=MemoryStatus.CURATED,
        tags=("decision",),
    )

    data = record.to_dict()

    assert data["kind"] == "source_of_truth"
    assert data["status"] == "curated"
    assert data["tags"] == ["decision"]

