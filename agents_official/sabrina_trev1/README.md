# sabrina_trev1 — anti-deckout buffer A/B (vs Hop's Trevenant)

Fork de `sabrina_v1` que cambia **una sola variable** para atacar el matchup de mayor cuota del campo (Hop's Trevenant, 34% del meta, estábamos a la par 49%).

## El cambio (una variable)
`main.py:360`, método `_deck_preserve`:
```
deck_low = self.me.deckCount <= remaining_prizes + 4   # sabrina_v1
deck_low = self.me.deckCount <= remaining_prizes + 8   # sabrina_trev1
```
`deck.csv` **byte-idéntico a sabrina_v1** (variable aislada). Es el único diff del repo.

## Por qué (evidencia de replays del piloto top)
Minería de los 7 replays del piloto top de Alakazam (THIRD PTCG Club) + verificación adversarial directa: **perdemos vs Trevenant por nuestro propio deck-out**, no por falta de daño. En 2 de las 4 derrotas vs Trevenant íbamos **ganando** la carrera de premios (rival a 4-5 premios restantes) y nos milleamos a 0 con una mano letal en mano (Powerful Hand = 20×hand). Trevenant es un muro de grind (Horrifying Revenge castiga el KO con +100; Phantump Splashing Dodge alarga), y nuestro motor de robo quema ~8 cartas en un turno pesado.

**Valor +8 (derivado, no a ojo):** el peor turno-pesado observado quema ~8 cartas, así que +8 absorbe el peor "misfire" exacto. Nuestro deck millea ~33% más lento que el del piloto top (8 supporters de robo vs 12, sin Lillie's, + recuperación Battle Cage/Sacred Ash/Night Stretcher), así que +8 deja colchón sano mientras roba ~2 turnos más que +10. +4/+6 reproducen los deck-outs observados; +10 es seguro pero sobre-conservador para nuestro deck durable.

**Seguridad en matchups rápidos:** el gate `big_hand` (sin tocar) solo deja preservar cuando la mano actual YA hace KO al activo. Contra ex de HP alta (Dragapult ~320, Mega Lucario ~340) como activo, `big_hand` es falso y el robo sigue ON. No hay pérdida de daño; el único riesgo es una concesión leve de tempo en una banda tardía estrecha vs aggro.

## Protocolo de A/B (dev aumentado)
1. **Filtro local (DIRECTIONAL)**: pareado vs `sabrina_v1`, mismas seeds, N≥60. Métricas de decisión = **(a) tasa de deck-out propio** y **(b) WR desglosado Trevenant vs NO-Trevenant** por separado.
2. 🚫 **NO vetar por una caída de cabt** — cabt es anti-predictivo del ladder (Spearman −0.80). Una bajada de cabt no es evidencia de que el cambio sea malo.
3. **El ladder es el único juez.** Si el filtro local no muestra regresión en deck-out ni en el cohort NO-Trevenant, `bash build_submission.sh` y subir (decisión de Fran), 1 cambio/día, manteniendo `sabrina_v1` como suelo en la otra ranura.

## Scope honesto (no inflar)
Rescata **~2 de las 4** derrotas vs Trevenant (las de deck-out yendo ganando), **no** convierte el 0-4 en 4-0. Las otras derrotas se pierden en la **carrera de premios** (bucle Horrifying Revenge rompe nuestro atacante y nos quedamos sin segundo cierre). El **lever complementario** (siguiente candidato, otra variable, otro día): mantener un **segundo Alakazam cargado en banca + energía de recambio** para sobrevivir al bucle y no perder tempo tras cada KO castigado. No hay ninguna victoria del piloto top vs Trevenant en la muestra → la "línea ganadora vs Trevenant" sigue siendo hipótesis.
