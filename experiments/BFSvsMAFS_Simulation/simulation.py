import random
import csv
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Set

# GRAPH BUILDER
def build_graph(V: int, epn: float) -> list[list[int]]:
    """
    Random connected graph:
      - Random spanning tree (guarantees connectivity)
      - Extra random edges until edge count ≈ V * epn
    """
    adj = [[] for _ in range(V)]
    seen: set[tuple] = set()

    def link(a, b):
        key = (min(a, b), max(a, b))
        if a != b and key not in seen:
            seen.add(key)
            adj[a].append(b)
            adj[b].append(a)

    # Random spanning tree
    perm = list(range(V))
    random.shuffle(perm)
    for i in range(1, V):
        link(perm[i], perm[random.randint(0, i - 1)])

    # Extra edges
    extra = int(V * epn)
    attempts = 0
    while len(seen) - (V - 1) < extra and attempts < extra * 8:
        link(random.randint(0, V - 1), random.randint(0, V - 1))
        attempts += 1

    return adj

# TRADITIONAL BFS  (Na sequential runs)
def run_traditional(adj: list, src: int, targets: list[int]) -> int:
    """
    One BFS per target, starting from src, stopping when target is found.
    Returns total node visits across all runs.
    """
    V = len(adj)
    total_ops = 0

    for tgt in targets:
        visited = [False] * V
        visited[src] = True
        q = deque([src])

        while q:
            u = q.popleft()
            total_ops += 1
            if u == tgt:
                break
            for v in adj[u]:
                if not visited[v]:
                    visited[v] = True
                    q.append(v)

    return total_ops

# MAFS  (parallel BFS + Eidetic Memory Fusion)
@dataclass
class Cluster:
    mem: Set[int]        # all nodes ever visited by this cluster
    front: Set[int]      # current BFS frontier
    size: int            # number of original agents merged into this cluster


def run_mafs(adj: list, src: int, targets: list[int]) -> dict:
    """
    All agents (src + targets) run BFS simultaneously.
    Fusion: when cluster A's frontier intersects cluster B's memory → merge.
    Returns ops count, fusion events, and fusion work cost.
    """
    V = len(adj)

    clusters: List[Cluster] = [
        Cluster(mem={s}, front={s}, size=1)
        for s in [src] + list(targets)
    ]

    ops = len(clusters)          # initial placements
    fusion_events = 0
    fusion_work = 0

    for _ in range(V + 10):
        if not any(c.front for c in clusters):
            break

        # ── Expand each cluster one BFS level ──
        for c in clusters:
            nxt = set()
            for u in c.front:
                for v in adj[u]:
                    if v not in c.mem:
                        nxt.add(v)
            c.mem.update(nxt)
            ops += len(nxt)
            c.front = nxt

        # ── Detect and execute fusions ──
        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(clusters):
                j = i + 1
                while j < len(clusters):
                    a, b = clusters[i], clusters[j]
                    # Check frontier ∩ memory overlap
                    hit = bool(a.front & b.mem) or bool(b.front & a.mem)
                    if hit:
                        fusion_events += 1
                        fusion_work += min(len(a.mem), len(b.mem))
                        # Merge b into a
                        new_mem = a.mem | b.mem
                        new_front = (
                            (a.front - b.mem) | (b.front - a.mem)
                        )
                        clusters[i] = Cluster(
                            mem=new_mem,
                            front=new_front,
                            size=a.size + b.size
                        )
                        clusters.pop(j)
                        merged = True
                        break
                    j += 1
                if merged:
                    break
                i += 1

        # Remove exhausted clusters
        clusters = [c for c in clusters if c.front]
        if len(clusters) <= 1:
            break

    return {"ops": ops, "fusion_events": fusion_events, "fusion_work": fusion_work}

# TRIAL RUNNER  (averaged over multiple random graphs)
def run_trial(V: int, Na: int, epn: float, runs: int = 10) -> dict:
    t_sum = m_sum = fw_sum = fe_sum = 0

    for _ in range(runs):
        adj = build_graph(V, epn)
        perm = list(range(V))
        random.shuffle(perm)
        src = perm[0]
        tgts = perm[1: Na + 1]

        t_sum += run_traditional(adj, src, tgts)
        m = run_mafs(adj, src, tgts)
        m_sum += m["ops"]
        fw_sum += m["fusion_work"]
        fe_sum += m["fusion_events"]

    t = t_sum / runs
    m = m_sum / runs
    fw = fw_sum / runs
    fe = fe_sum / runs
    m_net = m + fw

    speedup     = round((t - m)     / t * 100, 1) if t > 0 else 0.0
    speedup_net = round(max(0, (t - m_net) / t * 100), 1) if t > 0 else 0.0

    return {
        "traditional":    round(t),
        "mafs":           round(m),
        "mafs_net":       round(m_net),
        "fusion_events":  round(fe),
        "speedup":        speedup,
        "speedup_net":    speedup_net,
    }

# DISPLAY HELPERS
def fmt(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)

def bar(pct: float, width: int = 30) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")

