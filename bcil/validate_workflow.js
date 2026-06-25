export const meta = {
  name: 'validate-leon-v3-greedy',
  description: 'Dev Aumentado Fase C: ¿la policy greedy Leon v3 bate a Leon v1? Bug-hunt adversarial + A/B paralelo + juicio',
  phases: [
    { title: 'BugHunt', detail: '2 verificadores buscan un BUG que explique el bajo rendimiento pese al 77% offline' },
    { title: 'AB', detail: 'A/B paralelo leon_v3_bc vs Leon v1 (200 partidas) + floor vs first-legal' },
    { title: 'Judge', detail: 'sintetiza: ¿bug o debilidad real? GO/NO-GO de subir + diagnostico + siguiente paso' },
  ],
}

const REPO = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'
const DOCKER = `export PATH="/opt/homebrew/bin:$PATH" && docker run --platform=linux/amd64 --rm -v "${REPO}":/work -w /work ptcg-torch`

const CONTEXT = `Contexto: Leon v3 es una policy BC (Behavioral Cloning) entrenada de pilotos Elo>=1150. Offline acierta
la jugada del experto 77% (val top1). PERO en un A/B local de 10 partidas leon_v3_bc PIERDE a Leon v1 (el sample
Dragapult tuneado) 1W/9L, con la net conduciendo el 100% (678 decisiones, 0 fallbacks, 0 errores). Ambos pilotan
Dragapult (mirror). Hipotesis a discriminar: (a) BUG de inferencia que hace jugar mal a la net pese al 77% offline,
o (b) debilidad REAL (una policy general clonada, entrenada sobre todo de mazos NO-Dragapult de elite, pilota
Dragapult peor que el especialista tuneado). cwd=${REPO}.
Agente: agents_official/leon_v3_bc/ (main.py + encode_lib.py + model.py + leon_v3.pt + deck.csv + cg/).
Entreno: bcil/train.py + bcil/model.py + bcil/encode.py. Docker con torch: ${DOCKER} python <script>.`

const REVIEW_SCHEMA = {
  type: 'object', required: ['found_bug', 'severity', 'summary', 'checks', 'findings'],
  properties: {
    found_bug: { type: 'boolean' },
    severity: { type: 'string', enum: ['none', 'minor', 'major', 'critical'] },
    summary: { type: 'string' },
    checks: { type: 'array', items: { type: 'string' } },
    findings: { type: 'array', items: { type: 'object', required: ['claim', 'evidence', 'would_explain_loss'],
      properties: { claim: { type: 'string' }, evidence: { type: 'string' }, would_explain_loss: { type: 'boolean' } } } },
  },
}
const AB_SCHEMA = {
  type: 'object', required: ['matchup', 'A_wins', 'B_wins', 'draws', 'winrate_A', 'net_drove'],
  properties: {
    matchup: { type: 'string' }, A_wins: { type: 'integer' }, B_wins: { type: 'integer' },
    draws: { type: 'integer' }, winrate_A: { type: 'number' }, wilson_lo: { type: 'number' },
    wilson_hi: { type: 'number' }, net_drove: { type: 'boolean' }, raw: { type: 'string' },
  },
}

phase('BugHunt')
const reviewLenses = [
  {
    key: 'inferencia-vs-entreno',
    task: `¿La INFERENCIA de leon_v3_bc reproduce EXACTO lo que se entreno? Busca un mismatch que haga jugar mal:
1. El encoding de inferencia (main.py::_net_decision usa encode_lib.encode_pair) debe ser IDENTICO al de entreno
   (bcil/encode_dataset.py usa bcil/encode.py). Confirma que encode_lib.py == bcil/encode.py (diff).
2. La construccion de tensores en _net_decision: e_wo=sv_enc.offset, d_wo=sv_dec.offset, n_cand=[len(actions)].
   ¿Coincide con lo que el modelo espera (forward batcheado)? Para batch=1, ¿el offset[0]==0 y el scatter da el
   mismo resultado que en collate de train.py? Verifica corriendo en Docker: encodea UNA obs real, pasa por el
   modelo cargado de leon_v3.pt, y compara el argmax con un calculo manual de la policy.
3. ¿Se usa la cabeza correcta? Debe elegir argmax de la POLICY (logits sobre candidatos), NO de la value head.
   Revisa que logits=model(...)[0] es la policy. Un swap policy/value explicaria jugar casi aleatorio.
4. ¿El orden de candidatos en inferencia (candidate_actions, [] primero si minCount==0) == el del target de entreno?
Si encuentras un mismatch que degradaria el juego, found_bug=true, would_explain_loss=true, con evidencia.`,
  },
  {
    key: 'deck-estado-robustez',
    task: `¿El agente pilota bien o hay un fallo sutil que lo lastra (sin crashear)?
1. deck.csv de leon_v3_bc == el de dragapult_sample (mismo mazo Dragapult)? Si pilotara otro mazo, perderia.
2. _net_decision pasa my_deck al encoder (your_deck). Confirma que my_deck son las 60 cartas correctas y que el
   encoder recibe el deck del JUGADOR ACTIVO, no algo cruzado.
3. ¿La net colapsa a una jugada degenerada? Corre en Docker una partida instrumentada: loguea la distribucion de
   OptionType elegidos por leon_v3_bc en una partida y compara con lo que haria Leon v1. Si la net p.ej. ataca
   tardisimo o nunca evoluciona, es debilidad de policy (no bug) — repórtalo como would_explain_loss pero NO bug.
4. Revisa que no haya un sesgo del argmax (p.ej. siempre elige el candidato 0 / la accion vacia []). Mide el % de
   veces que elige [] o el indice 0 en una partida; si es anormalmente alto, es sospechoso.
Reporta hallazgos con evidencia numerica. Distingue BUG (found_bug) de DEBILIDAD DE POLICY (would_explain_loss sin bug).`,
  },
]
const reviews = await parallel(reviewLenses.map(L => () =>
  agent(`Eres un VERIFICADOR ADVERSARIAL CIEGO (Dev Aumentado J2). ${CONTEXT}\n\nTU TAREA: ${L.task}\n\n` +
    `Comando Docker para cualquier prueba: ${DOCKER} python <tu_script.py> (escribe scripts en /tmp o bcil/_tmp_*.py). ` +
    `Default escéptico. Devuelve el schema.`,
    { label: `bughunt:${L.key}`, phase: 'BugHunt', agentType: 'verificador', schema: REVIEW_SCHEMA, effort: 'high' })
)).then(r => r.filter(Boolean))

