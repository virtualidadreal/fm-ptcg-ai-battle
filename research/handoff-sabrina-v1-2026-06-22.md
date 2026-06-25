# HANDOFF → construir el pivote rule-based (2 líneas) — para la sesión que prepara los agentes (2026-06-22)

> Pegar/leer en la sesión que construye los agentes. Esta sesión (selección + minería de replays del ladder)
> deja TODO verificado con disciplina Dev Aumentado. Detalle largo en:
> - `research/alakazam-top-pilot-analisis-2026-06-22.md` (Alakazam, top-6 del ladder)
> - `research/megastarmie-keidroid-analisis-2026-06-22.md` (Mega Starmie ex, #1 del ladder)
> Léelos enteros antes de codear.

## Plan de slots (decisión de dirección)
El mirror Dragapult rule-based está techado (paridad, todos corren el mismo sample). Pivotamos a **2 líneas rule-based
complementarias**, una por ranura del ladder (5 envíos/día, cuentan los 2 últimos). Dragapult (Leon v1) al banco como suelo.

| Orden | Línea | Mazo | Por qué | Riesgo |
|---|---|---|---|---|
| **1º (construir primero)** | Mega Starmie | **Mega Starmie ex** (keidroid, #1 del ladder) | Piloto rule-based MÁS simple, #1 actual, cero deck-out, edge en las CARTAS → ROI más rápido | Brick de apertura; lo countera Alakazam |
| **2º** | Sabrina | **Alakazam** (THIRD PTCG Club, top-6) | Counter de Mega Starmie, perfil opuesto, cubre el campo | Deck-out; 0-4 vs Trevenant |

**Piedra-papel-tijera real:** Trevenant > Alakazam > Mega Starmie. Alakazam = 5/8 derrotas de Mega Starmie. Correr ambos cubre
más campo que duplicar uno. Nombres por `AGENTS.md` (trainer↔mazo); asignar al crear.

**Caveat clave:** el 67% de Mega Starmie es en parte off-meta no adaptado. Cuando el campo lo copie (es el #1), bajará.
Por eso Alakazam como 2º slot es el seguro, no un lujo.

---

# LÍNEA 1 — Mega Starmie ex (construir primero)

## Por qué gana 67% con un Mega ex de 3 premios (confirmado airtight)
Su Mega de **330 HP no muere** (cae 0-1 veces en victorias vs 2-4 en derrotas) → nunca entrega el bloque de 3 premios.
Muro intankable + agresión barata. NO es un motor de cura (eso es secundario). El plan es casi determinista.

## Decklist (confianza 100%, vista entera en 15 replays, idéntica en todas)
**POKÉMON:** 3x Mega Starmie ex (1031, 330HP, Stage1, prize 3) · 3x Staryu (1030) · 4x Cinderace (666, atacante 1-premio).
**ENERGÍA (13):** 9x Basic {W} · 4x Ignition Energy (17, Special = {C}{C}{C} sobre evoluciones).
**SUPPORTERS:** 4x Salvatore (1189) · 4x Wally's Compassion (1229) · 4x Lillie's Determination · 2x Hilda (1225) · 2x Harlequin (1223) · 1x Boss's Orders.
**ITEMS/TOOLS:** 4x Mega Signal (1145) · 4x Buddy-Buddy Poffin · 4x Crushing Hammer · 4x Pokégear 3.0 · 2x Night Stretcher · 1x Ultra Ball · 1x Hero's Cape (1159, Tool ACE SPEC, +100HP→430).
Es un mazo DUAL: cuerpos baratos de 1 premio (Cinderace/Staryu) hacen daño temprano antes de comprometer el Mega.

## Reglas de pilotaje confirmadas (encodear)
1. **Evolucionar a Mega Starmie en T2-T3 vía Salvatore** (evoluciona el turno que entra el Staryu). Mediana T3.
2. **Jetting Blow por defecto** (1 energía, 120 al activo + 50 snipe al banco). Presión barata + esculpe el banco rival.
3. **Nebula Beam (3E, 210) SOLO para one-shots de remate**, acelerado con Ignition Energy. Decisión por aritmética de HP: si 210 mata → Nebula; si no → Jetting Blow. (El árbol de ataque colapsa a 2 opciones.)
4. **Boss's Orders = carta de cierre** (arrastra banco rival para rematar la carrera de premios). Solo cuando vas a ganar.
5. **No jugar defensivo:** atacar cada turno, dejar que el 330HP tanquee. Wally's Compassion como red de seguridad.
6. **NO gestionar deck-out** (no lo sufre; deckCount mínimo ~18). Lillie's Determination y Harlequin reciclan mano al mazo.

## El reto real de Sabrina/Mega Starmie NO es el combate, es el SETUP
La táctica de ataque es casi determinista. Donde se gana o se pierde es en **no brickear la apertura**: robar Staryu + energía + evolución a tiempo. 3/8 derrotas son brick puro (el Staryu de 70HP muere antes de evolucionar). **Minimizar el brick-rate = la prioridad de pilotaje.** (Anomalía abierta: Cinderace entra activo T0 sin línea evolutiva; mecanismo probable = Mega Signal, texto no legible en el dataset. No bloquea construir.)

---

# LÍNEA 2 — Alakazam (Sabrina, construir después)

Referencia: `THIRD PTCG Club`, rank 6 del ladder, 1288.6, 62,2% WR, 390 partidas. Replays en `data/alakazam_analysis/`.

## Decklist (vista al 100%)
Línea **4-4-3 Alakazam + 3 Rare Candy**, single-prize puro (0 EX salvo 1 Fezandipiti ex), all-in motor de robo.
**11 cambios netos vs `ptcg-abc/agents/alakazam/deck.csv`** (aplicar sin reservas):
+4 Lillie's Determination (1227) · +3 Dunsparce Trading Places (305) / −4 Dunsparce Dig (65) · −4 Battle Cage (1264) ·
+1 Fezandipiti ex (140) · +1 Enriching Energy (13) · +1 Xerosic's Machinations (1197) · +1 Night Stretcher (1097) ·
−1 Dudunsparce (66) · −1 Enhanced Hammer (1081) · −1 Hero's Cape (1159).

## Reglas (12 confirmadas) y lo que NO encodear
Detalle por dimensión (apertura/ataque-prizetrade/sequencing) en el doc de análisis con evidencia replay+turno.
🛑 **NO encodear (refutado adversarialmente):**
- ❌ "Rare Candy como vía principal" → el top usa la **cadena Kadabra (6/10)**.
- ❌ "Robar al máximo siempre" → causa el **deck-out**, que es su modo de derrota dominante.
🔑 **El edge de Alakazam = no deckearse.** 4/5 derrotas del top son con mazo a 0, 2 yendo ganando 5-2 en premios. Si Sabrina gestiona el robo para no deckearse, bate al propio top en su punto débil. Y resolver el **0-4 vs Hop's Trevenant**.

---

# COMÚN A LAS DOS LÍNEAS

- **Reusar el scaffolding robusto del campeón** (`agents_official/dragapult_sample/` o `leon_v1_5_prizeaware/`): try/except doble, `_legal_fallback` repetición-safe, watchdog, deck loader cwd-safe. 0 crashes / 0 invalids es requisito.
- **Validar en A/B de LADDER REAL, no cabt** (el sim local NO predice el ladder, confirmado repetidamente).
- **Headroom = de PILOTAJE, no de deck** (las decklists ya son las correctas, vistas del top). En Mega Starmie el headroom es minimizar brick; en Alakazam, no deckearse.
- **Reparto de ficheros (no colisionar):** esta sesión escribió SOLO en `research/`, `data/alakazam_analysis/`, `data/megastarmie_analysis/` y ya terminó ahí. Vía libre para ti en `bcil/`, `agent_ismcts/` y los dirs nuevos (sugerencia `agents_official/mega_starmie_v1/` y `agents_official/sabrina_v1/`).
- **Disciplina de slots:** mantener SIEMPRE un agente validado en una de las 2 ranuras; promover candidatos solo tras A/B de ladder.
