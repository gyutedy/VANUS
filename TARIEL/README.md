# TARIEL — orchestrateur

Coordonne. Ne calcule pas. Ne parse pas. N'alerte pas.

| Fichier | Role |
|---|---|
| `CODEBASE/tariel.py` | poll + subprocess des fregates |
| `CODEBASE/gates.py` | portes lecture / alerte |
| `CODEBASE/run.py` | `--once` ou boucle |

Portes : lecture (F00→F05) / alerte (F03 OUT → F04). L'humain reste le dernier mot pour parier.