# MAIN
def main():
    # ── Default config (mirrors the JSX defaults) ──
    V   = 120      # graph nodes
    Na  = 8        # number of target agents
    epn = 1.5      # edge density multiplier

    print("╔══════════════════════════════════════════════════════════╗")
    print("║              MAFS Simulation Lab — Python                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nConfig: V={V} nodes, Na={Na} agents, edge density ×{epn}")
    print("(Edit V, Na, epn at the top of main() to change parameters)\n")

    # ── 1. Single simulation ──
    section("1 · Single Simulation")
    print("Running 15 trials and averaging…")
    t0 = time.time()
    r = run_trial(V, Na, epn, runs=15)
    elapsed = time.time() - t0

    print(f"\n  Traditional visits : {fmt(r['traditional']):>8}  ({Na} sequential BFS)")
    print(f"  MAFS visits (gross): {fmt(r['mafs']):>8}  ({r['fusion_events']} fusion events)")
    print(f"  MAFS visits (net)  : {fmt(r['mafs_net']):>8}  (gross + fusion union cost)")
    print(f"\n  Gross speedup : {r['speedup']:>5.1f}%  {bar(r['speedup'])}")
    print(f"  Net speedup   : {r['speedup_net']:>5.1f}%  {bar(r['speedup_net'])}")
    print(f"\n  Computed in {elapsed:.2f}s")

    # ── 2. Sweep by Na ──
    section("2 · Sweep by Na (Agents)  [V=100 fixed]")
    sweep_na = []
    print(f"  {'Na':>4}  {'Trad':>7}  {'MAFS':>7}  {'Gross%':>7}  {'Net%':>7}  {'Theory%':>8}  Bar")
    print(f"  {'─'*4}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*8}  {'─'*20}")
    for na in range(2, 25, 2):
        r2 = run_trial(100, na, epn, runs=6)
        theory = round(max(0, (1 - 2 / na) * 100), 1)
        sweep_na.append({
            "Na": na,
            "traditional": r2["traditional"],
            "mafs": r2["mafs"],
            "speedup": r2["speedup"],
            "speedup_net": r2["speedup_net"],
            "theoretical": theory
        })
        print(f"  {na:>4}  {fmt(r2['traditional']):>7}  {fmt(r2['mafs']):>7}  "
              f"{r2['speedup']:>6.1f}%  {r2['speedup_net']:>6.1f}%  {theory:>7.1f}%  "
              f"{bar(r2['speedup'], 20)}")

    # Key thresholds
    thresholds = [(20, 40, 60)]
    print("\n  Key thresholds:")
    for pct in [20, 40, 60]:
        hit = next((d for d in sweep_na if d["speedup"] >= pct), None)
        if hit:
            print(f"    >{pct}% gross speedup first reached at Na = {hit['Na']}")
        else:
            print(f"    >{pct}% speedup not reached in this range")

    # ── 3. Sweep by V ──
    section("3 · Sweep by V (Graph Size)  [Na fixed]")
    sweep_v = []
    print(f"  {'V':>5}  {'Trad':>8}  {'MAFS':>8}  {'Speedup%':>9}  Bar")
    print(f"  {'─'*5}  {'─'*8}  {'─'*8}  {'─'*9}  {'─'*22}")
    for v in range(50, 281, 20):
        r3 = run_trial(v, Na, epn, runs=6)
        sweep_v.append({
            "V": v,
            "traditional": r3["traditional"],
            "mafs": r3["mafs"],
            "speedup": r3["speedup"]
        })
        print(f"  {v:>5}  {fmt(r3['traditional']):>8}  {fmt(r3['mafs']):>8}  "
              f"{r3['speedup']:>8.1f}%  {bar(r3['speedup'], 22)}")

    speeds = [d["speedup"] for d in sweep_v]
    min_s = min(speeds); max_s = max(speeds)
    min_v = sweep_v[speeds.index(min_s)]["V"]
    max_v = sweep_v[speeds.index(max_s)]["V"]
    print(f"\n  Range: min {min_s}% at V={min_v}  →  max {max_s}% at V={max_v}")

    # ── 4. Save CSV ──
    section("4 · Saving Results to CSV")
    with open("mafs_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sweep", "param", "traditional", "mafs", "speedup_pct", "speedup_net_pct", "theoretical_pct"])
        for d in sweep_na:
            w.writerow(["Na_sweep", d["Na"], d["traditional"], d["mafs"],
                        d["speedup"], d["speedup_net"], d["theoretical"]])
        for d in sweep_v:
            w.writerow(["V_sweep", d["V"], d["traditional"], d["mafs"],
                        d["speedup"], "", ""])
    print("  Saved → bfs_mafs_results.csv  (open in Excel / any spreadsheet app)")

    print(f"\n{'═' * 60}")
    print("  Done.")
    print(f"{'═' * 60}\n")
    print("Methodology: Unweighted random connected graphs (random spanning")
    print("tree + extra random edges). Agents at uniformly random positions.")
    print("BFS traditional stops on target found. MAFS terminates on single-")
    print("cluster merge. Fusion trigger: frontier(A) ∩ memory(B) ≠ ∅.")
    print("Fusion cost = O(min|A|,|B|) hash union. Each point avg 6–15 trials.")
    print("Theoretical ceiling = 1 − 2/Na.\n")


if __name__ == "__main__":
    main()