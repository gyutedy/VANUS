#!/usr/bin/env python3
"""
WINNER ORDER — VANUS ne fait qu'ordonner les observations.
==========================================================
Trie et deduplique les matchs d'un slate par match_key, sans jamais
calculer une probabilite, un verdict ou une cote. Utilise par les
capteurs Winner basket/foot avant export du contrat vanus.slate.v1.
"""
from __future__ import annotations


def order_matches(matches, holes=None):
    """Liste de matchs -> (liste triee et deduplee, trous)."""
    out, seen = [], set()
    notes = list(holes or [])
    for m in sorted(matches or [], key=lambda x: (x.get("kickoff") or "", x.get("match_key") or "")):
        key = m.get("match_key")
        if not key:
            notes.append("match_key_absent")
            continue
        if key in seen:
            notes.append("doublon_ignore:" + key)
            continue
        seen.add(key)
        out.append(m)
    return out, notes


def build_slate(contract, index, sport, source, matches, holes=None, generated_at=None):
    """Contrat vanus.slate.v1 complet, ordonne. Aucune probabilite."""
    from winner_common import now_iso
    ordered, notes = order_matches(matches, holes)
    return {
        "contract": contract,
        "index": index,
        "sport": sport,
        "generated_at": generated_at or now_iso(),
        "source": source,
        "matches": ordered,
        "holes": list(dict.fromkeys(notes)),
    }
