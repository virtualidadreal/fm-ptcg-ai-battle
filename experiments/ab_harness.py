"""A/B HARNESS for the Pokemon TCG AI Battle (cabt) — LOCAL filter, NOT the judge.

==============================================================================
WARNING — READ THIS:
  The cabt LOCAL environment does NOT predict the ranking of the ladder
  (verified by the top: an opt that scored 62% locally ended up WORSE on the
  ladder). This is a CHEAP FILTER, NOT THE JUDGE. The judge is the real ladder.
  Validate correlation with the ladder before trusting any local result here.
  (ref roadmap section 6 / 11.3)
==============================================================================

Loads two of OUR agent DIRECTORIES (each with main.py + deck.csv) as pre-built
callables at cwd=<agent dir> so each reads its OWN deck.csv ONCE. If a file-loaded
agent fell back to a cwd-relative deck.csv it would silently pilot the OPPONENT's
deck and corrupt every result -- so we use kaggle_environments.agent.get_last_callable
with a chdir into the agent dir BEFORE loading (proven trick from ptcg-abc/tools).

Usage (paths relative to the PROJECT ROOT):
  python experiments/ab_harness.py <dirA> <dirB> [games]
  python experiments/ab_harness.py --panel <dirA> <dir1> <dir2> ... [--games N]

Statistics:
  - Win-rate of A over DECISIVE games (draws excluded) + Wilson 95% interval.
  - "DIFERENCIA SIGNIFICATIVA" declared ONLY if the Wilson interval excludes 0.5.
  - TrueSkill ranking: ratings updated per game; prints final mu/sigma + mu_A - mu_B.
"""
import os
import sys
import math
import warnings

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def load_cb(agent_dir):
    """Load an agent dir as a pre-built callable, reading its own deck.csv once."""
    adir = os.path.join(ROOT, agent_dir)
    main = os.path.join(adir, "main.py")
    if not os.path.exists(main):
        raise SystemExit(f"no main.py in {agent_dir}")
    from kaggle_environments.agent import get_last_callable

    cur = os.getcwd()
    os.chdir(adir)
    try:
        cb = get_last_callable(open(main).read(), path=main)
    finally:
        os.chdir(cur)
    # If the agent exposes my_deck, verify 60 ids. Some agents may not -- that's ok,
    # the deck-phase check below confirms it returns 60 ids regardless.
    md = getattr(cb, "__globals__", {}).get("my_deck")
    if md is not None and len(md) != 60:
        raise SystemExit(f"{agent_dir} my_deck has {len(md)} ids (expected 60)")
    return cb


def verify_deck_phase(cb, name):
    """Confirm the agent returns exactly 60 ids when select is None (deck phase)."""
    try:
        out = cb({"select": None}, None)
    except Exception as e:
        raise SystemExit(f"FATAL: {name} raised on deck-phase probe: {e}")
    if not isinstance(out, list) or len(out) != 60:
        got = len(out) if isinstance(out, list) else type(out)
        # A bad deck phase = INVALID on game 1 = silent loss. Fail loudly.
        raise SystemExit(f"FATAL: {name} returned {got} on deck phase (expected list of 60)")
    print(f"  [ok] {name} deck-phase returns 60 ids")


