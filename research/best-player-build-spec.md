# Best-player build spec — Alakazam single-prize (anti-deck-out)

> Arquitecto del agente "mejor jugador" para el reto cabt.
> Shell elegido: **Alakazam single-prize** (sabrina_v1, base ladder 826.9).
> Última actualización: 23 jun 2026.
> Fuentes: `knowledge/synthesis/heuristicas-computables.md`, `knowledge/synthesis/reward-spec.md`,
> `agents_official/sabrina_v1/main.py`, `AGENTS.md`, `STRATEGY-PLAN.md`.

---

## 0. Tesis del shell (lo que condiciona TODO lo de abajo)

El atacante (Alakazam, Powerful Hand) **siempre vale 1 premio** y el shell es **single-prize**
salvo techs no-Rule-Box. Consecuencias duras, verificadas contra el código:

1. **Net-prize (R1) es INERTE aquí.** `net_prize_value(my, target) = PRIZE_VALUE[target] − PRIZE_VALUE[my]`
   con `PRIZE_VALUE[my] = 1` constante ⇒ ordenar KOs por net es idéntico a ordenar por
   `PRIZE_VALUE[target]`, que `_target_value()` (línea 520) ya hace con `prize_count(p) * 1000`.
   El término "concedo" es una constante (1) para todo trade. No hay edge encodeable en R1 con este shell.
   *Esto es exactamente el "A1 inerte" del report y el anti-goal de STRATEGY-PLAN §5.*
2. **El modo de derrota DOMINANTE es el DECK-OUT.** El win-con (Powerful Hand = 20×mano) EMPUJA
   a robar agresivamente (Run Away Draw +3, Hilda/Dawn). El código ya tiene cicatriz: `_deck_preserve()`
   (línea 346, "real-ladder bug: filtramos el mazo a 0 yendo ganando"), floors `deckCount<=7`
   (línea 623), `handCount>=14 and deckCount<=12` (línea 645). **Aquí está el edge real.**
3. **El edge encodeable = árbol de decisión que ataca el deck-out + pilotaje** (sequencing, rol,
   gestión de robo prize-belief-aware). NO multi-prize math.

---

## 1. Clasificación de las 9 heurísticas

Leyenda: **(A)** aplica al shell Alakazam y NO inerte · **(B)** inerte / no-aplica aquí ·
**(C)** requiere otro shell (multi-prize).

| # | Heurística | Concepto | Clase | Razón en este shell |
|---|-----------|----------|:-----:|---------------------|
| 1 | Net prize value de KO | prize-trade | **B** | Atacante = 1 premio fijo ⇒ resta neta = constante. Ya cubierto por `_target_value`. Inerte. |
| 2 | Penalizar exposición a KO | prize-trade/reading | **B/C** | El valor de exponer mi atacante = 1 premio (single-prize): no hay "regalar 2-3". El downside real de perder el atacante es *tempo* (un turno sin KO ⇒ más mill), no premios. Marginal; vive dentro de #8/promoción. |
| 3 | Counter Catcher / behind | tempo | **A** (parcial) | Boss's Orders ya está (sin guard de premios; es Supporter, no Item). Gusting-libera-Supporter NO aplica si no hay equivalente Item en el pool de cabt. Aplica el **patrón** "ir-detrás desbloquea jugadas" sólo si existe el Item. **Verificar pool.** |
| 4 | Belief cartas premiadas (prize-checking) | prize-checking | **A** | Núcleo anti-deck-out indirecto: si la pieza clave está probablemente premiada, no quemes mazo cavando por ella. Toca `prizes_remaining`, `deckCount`. |
| 5 | Ordenar turno por fase (sequencing) | sequencing | **A** | **Draw-before-search** es el principio más barato y seguro: robar antes de buscar revela cartas, evita búsquedas redundantes que aceleran el mill. Encodeable como ajuste de scores. |
| 6 | Mulligan / consistencia | consistency | **B** (turno) | Matemática de deckbuild, no de turno. El deck.csv ya está fijado. No es palanca de pilotaje en runtime. |
| 7 | Belief arquetipo rival | reading/archetypes | **C/P2** | Requiere belief-state maduro + features. Alto coste, bajo ROI inmediato vs deck-out. No primera ola. |
| 8 | Rol BEATDOWN/CONTROL | archetypes | **A** | Directamente relevante: contra rival lento, el riesgo NO es perder la carrera sino **deckear-se**. Asignar rol "race vs grind" gobierna cuánto robar. Re-mapeable a "draw-hard vs draw-thrifty". |
| 9 | Poda Reklev / setup gate | deckbuilding | **B** (offline) | Offline, deckbuild. No estado de turno. |

**(A) ordenadas por valor-para-evitar-deck-out / pilotaje:**

