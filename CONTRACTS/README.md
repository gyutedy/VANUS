# CONTRACTS — VANUS

Le vrai produit exportable. Un autre projet greffe VANUS en lisant ces schemas + `SHARED/OUT/signals/` (CELL/CIPHER lisent encore `F03_SPECULUM/OUT/`).

Changer un schema = versionner. Ne pas "ajouter un champ vite fait" dans un parseur.

| Schema | Producteur | Consommateur typique |
|---|---|---|
| `schema_slate.json` | F00 INFOCYTE | F01, F05 |
| `schema_match.json` | F01 SCRYER | F02, F05 |
| `schema_evolution.json` | F03 SPECULUM | F05, greffe externe |
| `schema_alert.json` | F03 SPECULUM | F04, F05 |
| `schema_blog.json` | F02 MNEMOS | F05 |
| `schema_signal.json` | F03 SPECULUM (`signals_export.py`) | greffe externe, PARI |

Attention : `schema_signal` n'est PAS une probabilite. Un `pick` PredictLix
reste une observation. Aucun consommateur ne peut le convertir en `p`
(HERESIE #7). Le graphe de decision reste dans le projet consommateur.

Les fichiers ici sont des **contrats**, pas des instances. Les instances vivent dans `OUT/` et `ARCHIVUM/`.
