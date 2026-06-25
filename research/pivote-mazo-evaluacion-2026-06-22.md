# Evaluación de pivote de mazo — ¿a qué arquetipo mover el agente rule-based? (2026-06-22)

> Pregunta: el mirror Dragapult rule-based está techado (todos corren el mismo sample = paridad).
> ¿Qué mazo del pool tiene MÁS headroom para un agente simple/rule-based?
> Veredicto: **PIVOTAR A ALAKAZAM** (sin quemar Dragapult como suelo). Dos estudios read-only convergen.

## Marco: qué hace a un mazo "rule-based friendly"

> Un rule-based no pierde por jugar mal el plan A; **pierde en las RAMAS**. Friendliness = nº de
> decisiones de alto impacto, dependientes del rival, que el mazo te obliga a acertar por partida.

Criterios por peso real en el motor cabt:
1. **Linealidad / profundidad del árbol** (altísimo) — menos ramas = menos divergencia del piloto top.
2. **Dependencia de info oculta / lectura de rival** (alto) — control y disrupción la necesitan; veneno para reglas.
3. **Consistencia / motor de robo** (alto) — si no arranca, ningún policy lo salva.
4. **Matemática de premios forgiving** (medio) — swings de 2 perdonan; trading single-prize fino castiga.
5. **Matchup spread en ladder ciego** (medio-alto) — spread plano sube Elo estable.
6. **Headroom** (el objetivo) — distancia entre lo que rinde tu policy HOY y el techo del arquetipo.

**Distinción clave (la descubrió ptcg-abc a las malas):** headroom de arquetipo ≠ friendliness de pilotaje.
Dragapult tiene 63% WR de arquetipo pero nuestro policy hand-rolled perdió **13-1** contra el sample,
porque Phantom Dive (colocar 6 contadores en banca para KOs múltiples) es justo el tipo de decisión
combinatoria que un rule-based pilota mal.

## Datos duros (de local, verificados)

- **Leaderboard** (`data/leaderboard_dl/...2026-06-22.csv`): 2.774 equipos. **Corte Top 8 ≈ 1257.** Fran = rank 931, score 774. Hay que ganar ~480 Elo.
- **Meta top-tier (Elo≥1150, vía `ptcg-abc/meta_analyze.py`):** Trevenant 42,2%/52,3% (↓) · Alakazam 18,9%/**55,1%** · Dragapult 16,5%/**63,1%** (↑) · Cinderace 3,8%/**67,2%** · Mega Froslass 3,6%/**70%** · Rocket's Mewtwo 1,9%/**75,4%** · Mega Lucario 0,4% (EXTINTO).
- **Matchups Dragapult:** gana Trevenant 79%, Chandelure 81%, Iono 80%; **par vs Alakazam (~50%)**; pierde Lucario 46% y **Cinderace 36%** (su único counter claro).
- **Mazos YA implementados** en `ptcg-abc/agents/`: dragapult (sample=campeón), **alakazam + alakazam_mist**, trevenant, bellibolt, typhlosion. Coste de pivote a Alakazam ≈ nulo (ya hay deck+scaffolding).
- **Ladder histórico nuestro:** Dragapult 774, Trevenant 879 (demoted), Bellibolt 836 (crashed), Alakazam 674, Typhlosion 532.

## Ranking de pivote

| # | Mazo | Friendliness | Headroom | Veredicto |
|---|---|---|---|---|
| **1** | **Alakazam** | ALTA | **ALTO** | **PIVOTAR AQUÍ** |
| 2 | Rocket's Mewtwo ex | media (?) | alto (?) | Investigar — 75% WR / 1,9% share = edge sin explotar, pero sin sample y 3 premios |
| 3 | Dragapult ex | media-baja | bajo (techo) | **Mantener como SUELO**, no apuesta de crecimiento |
| 4 | Trevenant | media-alta | dep. meta | Pivot dormido si el campo gira |
| 5 | Typhlosion | media | bajo | Friendly pero no competitivo (532) |
| 6 | Bellibolt | baja-media | bajo | Inestable + disrupción Iono anti-friendly |
| — | Lucario / Clefairy / Mega | varias | — | Extinto / anti-meta no lineal / sin sample |

## Por qué Alakazam (el argumento decisivo)

1. **Prueba EXTERNA directa de techo rule-based alto:** el kernel `rule-based-not-psychic-alakazam-best-5th`
   llegó al **TOP 5 del ladder Kaggle con Alakazam y SIN ML**. Dragapult no tiene ese precedente: su techo
   rule-based conocido es "paridad con el sample". Alguien ya demostró que un árbol de reglas pilota Alakazam al top.
2. **Headroom de PILOTAJE, no estructural:** nuestro Alakazam rinde 674 vs un arquetipo de 55,1% WR top-tier.
   Ese gap es recuperable mejorando policy. En Dragapult el gap a paridad ya está cerrado y el techo es estructural
   (todos corren la misma netdeck) → solo quedan micro-divergencias.
3. **Plan más lineal:** tempo/setup repetible ("monto y pego"), single-prize, no planificación espacial tipo Phantom Dive.
4. **Spread plano:** par vs Dragapult, gana a Lucario, 55% global → sube Elo estable en ladder ciego.
5. **Coste casi nulo:** ya hay `agents/alakazam` y `agents/alakazam_mist` locales. Es mejorar policy, no construir mazo.

## Honestidad sobre la incertidumbre

- **El sim local MIENTE** (lo grita ptcg-abc: Mist cabt 62% pero ladder 907<1006). Validar SIEMPRE en A/B de ladder real. Por eso este ranking se apoya en datos de ladder (WR top-tier + el kernel 5º), no en cabt.
- **El precedente del 5º** prueba que el ARQUETIPO tiene techo rule-based, NO que nuestra lista/policy lleguen ahí. Acción: localizar ese kernel, diff de su decklist vs `agents/alakazam/deck.csv`, minar sus reglas.
- **El meta gira en un día** (Lucario 56%→extinto en días). La friendliness ESTRUCTURAL de Alakazam es robusta al giro; los números de WR no.
- **Stage-2 = riesgo de arranque** (evolucionar 2 veces). Un mal opening lo descarta.
- **No quemar Dragapult:** es el suelo verificado y bate a los 2 mazos más jugados (Trevenant+Iono). Con 5 subs/día y los 2 últimos puntuados → **Alakazam en una ranura (crecimiento) + Dragapult en la otra (suelo)**.

## Convergencia con la otra sesión (importante)

Este estudio = capa de **SELECCIÓN** ("pivotar a Alakazam y por qué"). La opción (c) de la otra sesión = capa de
**EJECUCIÓN** ("extraer reglas de pilotaje del kernel `alakazam-5th` y del visor de replays"). **Componen perfecto:**
yo digo el destino, ellos traen el cómo pilotarlo. Si ambas sesiones confirman Alakazam, es la señal más fuerte
que tenemos para reasignar el esfuerzo de I+D fuera del mirror Dragapult techado.

## Acción concreta siguiente

1. Localizar el kernel `rule-based-not-psychic-alakazam-best-5th` → diff decklist vs `agents/alakazam/deck.csv` + minar reglas.
2. Construir "Sabrina v1" (Alakazam, según AGENTS.md trainer↔mazo) sobre el scaffolding robusto del campeón.
3. A/B de ladder real (no cabt) en una ranura, Dragapult en la otra como suelo.
