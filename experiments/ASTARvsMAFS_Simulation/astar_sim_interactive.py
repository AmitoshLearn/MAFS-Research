# MAFS vs A* Simulation Lab — interactive version
# Run: python mafs_astar_simulation_interactive.py

import random
import csv
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import List
import heapq


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph(V: int, epn: float):
    pos = [(random.random(), random.random()) for _ in range(V)]
    adj = [[] for _ in range(V)]
    seen: set[tuple] = set()

    def link(a, b):
        key = (min(a, b), max(a, b))
        if a != b and key not in seen:
            seen.add(key)
            adj[a].append(b)
            adj[b].append(a)

    perm = list(range(V))
    random.shuffle(perm)
    for i in range(1, V):
        link(perm[i], perm[random.randint(0, i - 1)])

    target = int(V * epn)
    attempts = 0
    while len(seen) - (V - 1) < target and attempts < target * 12:
        link(random.randint(0, V - 1), random.randint(0, V - 1))
        attempts += 1

    return adj, pos


def edist(pos, a, b) -> float:
    dx = pos[a][0] - pos[b][0]
    dy = pos[a][1] - pos[b][1]
    return math.sqrt(dx * dx + dy * dy)


# ── Algorithm 1: Sequential BFS ────────────────────────────────────────────────

def run_bfs(adj: list, src: int, targets: list[int]) -> int:
    V = len(adj)
    total_ops = 0
    for tgt in targets:
        visited = bytearray(V)
        visited[src] = 1
        q = deque([src])
        while q:
            u = q.popleft()
            total_ops += 1
            if u == tgt:
                break
            for v in adj[u]:
                if not visited[v]:
                    visited[v] = 1
                    q.append(v)
    return total_ops


# ── Algorithm 2: Sequential A* ─────────────────────────────────────────────────

def run_astar(adj: list, pos: list, src: int, targets: list[int]) -> int:
    V = len(adj)
    total_ops = 0
    for tgt in targets:
        visited = bytearray(V)
        g = [math.inf] * V
        g[src] = 0
        pq = [(edist(pos, src, tgt), src)]
        while pq:
            _, u = heapq.heappop(pq)
            if visited[u]:
                continue  # lazy deletion
            visited[u] = 1
            total_ops += 1
            if u == tgt:
                break
            for v in adj[u]:
                ng = g[u] + 1
                if ng < g[v]:
                    g[v] = ng
                    heapq.heappush(pq, (ng + edist(pos, v, tgt), v))
    return total_ops


# ── Algorithm 3: MAFS-BFS ──────────────────────────────────────────────────────

@dataclass
class BFSCluster:
    mem: bytearray
    front: list
    mem_count: int
    n: int


def run_mafs_bfs(adj: list, src: int, targets: list[int]) -> dict:
    V = len(adj)
    ops = 0
    fusion_work = 0
    fusion_events = 0

    clusters: List[BFSCluster] = []
    for s in [src] + list(targets):
        mem = bytearray(V)
        mem[s] = 1
        clusters.append(BFSCluster(mem=mem, front=[s], mem_count=1, n=1))
    ops += len(clusters)

    for _ in range(V + 10):
        if not any(c.front for c in clusters):
            break
        for c in clusters:
            nxt = []
            for u in c.front:
                for v in adj[u]:
                    if not c.mem[v]:
                        c.mem[v] = 1
                        c.mem_count += 1
                        ops += 1
                        nxt.append(v)
            c.front = nxt

        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(clusters):
                j = i + 1
                while j < len(clusters):
                    a, b = clusters[i], clusters[j]
                    hit = any(b.mem[n] for n in a.front) or any(a.mem[n] for n in b.front)
                    if hit:
                        fusion_events += 1
                        big, small = (a, b) if a.mem_count >= b.mem_count else (b, a)
                        fusion_work += small.mem_count
                        for v in range(V):
                            if small.mem[v] and not big.mem[v]:
                                big.mem[v] = 1
                                big.mem_count += 1
                        new_front = list(big.front)
                        for n in small.front:
                            if not big.mem[n]:
                                big.mem[n] = 1
                                big.mem_count += 1
                                new_front.append(n)
                        big.front = new_front
                        big.n += small.n
                        big_idx = i if a.mem_count >= b.mem_count else j
                        small_idx = j if a.mem_count >= b.mem_count else i
                        clusters[big_idx] = big
                        clusters.pop(small_idx)
                        merged = True
                        break
                    j += 1
                if merged:
                    break
                i += 1

        clusters = [c for c in clusters if c.front]
        if len(clusters) <= 1:
            break

    return {"ops": ops, "fusion_work": fusion_work, "fusion_events": fusion_events}