1. **#5 sequencing (draw-before-search)** — el más barato, más seguro, ataca el mill directamente
   (menos búsquedas redundantes ⇒ menos cartas quemadas). Cero dependencia de belief.
2. **#8 rol beatdown/control (race vs grind)** — gobierna la política global de robo: cuándo
   pisar el freno de draw. Es el dial maestro del deck-out.
3. **#4 prize-belief anti-deck-out** — evita cavar el mazo persiguiendo una pieza premiada;
   refina el freno de #8 con la hipergeométrica pública.
4. **#3 tempo/behind** — sólo si el pool de cabt tiene el Item-gust equivalente. Condicional.

---

## 2. Clasificación de los 7 reward-terms

| Term | Símbolo | Clase | Razón en este shell |
|------|---------|:-----:|---------------------|
| R1 · Net prize trade | W1·R_net_prize | **B** | INERTE. Atacante single-prize ⇒ `PRIZE_VALUE[my]=1` constante. Es el "A1 inerte". |
| R2 · Exposure penalty | W2·R_exposure | **B/C** | Exponer single-prize concede 1, no 2-3. Sin asimetría que explotar. Degenera a tempo. |
| R3 · Tempo / behind | W3·R_tempo | **A** (parcial) | El sub-term `delta_prize_lead` aplica; el sub-term Counter-Catcher sólo si existe el Item. |
| R4 · Prize-belief | W4·R_prize_belief | **A** | Aplica: modificador de prioridad anti-cavado. Conecta con deck-out. |
| R5 · Mulligan cost | W5·R_mulligan | **B** | Deckbuild/inicio, no runtime. |
| R6 · Invite penalty | W6·R_invite | **B** | Penaliza benchear multi-premio. Nuestro bench es single-prize (Abra/Dunsparce/techs). Inerte. |
| R7 · Information gain | W7·R_info | **C/P2** | Requiere belief rival. No primera ola. |

**Term faltante que el shell EXIGE (no está en el spec original porque el spec asume multi-prize):**

> **R8 · Deck-out penalty / survival** — `R_deckout = − f(deckCount, prizes_remaining)`, fuerte y no-lineal
> cuando `deckCount → prizes_remaining`. ESTE es el reward-term dominante del shell Alakazam.
> El código ya lo aproxima con guards booleanos (`_deck_preserve`, floors). La oportunidad de edge =
> convertir esos guards binarios en un gradiente continuo prize-belief-aware. Es el corazón de los candidatos.

---

## 3. Candidatos de UNA SOLA PALANCA (protocolo "1 variable a la vez")

Regla del report (STRATEGY-PLAN §5 + disciplina dev-aumentado): **1 cambio/día, A/B pareado, byte-idéntico
a sabrina_v1 salvo la palanca, N≥60, Wilson.** Cada candidato = `main.py` de sabrina_v1 con UN solo edit
localizado. Todos preservan el contrato (ver §4).

---

### Candidato 1 — `sabrina_dbs1` · sequencing: DRAW-BEFORE-SEARCH

**Palanca (1 variable):** prioridad relativa de *draw-supporters* (Hilda/Dawn, robo) vs
*directed-search* en `_score_play_trainer`. Hoy ambos viven en la banda ~12000-14000 sin orden de fase
garantizado; la palanca añade un **bias de fase** que pone el robo estrictamente por delante de la búsqueda
dirigida **cuando aún no hay info nueva revelada este turno**.

**Variable de estado de cabt que toca:** `self.state.supporterPlayed` (ya leída), conteo de búsqueda
ya jugada este turno (derivable de las opciones legales restantes). No introduce estado nuevo; reordena
scores existentes.

**Pseudocódigo del nudge (un único bloque añadido en `_score_play_trainer`):**
```python
PHASE_DRAW = 1.0      # robo (revela cartas)
PHASE_SEARCH = 0.5    # búsqueda dirigida (compromete sin revelar)
SEQ_BIAS = 400        # << banda de scores, sólo desempata

def _seq_bias(self, card_id):
    # draw-supporters por DELANTE de search dirigido: robar revela cartas y evita
    # búsquedas redundantes que aceleran el deck-out. Sólo aplica antes de revelar.
    if self.state.supporterPlayed:
        return 0
    if card_id in (C.HILDA, C.DAWN):        # roban / cavan ancho -> fase draw
        return +SEQ_BIAS
    if card_id in (C.BUDDY_POFFIN, C.POKE_PAD):  # search dirigido -> fase posterior
        return -SEQ_BIAS
    return 0
# y al final de cada return de _score_play_trainer (no en RARE_CANDY/BOSS, que son gating):
#   return base_score + self._seq_bias(cid)
```