def wilson(wins, n, z=1.96):
    """Wilson score interval for a binomial proportion. Returns (lo, p, hi)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), p, min(1.0, center + half))


def play_match(cbA, cbB, games):
    """Play `games` matches, alternating A's seat each game. Updates TrueSkill.
    Returns (w, ts, rA, rB) where w=[A wins, B wins, draws]."""
    import trueskill
    from kaggle_environments import make

    ts = trueskill.TrueSkill(draw_probability=0.0)
    rA = ts.create_rating()
    rB = ts.create_rating()
    w = [0, 0, 0]  # A wins, B wins, draws

    for g in range(games):
        env = make("cabt")
        a_seat = 0 if g % 2 == 0 else 1
        order = [cbA, cbB] if a_seat == 0 else [cbB, cbA]
        res = env.run(order)
        r = [s.get("reward") for s in res[-1]]
        ra, rb = r[a_seat], r[1 - a_seat]

        # None reward on a side = that side errored/INVALID = loss for that side.
        if ra is None and rb is None:
            outcome = "draw"
        elif ra is None:
            outcome = "B"
        elif rb is None:
            outcome = "A"
        elif ra > rb:
            outcome = "A"
        elif rb > ra:
            outcome = "B"
        else:
            outcome = "draw"

        if outcome == "A":
            w[0] += 1
            rA, rB = ts.rate_1vs1(rA, rB)
        elif outcome == "B":
            w[1] += 1
            rB, rA = ts.rate_1vs1(rB, rA)
        else:
            w[2] += 1
            # draw: with draw_probability=0.0, rate_1vs1(drawn=True) is degenerate
            # (can raise/skew); draws carry ~no skill signal, so leave ratings unchanged.

        print(f"  game {g+1}/{games}: A={ra} B={rb}  [{w[0]}W/{w[1]}L/{w[2]}D]", flush=True)

    return w, ts, rA, rB


def report_ab(dirA, dirB, w, rA, rB):
    decisive = w[0] + w[1]
    lo, p, hi = wilson(w[0], decisive)
    print()
    print("=" * 70)
    print(f"A = {dirA}")
    print(f"B = {dirB}")
    print(f"Result (A's view): {w[0]}W / {w[1]}L / {w[2]}D   (total {sum(w)} games)")
    if decisive:
        print(f"Win-rate of A over decisive games: {p*100:.1f}%  "
              f"(Wilson 95% IC: {lo*100:.1f}% .. {hi*100:.1f}%)")
        if lo > 0.5:
            print(f"==> DIFERENCIA SIGNIFICATIVA: A es mejor (IC Wilson excluye 0.5).")
        elif hi < 0.5:
            print(f"==> DIFERENCIA SIGNIFICATIVA: B es mejor (IC Wilson excluye 0.5).")
        else:
            print(f"==> Sin diferencia significativa (el IC Wilson incluye 0.5).")
    else:
        print("No decisive games (all draws/errors).")
    print(f"TrueSkill: A mu={rA.mu:.2f} sigma={rA.sigma:.2f} | "
          f"B mu={rB.mu:.2f} sigma={rB.sigma:.2f} | mu_A - mu_B = {rA.mu - rB.mu:+.2f}")
    print("=" * 70)


def run_ab(dirA, dirB, games):
    print(f"[A/B] loading agents...")
    cbA = load_cb(dirA)
    cbB = load_cb(dirB)
    verify_deck_phase(cbA, dirA)
    verify_deck_phase(cbB, dirB)
    w, ts, rA, rB = play_match(cbA, cbB, games)
    report_ab(dirA, dirB, w, rA, rB)
    print_warning()


def run_panel(dirA, rivals, games):
    import trueskill

    print(f"[PANEL] A = {dirA}  vs  {len(rivals)} rivals, {games} games each")
    cbA = load_cb(dirA)
    verify_deck_phase(cbA, dirA)

    rows = []
    agg_w = [0, 0, 0]  # aggregated over all rivals (A's view)

    # One TrueSkill environment across the whole panel: A's rating carries across
    # all rivals, each rival gets its own rating.
    ts = trueskill.TrueSkill(draw_probability=0.0)
    rA = ts.create_rating()

    for rv in rivals:
        cbB = load_cb(rv)
        verify_deck_phase(cbB, rv)
        rB = ts.create_rating()
        from kaggle_environments import make

        w = [0, 0, 0]
        for g in range(games):
            env = make("cabt")
            a_seat = 0 if g % 2 == 0 else 1
            order = [cbA, cbB] if a_seat == 0 else [cbB, cbA]
            res = env.run(order)
            r = [s.get("reward") for s in res[-1]]
            ra, rb = r[a_seat], r[1 - a_seat]
            if ra is None and rb is None:
                outcome = "draw"
            elif ra is None:
                outcome = "B"
            elif rb is None:
                outcome = "A"
            elif ra > rb:
                outcome = "A"
            elif rb > ra:
                outcome = "B"
            else:
                outcome = "draw"
            if outcome == "A":
                w[0] += 1
                rA, rB = ts.rate_1vs1(rA, rB)
            elif outcome == "B":
                w[1] += 1
                rB, rA = ts.rate_1vs1(rB, rA)
            else:
                w[2] += 1
                # draw: leave ratings unchanged (see play_match note).
            print(f"  [{rv}] game {g+1}/{games}: A={ra} B={rb}  [{w[0]}W/{w[1]}L/{w[2]}D]", flush=True)

        rows.append((rv, w, rB))
        agg_w[0] += w[0]
        agg_w[1] += w[1]
        agg_w[2] += w[2]

    print()
    print("=" * 78)
    print(f"PANEL RESULTS — A = {dirA}")
    print("-" * 78)
    print(f"{'rival':<40} {'W/L/D':>10}  {'win% [Wilson 95% IC]':>26}")
    print("-" * 78)
    for rv, w, rB in rows:
        dec = w[0] + w[1]
        lo, p, hi = wilson(w[0], dec)
        wld = f"{w[0]}/{w[1]}/{w[2]}"
        if dec:
            stat = f"{p*100:.0f}% [{lo*100:.0f}-{hi*100:.0f}]"
        else:
            stat = "n/a"
        print(f"{rv:<40} {wld:>10}  {stat:>26}")
    print("-" * 78)
    agg_dec = agg_w[0] + agg_w[1]
    lo, p, hi = wilson(agg_w[0], agg_dec)
    print(f"{'AGGREGATE':<40} {agg_w[0]}/{agg_w[1]}/{agg_w[2]:>0}")
    if agg_dec:
        print(f"Aggregate win-rate of A: {p*100:.1f}%  (Wilson 95% IC: {lo*100:.1f}% .. {hi*100:.1f}%)")
        if lo > 0.5:
            print("==> DIFERENCIA SIGNIFICATIVA (agregado): A es mejor que el panel.")
        elif hi < 0.5:
            print("==> DIFERENCIA SIGNIFICATIVA (agregado): A es peor que el panel.")
        else:
            print("==> Sin diferencia significativa agregada (IC incluye 0.5).")
        print("    (NB: el agregado mezcla rivales heterogeneos -> el Wilson agregado viola i.i.d.;")
        print("     fiate de la tabla POR-RIVAL para el veredicto real.)")
    print(f"TrueSkill A: mu={rA.mu:.2f} sigma={rA.sigma:.2f}")
    for rv, w, rB in rows:
        print(f"  vs {rv}: rival mu={rB.mu:.2f} sigma={rB.sigma:.2f} | mu_A - mu_rival = {rA.mu - rB.mu:+.2f}")
    print("=" * 78)
    print_warning()


def print_warning():
    print()
    print("!" * 78)
    print("WARNING: el cabt LOCAL no predice el ranking del ladder (verificado por el")
    print("campo top: una opt 62% local quedo PEOR en ladder). Esto es un FILTRO barato,")
    print("NO el JUEZ. El juez es el ladder real. Valida correlacion con el ladder antes")
    print("de fiarte. (ref roadmap seccion 6 / 11.3)")
    print("!" * 78)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        raise SystemExit(2)

    if args[0] == "--panel":
        rest = args[1:]
        games = 20
        # extract --games N
        if "--games" in rest:
            i = rest.index("--games")
            games = int(rest[i + 1])
            rest = rest[:i] + rest[i + 2:]
        if len(rest) < 2:
            raise SystemExit("--panel needs <dirA> <rival1> [rival2 ...]")
        dirA = rest[0]
        rivals = rest[1:]
        run_panel(dirA, rivals, games)
    else:
        dirA = args[0]
        dirB = args[1]
        games = int(args[2]) if len(args) > 2 else 40
        run_ab(dirA, dirB, games)


if __name__ == "__main__":
    main()
