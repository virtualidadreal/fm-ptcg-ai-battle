export const meta = {
  name: 'verify-leon-v3-dataset',
  description: 'Dev Aumentado J2: verificacion adversarial CIEGA del dataset encodado BC Leon v3 antes de entrenar',
  phases: [
    { title: 'Verify', detail: '4 lentes adversariales independientes intentan REFUTAR la fidelidad del dataset' },
    { title: 'Synthesize', detail: 'fusiona veredictos -> GO/NO-GO para entrenar' },
  ],
}

const REPO = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'

// Definicion de Bien del DATASET (firmada implicitamente): lo que cada lente intenta REFUTAR.
const DOB = `DEFINICION DE BIEN del dataset encodado (intenta REFUTARLA, no confirmarla):
"Los shards en ${REPO}/bcil/dataset/encoded/shard_p*_*.npz representan FIEL y COMPLETAMENTE las 324.983
decisiones entrenables de pilotos Elo>=1150 del indice ${REPO}/bcil/dataset/pairs_index.jsonl, usando el
encoder OFICIAL (24 words encoder, vocab encoder<22000 y decoder<73847), con target = indice del candidato
que == accion del experto, value en {-1,+1}, y SIN perdida silenciosa ni solapamiento entre particiones."`

const ENV = `Entorno: cwd=${REPO}. Python host con torch/numpy: ${REPO}/.venv/bin/python3.12 .
Docker motor (para to_observation_class): export PATH="/opt/homebrew/bin:$PATH" &&
docker run --platform=linux/amd64 --rm -v "${REPO}":/work -w /work ptcg-cabt python <script>.
Encoder reusado: bcil/encode.py. Fuente oficial: data/official_kernels/mcts_rl/mcts_sample_code.py (lineas
117-325 = SparseVector..get_decoder_input; 33-46 = constantes). Extractor: bcil/extract_pairs.py.`

const VERDICT = {
  type: 'object',
  required: ['lens', 'refuted', 'severity', 'summary', 'checks_run', 'findings'],
  properties: {
    lens: { type: 'string' },
    refuted: { type: 'boolean', description: 'true si encontraste un fallo REAL de fidelidad/completitud' },
    severity: { type: 'string', enum: ['none', 'minor', 'blocking'] },
    summary: { type: 'string' },
    checks_run: { type: 'array', items: { type: 'string' } },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'evidence', 'blocking'],
        properties: {
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'numeros/comandos concretos, no impresiones' },
          blocking: { type: 'boolean' },
        },
      },
    },
  },
}

