"""Evidence packet rendering."""

from __future__ import annotations

from antma.schema import EvidencePacket


def render_evidence_packet(packet: EvidencePacket) -> str:
    criteria = "\n".join(f"- {item}" for item in packet.criteria)
    evidence = "\n".join(
        f"- {item.label}: {item.result} ({item.evidence})" for item in packet.evidence
    )
    return f"""# Evidence Packet

Created: {packet.created_at}
Status: {packet.status}

## Objective

{packet.objective}

## Completion Criteria

{criteria}

## Evidence

{evidence}

## Remaining Risk

{packet.remaining_risk}

## Next Action

{packet.next_action}
"""

