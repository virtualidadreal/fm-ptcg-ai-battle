#!/usr/bin/env python3
"""
Spearman rho entre el WR local cabt-vs-first-legal y el score REAL del ladder.

Tesis (PTCG / Sabrina): ningun proxy local predice el ladder. Aqui se cuantifica
sobre los 4 puntos reales que tenemos. Si rho < 0, maximizar el cabt BAJA el ladder.

Reproducible, sin internet. Usa scipy si esta disponible; si no, implementa
Spearman a mano: rho = 1 - 6*sum(d^2) / (n*(n^2-1)) con rangos.

Datos (verificados en memoria-claude/proyectos/ptcg-pivote-sabrina-alakazam.md
y en el repo donde estan; coinciden):
  - ladder score REAL:  v1=826.9, Dragapult=778.2, v2=722.5, Mega Starmie=641.2
  - cabt-vs-first-legal: v1=80%,  Dragapult=85%,   v2=92%,  Mega Starmie=87%

Nota: el cabt de Dragapult (85%) procede del enunciado/handoff; v1/v2/Mega
(80/92/87) constan ademas en la memoria. No difieren del repo.

Ejecutar:
  .venv/bin/python research/correlation.py
"""

# (etiqueta, cabt_pct, ladder_score)
DATA = [
    ("Sabrina v1",   80.0, 826.9),
    ("Dragapult",    85.0, 778.2),
    ("Sabrina v2",   92.0, 722.5),
    ("Mega Starmie", 87.0, 641.2),
]


def rank(values):
    """Rangos 1..n con promedio en empates (rango medio)."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        # rango medio para el grupo [i, j]
        avg = (i + j) / 2.0 + 1.0  # +1 porque los rangos empiezan en 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_manual(x, y):
    """rho = 1 - 6*sum(d^2) / (n*(n^2-1)). Valido sin empates; con empates
    es una aproximacion (aqui no hay empates en ninguna de las dos series)."""
    n = len(x)
    rx = rank(x)
    ry = rank(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    rho = 1.0 - (6.0 * d2) / (n * (n * n - 1))
    return rho, rx, ry, d2


def main():
    labels = [d[0] for d in DATA]
    cabt = [d[1] for d in DATA]
    ladder = [d[2] for d in DATA]
    n = len(DATA)

    rho_m, rx, ry, d2 = spearman_manual(cabt, ladder)

    print("=" * 64)
    print("Spearman rho: cabt-vs-first-legal  vs  ladder score (n=%d)" % n)
    print("=" * 64)
    print()
    print("%-14s %8s %8s %8s %8s" % ("agente", "cabt%", "ladder", "R(cabt)", "R(ladder)"))
    print("-" * 56)
    for i in range(n):
        print("%-14s %8.1f %8.1f %8.1f %8.1f" % (labels[i], cabt[i], ladder[i], rx[i], ry[i]))
    print()
    print("sum d^2 = %.1f" % d2)
    print("rho (formula a mano: 1 - 6*sum(d^2)/(n*(n^2-1))) = %+.4f" % rho_m)

    # scipy si esta disponible (verificacion cruzada)
    try:
        from scipy.stats import spearmanr
        rho_s, p = spearmanr(cabt, ladder)
        print("rho (scipy.stats.spearmanr)                       = %+.4f  (p=%.4f)" % (rho_s, p))
        used, val = "scipy", rho_s
    except Exception as e:  # noqa: BLE001
        print("scipy no disponible (%s); uso la formula a mano." % e)
        used, val = "manual", rho_m

    print()
    print("rho FINAL (%s) = %+.4f" % (used, val))
    print("Confirma -0.80 (tol 1e-9): %s" % (abs(val - (-0.80)) < 1e-9))
    print()
    print("Lectura: rho<0 => maximizar el cabt local BAJA el ladder. El proxy")
    print("local es ANTI-predictivo; el ladder es el unico juez.")


if __name__ == "__main__":
    main()