**Por qué NO rompe el contrato:** sólo modifica el **valor numérico** de opciones ya legales y ya
puntuadas; no cambia qué se devuelve si la opción no existe. `SEQ_BIAS=400 ≪` las bandas de gating
(que usan ±1 / −1 para legalidad), así que nunca convierte un −1 (ilegal/no-jugar) en jugable ni
viceversa. `normalize_selection` + `_validate_obj` intactos. Es desempate puro dentro de jugadas legales.

**Valor esperado:** medio-alto. Menos búsquedas redundantes ⇒ menos cartas quemadas/turno ⇒ retrasa el
deck-out, que es el modo de derrota dominante. Riesgo bajo (cambio conservador, no toca la identidad
draw-aggressive que el código documenta como necesaria en cabt).

---

### Candidato 2 — `sabrina_pbelief1` · gestión de robo prize-belief-aware ANTI-DECK-OUT

**Palanca (1 variable):** el **freno de robo opcional** (`_deck_preserve` / floors de `_score_ability`)
pasa de umbral booleano fijo a umbral **prize-belief-aware**. Hoy el freno usa `deckCount <= remaining_prizes + 4`
(constante 4) y `handCount>=14 and deckCount<=12` (constantes mágicas). La palanca sustituye ESE buffer
constante por uno derivado de la hipergeométrica de cuántas piezas-clave quedan accesibles, endureciendo
el freno cuanto más probable es que sigamos vivos sin cavar.

**Variable de estado de cabt que toca:** `self.me.deckCount`, `len(self.me.prize)` (premios restantes,
público), `self.me.handCount`. Opcionalmente `known_counts` derivado de `self.field`/`self.discard`/`self.hand`.
Todo ya disponible; no añade observación nueva.

**Pseudocódigo del nudge (reemplaza SÓLO el buffer constante de `_deck_preserve`):**
```python
from math import comb

def _prob_piece_drawable_soon(self, copies, draws=1):
    # ¿prob. de ver >=1 copia de una pieza-clave en los próximos `draws`?
    # unknown_pool = mazo (las premiadas/no vistas). Si es alta, NO necesitamos cavar.
    pool = max(1, self.me.deckCount)
    if copies <= 0 or copies > pool:
        return 0.0 if copies <= 0 else 1.0
    return 1 - comb(pool - copies, draws) / comb(pool, draws)

def _deck_preserve(self):                       # PALANCA: buffer dinámico
    if not self._have_attacker():
        return False
    opp = self.opponent.active[0] if self.opponent.active else None
    if opp is None:
        return False
    remaining = len(self.me.prize)
    big_hand = 20 * self.me.handCount >= max(opp.hp, 130)
    # buffer dinámico: si una pieza-clave es muy drawable sin cavar, aprieta el freno antes
    # (buffer mayor); si está seca, afloja para poder cavar. Sustituye el "+4" constante.
    copies_attacker = self.hand[C.ALAKAZAM] + self.field[C.ALAKAZAM] + self.field[C.KADABRA]
    p_safe = self._prob_piece_drawable_soon(max(1, copies_attacker), draws=1)
    buffer = 3 + round(3 * p_safe)              # 3..6 según seguridad (antes: fijo 4)
    deck_low = self.me.deckCount <= remaining + buffer
    return big_hand and deck_low
```

**Por qué NO rompe el contrato:** `_deck_preserve` ya existe y sólo **devuelve un bool** que modula
scores (devuelve −1 a draws opcionales). La palanca cambia el *umbral*, no la mecánica ni la firma.
Sigue sin frenar repositioning-to-attack (ese path está fuera de `_deck_preserve`, línea 632). No toca
`agent()`, `normalize_selection`, ni `_validate_obj`. La hipergeométrica es pura aritmética sobre estado
público; sin riesgo de excepción (guards de pool≥1 y copies en rango).

**Valor esperado:** alto. Ataca directamente el deck-out (modo de derrota dominante) y reemplaza
constantes mágicas (que el propio código marca como A/B pendiente, línea 644) por una regla principiada
y citable en el report (hipergeométrica verificada). Riesgo medio: cambia el ritmo de robo, necesita A/B
contra el riesgo documentado "los deck-out guards regresaron cabt" — por eso es **dinámico** (afloja cuando
hace falta cavar), no un guard ciego.

---

### Candidato 3 — `sabrina_role1` · rol BEATDOWN/CONTROL como dial de robo (race vs grind)

**Palanca (1 variable):** un flag de rol `_grind_mode()` que, cuando el rival NO puede ganarnos la carrera
rápido (somos quien probablemente deckea primero), reduce el robo opcional un escalón — sin llegar al freno
duro de `_deck_preserve`. Es la versión "soft" y global de C2: un único interruptor que baja la agresividad
de draw en partidas de grind largas.

