# MAFS Simulation Lab — Interactive Version
# Run: python mafs_simulation_interactive.py

import random
import csv
import time
from collections import deque
from dataclasses import dataclass
from typing import List, Set


def build_graph(V: int, epn: float) -> list[list[int]]:
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

    extra = int(V * epn)
    attempts = 0
    while len(seen) - (V - 1) < extra and attempts < extra * 8:
        link(random.randint(0, V - 1), random.randint(0, V - 1))
        attempts += 1

    return adj


def run_traditional(adj: list, src: int, targets: list[int]) -> int:
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


@dataclass
class Cluster:
    mem: Set[int]
    front: Set[int]
    size: int


def run_mafs(adj: list, src: int, targets: list[int]) -> dict:
    V = len(adj)
    clusters: List[Cluster] = [
        Cluster(mem={s}, front={s}, size=1)
        for s in [src] + list(targets)
    ]
    ops = len(clusters)
    fusion_events = 0
    fusion_work = 0

    for _ in range(V + 10):
        if not any(c.front for c in clusters):
            break
        for c in clusters:
            nxt = set()
            for u in c.front:
                for v in adj[u]:
                    if v not in c.mem:
                        nxt.add(v)
            c.mem.update(nxt)
            ops += len(nxt)
            c.front = nxt

        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(clusters):
                j = i + 1
                while j < len(clusters):
                    a, b = clusters[i], clusters[j]
                    hit = bool(a.front & b.mem) or bool(b.front & a.mem)
                    if hit:
                        fusion_events += 1
                        fusion_work += min(len(a.mem), len(b.mem))
                        clusters[i] = Cluster(
                            mem=a.mem | b.mem,
                            front=(a.front - b.mem) | (b.front - a.mem),
                            size=a.size + b.size
                        )
                        clusters.pop(j)
                        merged = True
                        break
                    j += 1
                if merged:
                    break
                i += 1

        clusters = [c for c in clusters if c.front]
        if len(clusters) <= 1:
            break

    return {"ops": ops, "fusion_events": fusion_events, "fusion_work": fusion_work}


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

    return {
        "traditional":   round(t),
        "mafs":          round(m),
        "mafs_net":      round(m_net),
        "fusion_events": round(fe),
        "speedup":       round((t - m) / t * 100, 1) if t > 0 else 0.0,
        "speedup_net":   round(max(0, (t - m_net) / t * 100), 1) if t > 0 else 0.0,
    }


def fmt(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)

def bar(pct: float, width: int = 28) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def section(title: str):
    print(f"\n{'═' * 62}")
    print(f"  {title}")
    print(f"{'═' * 62}")