const LENSES = [
  {
    key: 'completitud',
    task: `LENTE COMPLETITUD / NO PERDIDA SILENCIOSA. Comprueba con codigo (no de palabra):
1. Suma de muestras sobre TODOS los shards encoded/shard_p*_*.npz == 324983 (el total entrenable del indice).
   Carga cada .npz y suma len(target). Si difiere, es REFUTACION (cuanta perdida y donde).
2. Las 4 particiones (p1..p4) son DISJUNTAS y COMPLETAS: re-deriva la particion por episodio que usa
   encode_dataset.py (--part i/4: keys ordenadas, j%4==i-1) y confirma que la union cubre todos los episodios
   entrenables del indice y ninguno se cuenta dos veces.
3. value tiene AMBAS clases (-1 y +1) en proporcion razonable (no colapsada a una sola). Reporta el balance.
4. n_cand>=1 siempre; target en [0, n_cand) en TODAS las muestras de TODOS los shards.`,
  },
  {
    key: 'fidelidad-encoder',
    task: `LENTE FIDELIDAD DEL ENCODER. ¿bcil/encode.py reproduce el encoder OFICIAL?
1. Diff textual: extrae de bcil/encode.py las funciones SparseVector/add_card/add_cards/add_pokemon/add_player/
   get_encoder_input/get_card/decoder_main/decoder_card_id/decoder_card/get_decoder_input y las constantes
   (num_words_encoder, encoder_size, decoder_*). Comparalas con data/official_kernels/mcts_rl/mcts_sample_code.py
   (lineas 33-46 y 117-325). Deben ser VERBATIM (salvo el header de import de cg). Cualquier divergencia logica = REFUTACION.
2. Runtime en Docker: corre bcil/test_encode.py (ya existe) y confirma 300/300 encodean, 24 words, decoder
   words == nº candidatos, y target valido ~99%+. Si algo no cuadra, REFUTA con el numero.
3. Confirma card_count=1268, encoder_size=22000, decoder_size=73847 (deben coincidir con bcil/model.py).`,
  },
  {
    key: 'target-alineacion',
    task: `LENTE TARGET / ALINEACION obs->accion. El nucleo del BC: ¿el target es DE VERDAD la jugada del experto?
1. En 200 episodios aleatorios (data/episodes/d2*/...zip via zipfile, sin extraer), para celdas status==ACTIVE
   con select: confirma que la accion vive en steps[t+1][seat] (NO en steps[t][seat], que es placeholder []).
   Mide el % en que bc_target (de bcil/extract_pairs.py) encuentra la accion experta. Debe ser ~99.7%.
   Si la regla same-step diera mejor o igual, seria REFUTACION de la alineacion elegida.
2. Decodifica el target: para K muestras, el combo en la posicion 'target' (enumerate_combos + [] si minCount==0)
   debe == la accion experta (orden-insensible). Si no, REFUTACION.
3. Reporta la distribucion de tamanos de seleccion y que % de pares se DESCARTO por target<0 (multi-select
   variable). Confirma que es minoria (~0.1%) y no un sesgo grande.`,
  },
  {
    key: 'integridad-shape',
    task: `LENTE INTEGRIDAD ESTRUCTURAL de los shards. Carga TODOS los encoded/shard_p*_*.npz y por cada uno:
1. len(e_word_off) == 24*len(target) (24 words encoder por muestra). Si no, REFUTACION.
2. len(d_word_off) == sum(n_cand) (un bag por candidato). Si no, REFUTACION.
3. e_idx.max() < 22000 y d_idx.max() < 73847 (dentro de vocab de los EmbeddingBag). Sin negativos.
4. e_word_off y d_word_off monotonos no decrecientes; sin NaN en e_val/d_val/value.
5. Carga un shard en bcil/model.py LeonV3Net y haz un forward de un mini-batch (en host con .venv torch CPU):
   logits shape (B, Cmax), value shape (B,), sin excepcion. Esto prueba que el formato es ENTRENABLE de verdad.`,
  },
]

phase('Verify')
const verdicts = await parallel(LENSES.map(L => () =>
  agent(
    `Eres un VERIFICADOR ADVERSARIAL CIEGO (Dev Aumentado J2). Tu trabajo NO es aprobar: es intentar REFUTAR.\n\n${DOB}\n\n${ENV}\n\nTU LENTE: ${L.task}\n\n` +
    `Ejecuta comprobaciones REALES con codigo/comandos. Default escéptico: si algo no lo puedes verificar, dilo. ` +
    `Devuelve el veredicto en el schema. 'refuted'=true SOLO con evidencia numerica concreta de un fallo real.`,
    { label: `verify:${L.key}`, phase: 'Verify', agentType: 'verificador', schema: VERDICT, effort: 'high' }
  )
)).then(v => v.filter(Boolean))

phase('Synthesize')
const synth = await agent(
  `Eres el sintetizador del gate Dev Aumentado para el dataset BC Leon v3. Te paso ${verdicts.length} veredictos ` +
  `adversariales (JSON):\n\n${JSON.stringify(verdicts, null, 2)}\n\n` +
  `${DOB}\n\nDecide GO/NO-GO para ENTRENAR:\n` +
  `- NO-GO si CUALQUIER lente tiene un finding blocking=true (fallo real de fidelidad/completitud/integridad).\n` +
  `- GO si ninguna lente refuta con severidad blocking.\n` +
  `Da: el veredicto (GO|NO-GO), los hallazgos blocking si los hay (con su evidencia), los minor a vigilar, y ` +
  `la lista de acciones concretas a corregir ANTES de entrenar si es NO-GO. Se conciso y honesto, sin inflar.`,
  { label: 'synth:go-no-go', phase: 'Synthesize', effort: 'high' }
)

return { verdicts, synthesis: synth }