**Variable de estado de cabt que toca:** `len(self.me.prize)` vs `len(self.opponent.prize)` (prize_diff,
público), `self.me.deckCount` vs `self.opponent.deckCount` (quién deckea antes), `self._ko_active_reachable()`
(velocidad propia, ya computada). Todo público/derivado; sin estado nuevo.

**Pseudocódigo del nudge (un método + un escalón en `_score_ability` de Run Away Draw benched):**
```python
def _grind_mode(self):
    # CONTROL/grind: si vamos por delante o a la par en premios y el rival NO nos OHKO-rushea,
    # la amenaza real es deckear-se. Roba lo justo. (No-OHKO se aproxima por nuestra ventaja de
    # mazo: si deckeamos DESPUES que el rival, la carrera de cartas la perdemos cavando de mas.)
    prize_diff = len(self.opponent.prize) - len(self.me.prize)   # >0 = vamos por delante
    deck_race_safe = self.me.deckCount >= self.opponent.deckCount  # deckeamos despues o igual
    return prize_diff >= 0 and not deck_race_safe

# en _score_ability, rama BENCHED Run Away Draw (tras los floors, ANTES del return 15000):
    if self._grind_mode() and self.me.handCount >= 8:
        return 12000        # sigue siendo alta (se activa) pero por debajo de search/KO plays
    return 15000
```

**Por qué NO rompe el contrato:** sólo rebaja un score (15000→12000) dentro de una opción que ya era
legal y deseada; nunca la apaga (sigue >0, por encima de END y de jugadas neutras). No toca floors de
deck-out (deckCount<=7) ni el path de repositioning. Firma de `_score_ability` intacta. `agent()` y la
capa de validación sin cambios.

**Valor esperado:** medio. Es el dial más "de concepto" (alinea con la tesis del report: rol dinámico /
consistency-first). Riesgo: solapa parcialmente con C2 — por disciplina de "1 variable" se evalúan por
separado y NO se combinan hasta tener A/B de cada uno. Menor ROI puntual que C2 pero más barato y citable
en el 20% (concepto de mazo).

---

## 4. Contrato compartido (lo que los 3 preservan, byte-idéntico salvo la palanca)

- `agent` sigue siendo el **último callable top-level** (kaggle `get_last_callable`). NO mover.
- `agent(obs_dict, config=None)`: deck-phase probe (`select is None → my_deck`) intacto.
- `normalize_selection`, `_repeat_to_min`, `_legal_fallback`, `_validate_obj`: intactos (red de
  supervivencia campeón, 0 INVALIDs).
- Cada palanca toca SÓLO scores de opciones ya legales (desempate), nunca legalidad ni la firma de
  métodos. Las bandas de gating (±1, −1) quedan por encima en magnitud de cualquier bias añadido.
- `deck.csv` byte-idéntico. `build_submission.sh` sin cambios.

---

## 5. Lista priorizada de candidatos a construir

| Orden | Slug | Palanca (1 variable) | Clase | Valor esperado anti-deck-out/pilotaje |
|:---:|------|----------------------|:-----:|---------------------------------------|
| **1** | `sabrina_pbelief1` | Buffer de `_deck_preserve` constante → prize-belief-aware (hipergeométrica) | A (#4 + R8) | **ALTO** — ataca el modo de derrota dominante; reemplaza constantes mágicas por regla citable |
| **2** | `sabrina_dbs1` | Bias de fase draw-before-search en `_score_play_trainer` | A (#5) | **MEDIO-ALTO** — menos búsquedas redundantes ⇒ menos mill; cambio conservador, bajo riesgo |
| **3** | `sabrina_role1` | Flag `_grind_mode()` baja un escalón el Run Away Draw en grind | A (#8 + R3) | **MEDIO** — dial de concepto (race vs grind); solapa con C2, evaluar aislado |

**Recomendación de cadencia (disciplina 1 cambio/día, no quemar ranuras):**
construir y A/B `sabrina_dbs1` PRIMERO (menor riesgo, valida el harness de A/B sobre un cambio seguro),
luego `sabrina_pbelief1` (mayor edge esperado, mayor riesgo — necesita el A/B robusto ya rodado),
y `sabrina_role1` como tercero (concepto, posible fusión futura con pbelief1 sólo tras A/B individuales).
Mantener Leon v1 (Dragapult, suelo verificado) en la otra ranura — NO quemar.

**NO construir (anti-goals confirmados):** cualquier candidato sobre R1/R2/R6 (inertes en single-prize),
R7/#7 (belief rival, P2, sin ROI inmediato), o que combine palancas antes de tener A/B individual de cada una.
```
