# 01 — PythonAnywhere

VANUS ne tourne pas sur GitHub Actions. Le nerf est `PA/`.

## Pieces (a venir, pas encore codees)

| Fichier | Role |
|---|---|
| `PA/pa_task.py` | Scheduled task. Reveille TARIEL. Ne parse pas. |
| `PA/pa_web.py` | WSGI. Sert F05 CELL seulement. |

## Contraintes hote

- Always-on = plan payant. Un scheduled task toutes les N minutes suffit.
- Un process web = la preview.
- Delai defaut 2 h, reglable, plancher 15–30 min.
- Secrets (Telegram, etc.) : env PythonAnywhere, jamais le git.

## Ce que PA n'est pas

Pas une fregate. Changer d'hote ne doit pas toucher F00–F05.
GitHub Actions : CI de tests plus tard, pas le poll de capture.
