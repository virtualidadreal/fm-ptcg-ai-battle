# sabrina_kb_draw — prize-belief-aware draw guard (anti deck-out)

Fork de `sabrina_v1` que añade **una sola palanca**: una guarda de robo *prize-belief-aware*
sobre las jugadas de robo **opcionales**, para atacar el modo de derrota dominante de este
mazo, el **DECK-OUT** (millearnos a 0 con una mano potencialmente letal en mano,
Powerful Hand = 20×mano).

`deck.csv` es **byte-idéntico** a `sabrina_v1` (1 palanca = solo lógica). El scaffolding de
hardening (contrato `agent(obs, config=None) -> list[int]`, doble `try/except` global,
`_legal_fallback` repetición-safe, `_validate_obj` como gate final, carga de módulo
no-raising) es **verbatim** del estándar campeón.

## La palanca (una variable, detrás de flag)

`main.py`: `KB_DRAW_GUARD = True`. Ponlo a `False` y el comportamiento vuelve a ser
**equivalente byte a byte** a `sabrina_v1` (la guarda se vuelve un no-op).

`sabrina_v1` ya preserva el mazo cuando va **GANANDO** (`_deck_preserve`: mano grande que ya
hace KO + mazo bajo). Esta palanca cubre **la otra mitad** del loop de deck-out: dejar de robar
opcionalmente cuando

1. el mazo está **genuinamente bajo** (`deckCount <= KB_DECK_FLOOR = 9`), **y**
2. ya tenemos un **atacante que puede actuar** (`_have_attacker`), **y**
3. la creencia bayesiana de que **TODAS las piezas clave NO están premiadas** supera el umbral
   (`prob_all_key_pieces_safe >= KB_SAFE_THRESHOLD = 0.85`).

Si se cumplen las tres, cada robo **opcional** (la copia banca de Run Away Draw de Dudunsparce,
y los supporters de robo/búsqueda Hilda/Dawn/Poké Pad) deja de tener upside de win-con y pasa a
ser **riesgo puro de deck-out** → la guarda lo apaga (devuelve `-1`).

### Por qué es un NUDGE acotado y reversible (no un rewrite)

- **Solo apaga robo OPCIONAL.** Nunca toca ataques, evoluciones, attach de energía, gusting ni
  reposicionamiento (la copia ACTIVE de Run Away Draw que recoloca para atacar sigue intacta).
- **Estrictamente MÁS conservadora que v1.** Solo puede hacernos robar **menos**, nunca más, y
  solo dentro de la misma banda de mazo-bajo que v1 ya vigila. No introduce agresión nueva.
- **Nunca dispara mientras todavía necesitamos cavar.** Si la creencia es baja (pieza clave
  probablemente premiada o aún no localizada) la guarda NO actúa → se mantiene el robo agresivo
  de v1. Solo frena cuando seguir robando no aporta nada a la win-con.
- **Override de utilidad:** si robar este turno alcanza letal en el Activo (`draw_for_ko`), ese
  robo tiene upside claro y **anula** la guarda — no se concede tempo en un turno de kill.
- Cualquier fallo en la matemática de creencia → `except` → se comporta exactamente como v1.

## La heurística del Knowledge OS de la que sale

Sale de la **heurística #4** de `knowledge/synthesis/heuristicas-computables.md`
("Belief-state de cartas premiadas — `prize-checking`", prioridad P1):

> mantén `prize_belief[card_id]` sobre tus propios premios ocultos; **hipergeométrica sobre el
> pool no visto, no sobre 60 fijo**.

Implementación exacta (la fórmula directa verificada vs lastlegume en la ficha, NO los
porcentajes redondeados naive):

```python
def prob_at_least_one_prized(copies, prizes_remaining, unknown_pool):
    if copies >= unknown_pool: return 1.0
    return 1 - comb(unknown_pool - copies, prizes_remaining) / comb(unknown_pool, prizes_remaining)
```

`unknown_pool = deck + premios propios aún boca abajo` (la mano/descarte/tablero son zonas
conocidas: una copia localizada ahí NO está premiada). Recomputado en cada decisión con
`unknown_pool` decreciente, como pide la ficha.

### Archetype-AGNOSTIC (objetivo "mejor jugador de PTCG", no solo Alakazam)

El módulo `PrizeBeliefModel` es **puro conteo**: recibe `deck_count`, `prizes_remaining`,
`known_counts` y una lista de piezas clave `[(card_id, target_count), ...]`, y responde
`prob_all_key_pieces_safe()`. **No contiene ninguna lógica de Alakazam** → es reutilizable por
un agente general de PTCG. La única parte específica del arquetipo (qué ids son "pieza clave":
para Alakazam el atacante `743` y el motor de robo Dudunsparce `66`) vive en la policy y se
**pasa al modelo** vía `_kb_key_pieces()`. Para otro mazo, cambias esa lista y nada más.

## Smoke test (motor cabt, local, vía Docker)

Validado end-to-end en el contenedor `ptcg-cabt` (12 partidas pareadas kb vs v1, asientos
alternados):

- **0 crashes, 0 invalids:** `policy_ok=831`, `policy_fallback=0`, `obs_fallback=0`,
  `fallback_rate=0.0`, `deck_ok=True`, `errors={}`.
- **La palanca está viva:** `kb_guard_fires=99` (dispara en la banda de mazo-bajo como se diseñó;
  no es código muerto).
- **WR vs v1 = 42% (5W/7L/0D)** — *direccional, N pequeño, dentro de ruido*. ⚠️ **NO es señal de
  veto:** cabt es anti-predictivo del ladder (Spearman −0.80). Una bajada de cabt NO es evidencia
  de que el cambio sea malo. El ladder es el único juez.

## Protocolo de A/B (dev aumentado)

1. **Filtro local (DIRECTIONAL)**, pareado vs `sabrina_v1`, asientos alternados, N≥60. Métrica
   clave de decisión = **tasa de deck-out propio** (el modo que esta palanca ataca), no el WR
   bruto. Comando exacto (desde la raíz del repo, con colima + Docker `ptcg-cabt` vivos):

   ```bash
   docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work/ptcg-abc ptcg-cabt \
     python tools/cabt_ab.py ../agents_official/sabrina_kb_draw ../agents_official/sabrina_v1 60
   ```

   (`cabt_ab.py` resuelve dirs relativos a `ptcg-abc/`, por eso `../agents_official/...`.
   Reporta el WR de A = kb_draw vs B = v1.)

2. 🚫 **NO vetar por una caída de cabt** — anti-predictivo del ladder. Mira la tasa de deck-out,
   no el WR de cabt.
3. **El ladder es el único juez.** Si el filtro local no muestra regresión en deck-out,
   `bash build_submission.sh` y subir (decisión de Fran), 1 cambio/día, manteniendo
   `sabrina_v1` (y Dragapult/Leon v1) como suelo verificado en la otra ranura.

## Scope honesto (no inflar)

Ataca el **deck-out yendo empatados/ganando** con atacante en juego y piezas clave NO premiadas.
NO toca las derrotas por carrera de premios pura ni por falta de daño. Es un nudge de tempo
conservador: el riesgo es ceder un robo en una banda tardía estrecha; el upside es no millearnos
a 0 con la partida ganable. Complementario a `sabrina_trev1` (que sube el buffer de
`_deck_preserve`): esta palanca usa **creencia sobre premios**, no un offset fijo, y se mantiene
**archetype-agnostic** para la base de "mejor jugador de PTCG".
