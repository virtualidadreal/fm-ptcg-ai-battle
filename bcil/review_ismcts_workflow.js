export const meta = {
  name: 'review-leon-v3-ismcts',
  description: 'Dev Aumentado J2: revision adversarial del cableado de la BC net (value+policy) en el ISMCTS de Leon v3',
  phases: [
    { title: 'Review', detail: '2 verificadores buscan fallos en la integracion net<->search antes de fiarse del A/B' },
    { title: 'Synthesize', detail: 'fusiona -> integracion correcta? que arreglar antes de concluir' },
  ],
}

const REPO = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'
const DOCKER = `export PATH="/opt/homebrew/bin:$PATH" && docker run --platform=linux/amd64 --rm -e FMA_MCTS_ON=1 -v "${REPO}":/work -w /work ptcg-torch`

const CONTEXT = `Contexto: Leon v3 final = ISMCTS (agent_ismcts/main.py) con la eval ESTATICA reemplazada por la BC net
(value + policy prior), a la create_node del kernel oficial MCTS. La integracion vive en agent_ismcts/main.py:
(1) carga del modulo-nivel del net (_NET, _E=encode_lib, _torch) tras el import de cg; (2) funcion _net_eval(obs,
actions) que hace UNA pasada y devuelve (value, priors); (3) _create_node usa _net_eval para value+priors, con
fallback a _static_eval/_priors_from_sample si la net falla. El obs del nodo YA es una Observation (no dict).
Referencia oficial: data/official_kernels/mcts_rl/mcts_sample_code.py create_node (L383-438) y eval_nn.
cwd=${REPO}. Docker con torch: ${DOCKER} python <script>.`

const SCHEMA = {
  type: 'object', required: ['found_issue', 'severity', 'summary', 'checks', 'findings'],
  properties: {
    found_issue: { type: 'boolean' },
    severity: { type: 'string', enum: ['none', 'minor', 'major', 'critical'] },
    summary: { type: 'string' },
    checks: { type: 'array', items: { type: 'string' } },
    findings: { type: 'array', items: { type: 'object', required: ['claim', 'evidence', 'blocking'],
      properties: { claim: { type: 'string' }, evidence: { type: 'string' }, blocking: { type: 'boolean' } } } },
  },
}

const LENSES = [
  {
    key: 'correccion-value-policy',
    task: `CORRECCION DEL CABLEADO net<->search. Compara agent_ismcts/main.py::_create_node y _net_eval contra el
create_node oficial (mcts_sample_code.py L383-438):
1. SIGNO del value: el value de la net es desde obs.current.yourIndex. _create_node hace 'if state.yourIndex !=
   your_index: v = -v'. ¿Es correcto el flip (igual que el oficial 'if state.yourIndex != your_index: v = -v')?
   Un signo invertido haria que el search prefiera perder. Verifica con cuidado.
2. ALINEACION de priors: _net_eval llama get_decoder_input(obs, actions) con las MISMAS 'actions' que
   _enumerate_actions del search, y la softmax se hace sobre logits[0, :len(actions)]. ¿Coincide el orden? OJO:
   _enumerate_actions NO añade la accion vacia [] (a diferencia de candidate_actions de entreno). ¿Importa para el
   scoring? (el decoder puntua cada accion independientemente, deberia dar igual el set). Confirma que probs[i]
   corresponde a actions[i].
3. Priors solo en nodos NUESTROS (state.yourIndex == your_index), uniforme en los del rival. ¿Bien?
4. ¿El value se backpropaga UNA vez (node.backprop(v)) sin doble conteo con el resultado terminal?
Corre en Docker si hace falta. found_issue=true solo con evidencia de un fallo que afecte la fuerza de juego.`,
  },
  {
    key: 'robustez-leak-budget',
    task: `ROBUSTEZ, LEAKS y PRESUPUESTO de la integracion:
1. Si _net_eval lanza excepcion en un nodo, ¿cae limpio a _static_eval sin romper la construccion del nodo ni
   el search? Revisa el try/except en _create_node.
2. ¿search_release/search_end se sigue llamando (sin leak de memoria del motor) con la net activa? Busca en el
   loop de determinizacion que no se haya roto la liberacion.
3. DECK en nodos del rival: _net_eval pasa my_deck (NUESTRO deck) al encoder incluso cuando yourIndex=rival.
   ¿Es un problema? (el oficial pasa your_deck siempre; los priors del rival son uniformes igualmente). Evalua
   si contamina el VALUE en nodos del rival y si eso sesga el minimax.
4. PRESUPUESTO: con FMA_WALL_S, ¿el search respeta el deadline por decision? Mide en Docker el tiempo por decision
   de agent_ismcts con FMA_WALL_S=1.2 en unas pocas decisiones; confirma que no se pasa de HARD_WALL_S y que no
   hay INVALID/crash. Reporta tiempo medio por decision.
5. ¿La carga del net a modulo-nivel puede dejar _NET_EVAL_OK=False en silencio y el agente jugaria entonces con
   eval estatica (net-negativa) sin avisar? ¿Como se detectaria en el A/B?`,
  },
]

phase('Review')
const reviews = await parallel(LENSES.map(L => () =>
  agent(`Eres un VERIFICADOR ADVERSARIAL CIEGO (Dev Aumentado J2). ${CONTEXT}\n\nTU LENTE: ${L.task}\n\n` +
    `Default escéptico, evidencia concreta. Devuelve el schema.`,
    { label: `review:${L.key}`, phase: 'Review', agentType: 'verificador', schema: SCHEMA, effort: 'high' })
)).then(r => r.filter(Boolean))

phase('Synthesize')
const synth = await agent(
  `Sintetiza la revision de la integracion BC-net en el ISMCTS de Leon v3. Reviews:\n${JSON.stringify(reviews, null, 2)}\n\n` +
  `Decide: ¿la integracion es CORRECTA (el A/B que esta corriendo en paralelo seria fiable) o hay un fallo que ` +
  `invalida el resultado y hay que arreglar antes? Lista findings blocking con su fix. Se conciso y honesto.`,
  { label: 'synth', phase: 'Synthesize', effort: 'high' })

return { reviews, synth }