# ── Algorithm 4: MAFS-Flow ─────────────────────────────────────────────────────

@dataclass
class FlowCluster:
    mem: bytearray
    g: list
    pq: list
    front: list
    mem_count: int
    n: int


def run_mafs_flow(adj: list, pos: list, src: int, targets: list[int]) -> dict:
    V = len(adj)
    ops = 0
    fusion_work = 0
    fusion_events = 0

    clusters: List[FlowCluster] = []
    for s in [src] + list(targets):
        mem = bytearray(V)
        mem[s] = 1
        g = [math.inf] * V
        g[s] = 0
        pq = [(1.0, s)]
        clusters.append(FlowCluster(mem=mem, g=g, pq=pq, front=[s], mem_count=1, n=1))
    ops += len(clusters)

    for _ in range(V * 3):
        any_active = False
        for c in clusters:
            if not c.pq:
                continue
            any_active = True
            nxt_front = []
            budget = max(1, V // len(clusters))
            expanded = 0
            while c.pq and expanded < budget:
                _, u = heapq.heappop(c.pq)
                if not c.mem[u]:
                    continue
                expanded += 1
                ops += 1
                for v in adj[u]:
                    if c.mem[v]:
                        continue
                    c.mem[v] = 1
                    c.mem_count += 1
                    gv = c.g[u] + 1
                    c.g[v] = gv
                    cost = (1.0 / c.n) + gv  # fusion boost: larger cluster = lower cost
                    heapq.heappush(c.pq, (cost, v))
                    nxt_front.append(v)
            c.front = nxt_front
        if not any_active:
            break

        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(clusters):
                j = i + 1
                while j < len(clusters):
                    a, b = clusters[i], clusters[j]
                    hit = any(b.mem[n] for n in a.front) or any(a.mem[n] for n in b.front)
                    if hit:
                        fusion_events += 1
                        big, small = (a, b) if a.mem_count >= b.mem_count else (b, a)
                        fusion_work += small.mem_count
                        new_n = big.n + small.n
                        for v in range(V):
                            if small.mem[v] and not big.mem[v]:
                                big.mem[v] = 1
                                big.mem_count += 1
                        for _, v in small.pq:
                            if not big.mem[v]:
                                heapq.heappush(big.pq, ((1.0 / new_n) + small.g[v], v))
                        new_pq = []
                        for _, v in big.pq:
                            if not big.mem[v]:
                                heapq.heappush(new_pq, ((1.0 / new_n) + big.g[v], v))
                        big.pq = new_pq
                        big.n = new_n
                        big.front = big.front + small.front
                        big_idx = i if a.mem_count >= b.mem_count else j
                        small_idx = j if a.mem_count >= b.mem_count else i
                        clusters[big_idx] = big
                        clusters.pop(small_idx)
                        merged = True
                        break
                    j += 1
                if merged:
                    break
                i += 1

        clusters = [c for c in clusters if c.pq or c.front]
        if len(clusters) <= 1:
            break

    return {"ops": ops, "fusion_work": fusion_work, "fusion_events": fusion_events}


# ── Trial runner ───────────────────────────────────────────────────────────────

def run_trial(V: int, Na: int, epn: float, runs: int = 8) -> dict:
    bfs_sum = astar_sum = 0
    mafs_ops_sum = mafs_net_sum = 0
    flow_ops_sum = flow_net_sum = 0

    for _ in range(runs):
        adj, pos = build_graph(V, epn)
        perm = list(range(V))
        random.shuffle(perm)
        src = perm[0]
        tgts = perm[1: Na + 1]

        bfs_sum   += run_bfs(adj, src, tgts)
        astar_sum += run_astar(adj, pos, src, tgts)

        m = run_mafs_bfs(adj, src, tgts)
        mafs_ops_sum += m["ops"]
        mafs_net_sum += m["ops"] + m["fusion_work"]

        f = run_mafs_flow(adj, pos, src, tgts)
        flow_ops_sum += f["ops"]
        flow_net_sum += f["ops"] + f["fusion_work"]

    bfs      = round(bfs_sum      / runs)
    astar    = round(astar_sum    / runs)
    mafs     = round(mafs_ops_sum / runs)
    mafs_net = round(mafs_net_sum / runs)
    flow     = round(flow_ops_sum / runs)
    flow_net = round(flow_net_sum / runs)

    def pct(base, val):
        return round(max(0.0, (base - val) / base * 100), 1) if base > 0 else 0.0

    return {
        "bfs": bfs, "astar": astar,
        "mafs": mafs, "mafs_net": mafs_net,
        "flow": flow, "flow_net": flow_net,
        "astar_vs_bfs":      pct(bfs,   astar),
        "mafs_vs_bfs_net":   pct(bfs,   mafs_net),
        "mafs_vs_astar_net": pct(astar, mafs_net),
        "flow_vs_bfs_net":   pct(bfs,   flow_net),
        "flow_vs_astar_net": pct(astar, flow_net),
    }


# ── Display helpers ────────────────────────────────────────────────────────────

def fmt(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)

def bar(pct: float, width: int = 26) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def section(title: str):
    print(f"\n{'═' * 64}")
    print(f"  {title}")
    print(f"{'═' * 64}")

def divider():
    print(f"  {'─' * 60}")


# ── Input helpers ──────────────────────────────────────────────────────────────

def ask_int(prompt: str, default: int, lo: int, hi: int) -> int:
    while True:
        raw = input(f"  {prompt} [{lo}–{hi}, default {default}]: ").strip()
        if raw == "":
            print(f"    → Using default: {default}")
            return default
        try:
            val = int(raw)
            if lo <= val <= hi:
                return val
            print(f"    ✗  Enter a value between {lo} and {hi}.")
        except ValueError:
            print("    ✗  That doesn't look like a whole number.")

def ask_float(prompt: str, default: float, lo: float, hi: float) -> float:
    while True:
        raw = input(f"  {prompt} [{lo}–{hi}, default {default}]: ").strip()
        if raw == "":
            print(f"    → Using default: {default}")
            return default
        try:
            val = float(raw)
            if lo <= val <= hi:
                return val
            print(f"    ✗  Enter a value between {lo} and {hi}.")
        except ValueError:
            print("    ✗  That doesn't look like a number.")

def ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"  {prompt} [{hint}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("    ✗  Please enter y or n.")

def ask_mode() -> str:
    print("\n  Which simulations would you like to run?")
    print("    1 · Single run only")
    print("    2 · Single run + sweep by Na (agents)")
    print("    3 · Single run + sweep by V (graph size)")
    print("    4 · All of the above  (default)")
    while True:
        raw = input("  Enter 1–4 [default 4]: ").strip()
        if raw in ("", "4"): return "all"
        if raw == "1": return "single"
        if raw == "2": return "na"
        if raw == "3": return "v"
        print("    ✗  Please enter 1, 2, 3, or 4.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║         MAFS vs A* Simulation Lab — Interactive               ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("\n  Press Enter at any prompt to accept the default value.\n")

    section("Step 1 · Set Parameters")
    V   = ask_int  ("Graph nodes  V",            150,  40,  500)
    Na  = ask_int  ("Target agents  Na",          15,   2,   40)
    epn = ask_float("Edge density  (×N per node)", 2.5, 1.0,  5.0)
    runs_single = ask_int("Trials per single run", 10,   5,   50)

    section("Step 2 · Choose Simulations")
    mode = ask_mode()

    all_results = []

    section("Running · Single Simulation")
    print(f"  Config: V={V}, Na={Na}, density=×{epn}, trials={runs_single}")
    print("  Computing…")
    t0 = time.time()
    r = run_trial(V, Na, epn, runs=runs_single)
    elapsed = time.time() - t0

    print(f"\n  {'Metric':<30} {'Value':>10}")
    divider()
    print(f"  {'BFS visits':<30} {fmt(r['bfs']):>10}  ({Na} sequential runs)")
    print(f"  {'A* visits':<30} {fmt(r['astar']):>10}  (Euclidean heuristic)")
    print(f"  {'MAFS-BFS (gross)':<30} {fmt(r['mafs']):>10}")
    print(f"  {'MAFS-BFS (net)':<30} {fmt(r['mafs_net']):>10}  (+ fusion overhead)")
    print(f"  {'MAFS-Flow (net)':<30} {fmt(r['flow_net']):>10}  (+ fusion overhead)")
    divider()
    print(f"  {'A* vs BFS':<30} {r['astar_vs_bfs']:>9.1f}%  {bar(r['astar_vs_bfs'])}")
    print(f"  {'MAFS-BFS vs BFS (net)':<30} {r['mafs_vs_bfs_net']:>9.1f}%  {bar(r['mafs_vs_bfs_net'])}")
    print(f"  {'MAFS-BFS vs A* (net)':<30} {r['mafs_vs_astar_net']:>9.1f}%  {bar(r['mafs_vs_astar_net'])}")
    print(f"  {'MAFS-Flow vs A* (net)':<30} {r['flow_vs_astar_net']:>9.1f}%  {bar(r['flow_vs_astar_net'])}")
    print(f"\n  Completed in {elapsed:.2f}s")

    all_results.append({"sweep": "single", "param": f"V={V},Na={Na},epn={epn}", **r})

    if mode in ("na", "all"):
        section("Running · Sweep by Na  (V=100 fixed)")
        na_max     = ask_int("Maximum Na to sweep up to", 24, 4, 40)
        na_step    = ask_int("Step size", 2, 1, 8)
        runs_sweep = ask_int("Trials per sweep point", 6, 3, 20)
        print()

        sweep_na = []
        print(f"  {'Na':>4}  {'BFS':>6}  {'A*':>6}  {'MAFS-net':>9}  {'Flow-net':>9}  "
              f"{'MAFS/A*%':>9}  {'Flow/A*%':>9}  Bar")
        divider()

        for na in range(2, na_max + 1, na_step):
            r2 = run_trial(100, na, epn, runs=runs_sweep)
            sweep_na.append({"Na": na, **r2})
            all_results.append({"sweep": "Na_sweep", "param": na, **r2})
            print(f"  {na:>4}  {fmt(r2['bfs']):>6}  {fmt(r2['astar']):>6}  "
                  f"{fmt(r2['mafs_net']):>9}  {fmt(r2['flow_net']):>9}  "
                  f"{r2['mafs_vs_astar_net']:>8.1f}%  {r2['flow_vs_astar_net']:>8.1f}%  "
                  f"{bar(r2['mafs_vs_astar_net'], 18)}")

        print("\n  Key thresholds (vs A* — the honest benchmark):")
        for t in [15, 30, 50]:
            mafs_hit = next((d for d in sweep_na if d["mafs_vs_astar_net"] >= t), None)
            flow_hit = next((d for d in sweep_na if d["flow_vs_astar_net"] >= t), None)
            print(f"    >{t}%  MAFS-BFS: Na >= {mafs_hit['Na'] if mafs_hit else 'not reached'}   "
                  f"MAFS-Flow: Na >= {flow_hit['Na'] if flow_hit else 'not reached'}")

    if mode in ("v", "all"):
        section("Running · Sweep by V  (Na fixed)")
        v_min        = ask_int("Minimum V", 50,  20, 200)
        v_max        = ask_int("Maximum V", 300, 60, 600)
        v_step       = ask_int("Step size", 25,   5,  50)
        runs_sweep_v = ask_int("Trials per sweep point", 6, 3, 20)
        print()

        sweep_v = []
        print(f"  {'V':>5}  {'BFS':>7}  {'A*':>7}  {'MAFS-net':>9}  {'Flow-net':>9}  "
              f"{'MAFS/A*%':>9}  Bar")
        divider()

        for v in range(v_min, v_max + 1, v_step):
            r3 = run_trial(v, Na, epn, runs=runs_sweep_v)
            sweep_v.append({"V": v, **r3})
            all_results.append({"sweep": "V_sweep", "param": v, **r3})
            print(f"  {v:>5}  {fmt(r3['bfs']):>7}  {fmt(r3['astar']):>7}  "
                  f"{fmt(r3['mafs_net']):>9}  {fmt(r3['flow_net']):>9}  "
                  f"{r3['mafs_vs_astar_net']:>8.1f}%  {bar(r3['mafs_vs_astar_net'], 20)}")

        if sweep_v:
            speeds = [d["mafs_vs_astar_net"] for d in sweep_v]
            print(f"\n  MAFS-BFS vs A* range: min {min(speeds):.1f}%  ->  max {max(speeds):.1f}%")

    section("Saving Results")
    if ask_yes_no("Save results to CSV?", default=True):
        filename = "mafs_astar_results_interactive.csv"
        fields = [
            "sweep", "param",
            "bfs", "astar", "mafs", "mafs_net", "flow", "flow_net",
            "astar_vs_bfs", "mafs_vs_bfs_net", "mafs_vs_astar_net",
            "flow_vs_bfs_net", "flow_vs_astar_net",
        ]
        with open(filename, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in all_results:
                w.writerow({k: row.get(k, "") for k in fields})
        print(f"\n  Saved -> {filename}")
    else:
        print("  Skipped.")

    print(f"\n{'=' * 64}")
    print("  All done! Re-run any time to try new parameters.")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()