def divider():
    print(f"  {'─' * 58}")


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
            print(f"    ✗  Please enter a value between {lo} and {hi}.")
        except ValueError:
            print(f"    ✗  That doesn't look like a whole number. Try again.")

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
            print(f"    ✗  Please enter a value between {lo} and {hi}.")
        except ValueError:
            print(f"    ✗  That doesn't look like a number. Try again.")

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
        if raw == "" or raw == "4":
            return "all"
        if raw == "1":
            return "single"
        if raw == "2":
            return "na"
        if raw == "3":
            return "v"
        print("    ✗  Please enter 1, 2, 3, or 4.")


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         MAFS Simulation Lab — Interactive Version           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("  Press Enter at any prompt to accept the default value.")
    print("  All results are saved to  mafs_results_interactive.csv\n")

    section("Step 1 · Set Parameters")
    V   = ask_int  ("Graph nodes  V",            120,  40,  500)
    Na  = ask_int  ("Target agents  Na",           8,   2,   40)
    epn = ask_float("Edge density  (×N per node)", 1.5, 1.0,  5.0)
    runs_single = ask_int("Trials per single run", 15,  5,   50)

    section("Step 2 · Choose Simulations")
    mode = ask_mode()

    all_results = []

    section("Running · Single Simulation")
    print(f"  Config: V={V}, Na={Na}, density=×{epn}, trials={runs_single}")
    print("  Computing…")
    t0 = time.time()
    r = run_trial(V, Na, epn, runs=runs_single)
    elapsed = time.time() - t0

    print(f"\n  ┌─────────────────────────────────────────────────┐")
    print(f"  │  Traditional visits : {fmt(r['traditional']):>8}  ({Na} sequential BFS)  │")
    print(f"  │  MAFS visits (gross): {fmt(r['mafs']):>8}  ({r['fusion_events']} fusion events)   │")
    print(f"  │  MAFS visits (net)  : {fmt(r['mafs_net']):>8}  (gross + fusion cost)  │")
    print(f"  ├─────────────────────────────────────────────────┤")
    print(f"  │  Gross speedup : {r['speedup']:>5.1f}%  {bar(r['speedup'], 22)}  │")
    print(f"  │  Net speedup   : {r['speedup_net']:>5.1f}%  {bar(r['speedup_net'], 22)}  │")
    print(f"  └─────────────────────────────────────────────────┘")
    print(f"\n  Completed in {elapsed:.2f}s")

    all_results.append({
        "sweep": "single", "param": f"V={V},Na={Na},epn={epn}",
        "traditional": r["traditional"], "mafs": r["mafs"],
        "speedup_pct": r["speedup"], "speedup_net_pct": r["speedup_net"],
        "theoretical_pct": ""
    })

    if mode in ("na", "all"):
        section("Running · Sweep by Na (Agents)  [V=100 fixed]")
        na_max = ask_int("Maximum Na to sweep up to", 24, 4, 40)
        na_step = ask_int("Step size", 2, 1, 8)
        runs_sweep = ask_int("Trials per sweep point", 6, 3, 20)
        print()

        sweep_na = []
        print(f"  {'Na':>4}  {'Trad':>7}  {'MAFS':>7}  {'Gross%':>7}  {'Net%':>7}  {'Theory%':>8}  Bar")
        divider()

        for na in range(2, na_max + 1, na_step):
            r2 = run_trial(100, na, epn, runs=runs_sweep)
            theory = round(max(0, (1 - 2 / na) * 100), 1)
            sweep_na.append({**r2, "Na": na, "theoretical": theory})
            print(f"  {na:>4}  {fmt(r2['traditional']):>7}  {fmt(r2['mafs']):>7}  "
                  f"{r2['speedup']:>6.1f}%  {r2['speedup_net']:>6.1f}%  {theory:>7.1f}%  "
                  f"{bar(r2['speedup'], 20)}")
            all_results.append({
                "sweep": "Na_sweep", "param": na,
                "traditional": r2["traditional"], "mafs": r2["mafs"],
                "speedup_pct": r2["speedup"], "speedup_net_pct": r2["speedup_net"],
                "theoretical_pct": theory
            })

        print("\n  Key thresholds:")
        for pct in [20, 40, 60]:
            hit = next((d for d in sweep_na if d["speedup"] >= pct), None)
            if hit:
                print(f"    >{pct}% gross speedup first reached at Na = {hit['Na']}")
            else:
                print(f"    >{pct}% gross speedup not reached in this range")

    if mode in ("v", "all"):
        section("Running · Sweep by V (Graph Size)  [Na fixed]")
        v_min  = ask_int("Minimum V", 50,  20, 200)
        v_max  = ask_int("Maximum V", 300, 60, 600)
        v_step = ask_int("Step size", 20,   5,  50)
        runs_sweep_v = ask_int("Trials per sweep point", 6, 3, 20)
        print()

        sweep_v = []
        print(f"  {'V':>5}  {'Trad':>8}  {'MAFS':>8}  {'Speedup%':>9}  Bar")
        divider()

        for v in range(v_min, v_max + 1, v_step):
            r3 = run_trial(v, Na, epn, runs=runs_sweep_v)
            sweep_v.append({**r3, "V": v})
            print(f"  {v:>5}  {fmt(r3['traditional']):>8}  {fmt(r3['mafs']):>8}  "
                  f"{r3['speedup']:>8.1f}%  {bar(r3['speedup'], 22)}")
            all_results.append({
                "sweep": "V_sweep", "param": v,
                "traditional": r3["traditional"], "mafs": r3["mafs"],
                "speedup_pct": r3["speedup"], "speedup_net_pct": r3["speedup_net"],
                "theoretical_pct": ""
            })

        if sweep_v:
            speeds = [d["speedup"] for d in sweep_v]
            min_s = min(speeds); max_s = max(speeds)
            min_v_val = sweep_v[speeds.index(min_s)]["V"]
            max_v_val = sweep_v[speeds.index(max_s)]["V"]
            print(f"\n  Range: min {min_s}% at V={min_v_val}  →  max {max_s}% at V={max_v_val}")

    section("Saving Results")
    save = ask_yes_no("Save results to CSV?", default=True)
    if save:
        filename = "mafs_results_interactive.csv"
        with open(filename, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "sweep", "param", "traditional", "mafs",
                "speedup_pct", "speedup_net_pct", "theoretical_pct"
            ])
            w.writeheader()
            w.writerows(all_results)
        print(f"\n  Saved → {filename}  (open in Excel or any spreadsheet app)")
    else:
        print("  Skipped.")

    print(f"\n{'═' * 62}")
    print("  All done! Re-run the script any time to try new parameters.")
    print(f"{'═' * 62}\n")


if __name__ == "__main__":
    main()