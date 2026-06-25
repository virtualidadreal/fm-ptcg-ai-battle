# Bucle de divergencia — el motor de mejora del pilotaje

> Por qué existe: no estamos atascados por falta de ideas, sino porque **no tenemos
> un juez local fiable**. La señal de score local está REFUTADA (μ−3σ vs media; cabt
> anti-predictivo −0.80). Pero la **divergencia decisión-a-decisión vs keidroid (#1)**
> sí es un diagnóstico útil: te dice *en qué jugadas concretas pilotamos distinto al
> mejor*. Es lo que cazó el bug de Salvatore — esto lo hace sistemático.

## Qué NO es
- NO es un predictor del ladder. Cerrar divergencia ≠ subir score garantizado
  (v2 incorporó un insight "mejor" y EMPEORÓ: 722 < 826). Úsalo como **diagnóstico
  cualitativo de bugs/huecos de pilotaje**, nunca como gate de subida.
- El único juez de subida sigue siendo el **ladder convergido** (días, μ−3σ).

## El ciclo (una vuelta)
1. **Medir** — `tools/run_divergence.sh agents_official/mega_starmie_v1 116`
   → `research/divergence/keidroid_mega_starmie_v1_<fecha>.txt`.
   Los contextos salen ordenados por agree% ASC: **los de arriba = donde más divergimos**.
2. **Leer** — por cada contexto con agree% bajo, mira el bloque:
   - `HUMAN picked` (lo que hizo keidroid) vs `WE picked instead` (lo nuestro).
   - `DISAMBIGUATED by board state` desglosa los YES/NO por estado de tablero.
   - `examples (human || ours [board])` = casos concretos.
   - Ignora cualquier carta con sufijo `*MISMATCH`: es divergencia por lista distinta
     (otro piloto), NO error de pilotaje nuestro.
3. **Diagnosticar** — ¿es un bug (como Salvatore), un hueco de regla, o juicio
   "BC-shaped" (difícil)? Solo los dos primeros son código seguro.
4. **Parchear** — un cambio acotado en `agents_official/mega_starmie_v1/main.py`,
   preservando el gate `_validate_obj` y los fallbacks (0 crashes es sagrado).
5. **Re-medir** — vuelve a (1) y confirma que ese contexto sube de agree%
   (señal de que ahora jugamos como keidroid ahí). NO es prueba de ladder, es prueba
   de que el parche hace lo que querías.
6. **Subir 1 cambio/día** al ladder con v1 (826.9) de suelo en la otra ranura, y
   leer la convergencia en días. Ese es el juez real.

## Gotchas (de ptcg-abc/CLAUDE.md, no re-aprender a la mala)
- **Archetype exacto**: el decode filtra por `ma.dk(deck)`. El runner lo auto-resuelve
  con un probe (clasifica el mazo de keidroid antes de correr). Si sale agree 0/0,
  el archetype está mal.
- **Nunca `| tail`**: los contextos salen por agree% ASC → tail tira justo los peores
  (donde más divergimos). Por eso el runner escribe a archivo.
- **No paralelizar decodes**: CPU pileup → cuelga colima (4CPU). El runner aborta si
  detecta otro decode vivo.
- **Mide el agente PARCHEADO**: correr el decode contra el agente viejo no sirve.

## Foco esperado (del análisis previo)
El gap vive en **SETUP** (búsquedas, orden de supporters, mulligan), no en combate.
Contextos a vigilar primero: `MAIN`, `MULLIGAN` (=42), `SETUP_ACTIVE`, `SETUP_BENCH`,
`TO_HAND`, `ATTACH_TO`. El combate (ATTACK) colapsa a aritmética de HP y diverge poco.
