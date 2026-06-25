#!/usr/bin/env python3
"""Core de render reutilizable por host (macOS) y Docker (linux).

Extrae la logica de Via 1 del Battle Replay Visualizer v2 (shiiin9): ejecuta
las celdas 4 (loaders de cartas) y 5 (plantilla + generate_html) del notebook
y produce el HTML interactivo del replay.

PURO stdlib (json/os/csv/html). NO importa cg ni depende de libcg.so/Docker,
asi que corre identico en host y en contenedor.
"""
import csv
import html  # noqa: F401  (disponible por si las celdas del notebook lo usan)
import json
import os

# Celdas del notebook que contienen la logica del autor:
#   4 -> _load_card_csv, load_card_info(_en), columnas EN/JP
#   5 -> _HTML_TEMPLATE + generate_html(steps, out_path)
_CELL_CARDS = 4
_CELL_TEMPLATE = 5

# Boton "Cargar partida" inyectado en el HTML generado. Se apoya en que STEPS
# (const array, mutable en sitio), cur (let) y render()/stopPlay()/updateStepUI()
# de la plantilla son visibles desde otro <script> clasico (mismo scope lexico).
_LOAD_BUTTON_JS = """
<script>
(function(){
  var header = document.getElementById('header');
  if(!header) return;
  var wrap = document.createElement('label');
  wrap.textContent = '\\uD83D\\uDCC1 Cargar partida';
  wrap.title = 'Abrir otro replay (.json con steps[0][0].visualize)';
  wrap.style.cssText = 'cursor:pointer;background:#1b3a5c;color:#cfe8ff;border:1px solid #2a5a8a;border-radius:6px;padding:3px 9px;font-size:0.85em;user-select:none;';
  var input = document.createElement('input');
  input.type = 'file'; input.accept = '.json,application/json'; input.style.display = 'none';
  wrap.appendChild(input); header.appendChild(wrap);
  input.addEventListener('change', function(e){
    var f = e.target.files && e.target.files[0];
    if(!f) return;
    var rd = new FileReader();
    rd.onload = function(){
      var j;
      try { j = JSON.parse(rd.result); }
      catch(err){ alert('No pude leer el JSON: ' + err.message); return; }
      var ns = j && j.steps && j.steps[0] && j.steps[0][0] && j.steps[0][0].visualize;
      if(!ns || !ns.length){
        alert('Ese JSON no es un replay (falta steps[0][0].visualize). Quiza es el log del agente, no la partida.');
        return;
      }
      if(typeof stopPlay === 'function') stopPlay();
      STEPS.length = 0;
      for(var i=0;i<ns.length;i++) STEPS.push(ns[i]);
      cur = 0;
      var sl = document.getElementById('step-slider'); if(sl) sl.max = STEPS.length - 1;
      var tot = document.getElementById('step-total'); if(tot) tot.textContent = '/ ' + STEPS.length;
      render();
      if(typeof updateStepUI === 'function') updateStepUI();
    };
    rd.readAsText(f);
  });
})();
</script>
"""


def _inject_load_button(out_path):
    """Inserta el boton 'Cargar partida' antes de </body> en el HTML ya escrito."""
    with open(out_path, encoding="utf-8") as f:
        html_text = f.read()
    if "Cargar partida" in html_text:
        return  # ya inyectado
    html_text = html_text.replace("</body>", _LOAD_BUTTON_JS + "</body>", 1)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)


def _exec_cell(nb, idx, ns):
    """Ejecuta el codigo de la celda idx del notebook en el namespace ns."""
    src = "".join(nb["cells"][idx]["source"])
    exec(compile(src, f"<cell {idx}>", "exec"), ns)


def _build_card_names_en(data_dir):
    """card_names_en = {int(Card ID): Card Name} desde {data_dir}/EN_Card_Data.csv.

    En el notebook esto sale de all_card_data() (cg.api -> libcg.so); aqui lo
    reconstruimos desde el CSV para no depender de Docker.
    """
    card_names_en = {}
    csv_path = os.path.join(data_dir, "EN_Card_Data.csv")
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                card_names_en[int(row["Card ID"])] = row["Card Name"]
            except (ValueError, KeyError):
                continue
    return card_names_en


def render(steps, out_path, data_dir, notebook_path):
    """Genera el HTML del replay y devuelve el numero de bytes escritos.

    Args:
        steps: lista de pasos de visualizacion del episodio.
        out_path: ruta del HTML de salida.
        data_dir: carpeta con EN_Card_Data.csv (y JP opcional).
        notebook_path: ruta al .ipynb del visualizer (fuente de las celdas 4 y 5).

    Returns:
        int: bytes escritos en out_path.
    """
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    # Namespace compartido con los globals que esperan las celdas del notebook.
    ns = {
        "os": os, "csv": csv, "json": json,
        "DATA_DIR": data_dir,
        "OUT_PATH": out_path,
        "__builtins__": __builtins__,
    }
    _exec_cell(nb, _CELL_CARDS, ns)      # loaders de cartas + columnas
    _exec_cell(nb, _CELL_TEMPLATE, ns)   # _HTML_TEMPLATE + generate_html

    ns["card_names_en"] = _build_card_names_en(data_dir)

    ns["generate_html"](steps, out_path)
    _inject_load_button(out_path)
    return os.path.getsize(out_path)