phase('AB')
// 4 workers vs Leon v1 (50 partidas c/u, seeds disjuntos) + 1 floor vs first-legal
const abJobs = [
  { m: 'leon_v3_bc vs Leon_v1 (seed 0)', dirB: 'agents_official/dragapult_sample', n: 50, seed: 0 },
  { m: 'leon_v3_bc vs Leon_v1 (seed 1000)', dirB: 'agents_official/dragapult_sample', n: 50, seed: 1000 },
  { m: 'leon_v3_bc vs Leon_v1 (seed 2000)', dirB: 'agents_official/dragapult_sample', n: 50, seed: 2000 },
  { m: 'leon_v3_bc vs Leon_v1 (seed 3000)', dirB: 'agents_official/dragapult_sample', n: 50, seed: 3000 },
  { m: 'leon_v3_bc vs first-legal (floor)', dirB: 'experiments/baselines/firstlegal', n: 40, seed: 7000 },
]
const abResults = await parallel(abJobs.map(J => () =>
  agent(`Ejecuta este A/B y devuelve el JSON. ${CONTEXT}\n\n` +
    `Corre EXACTAMENTE: ${DOCKER} python bcil/ab_json.py agents_official/leon_v3_bc ${J.dirB} ${J.n} ${J.seed}\n` +
    `Espera la linea que empieza por 'JSON_RESULT ' (puede tardar ~1-2 min). Parsea ese JSON y mapealo al schema: ` +
    `matchup="${J.m}", A_wins, B_wins, draws, winrate_A, wilson_lo, wilson_hi, net_drove = (A_fallbacks==0 && A_errors vacio && A_net_loaded==true), ` +
    `raw = la linea JSON cruda. Si el comando falla, reporta el error en raw y net_drove=false.`,
    { label: `ab:${J.seed}`, phase: 'AB', schema: AB_SCHEMA })
)).then(r => r.filter(Boolean))

phase('Judge')
const judge = await agent(
  `Eres el juez Dev Aumentado de Fase C. Definicion de Bien: "Leon v3 (greedy) es candidato a subir SOLO si bate a ` +
  `Leon v1 con significancia Wilson, dentro de presupuesto y sin crashes". ${CONTEXT}\n\n` +
  `BUG-HUNT (¿hay un bug que explique el bajo rendimiento?):\n${JSON.stringify(reviews, null, 2)}\n\n` +
  `A/B (¿gana o pierde, con cuanta significancia?):\n${JSON.stringify(abResults, null, 2)}\n\n` +
  `Decide y se HONESTO (anti falso-positivo):\n` +
  `1. ¿Hay un BUG real de inferencia (found_bug critical/major que would_explain_loss)? Si SI -> el resultado A/B NO ` +
  `es concluyente, hay que ARREGLAR y re-medir. Lista el fix.\n` +
  `2. Si NO hay bug: agrega las ~200 partidas vs Leon v1 (suma wins/losses, Wilson sobre el total) y vs first-legal. ` +
  `¿leon_v3_bc bate a Leon v1? (Wilson excluye 0.5 a favor?).\n` +
  `3. Veredicto SUBIR: GO solo si bate a Leon v1; si no, NO-GO y Leon v1 sigue de campeon (Muro FR-8, no gastar slot).\n` +
  `4. Diagnostico de POR QUE (si pierde): ¿gap del especialista en el mirror? ¿la policy general no sabe pilotar ` +
  `Dragapult? Recuerda que el plan preve que el salto real es BC-eval + ISMCTS (Leon v3 final), no la greedy sola.\n` +
  `5. Siguiente paso concreto recomendado. Recuerda §6: el A/B local es FILTRO, no el ladder.`,
  { label: 'judge:go-no-go', phase: 'Judge', effort: 'high' })

return { reviews, abResults, judge }
