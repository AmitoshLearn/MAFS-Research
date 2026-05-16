Analysis of your three results =>

~ The single most important pattern: Na/V ratio governs everything. Results 1 and 2 both sit at Na/V = 10% and deliver 75–84% net speedup despite one being twice the size of the other. Result 3 at Na/V = 6% collapses to just 9% net. This tells you the paper's Ffusion × Ememory composite factor is primarily driven by agent density relative to graph size, not absolute scale.

~ Result 3 is the most instructive number in the set. The gross-to-net collapse from 42.7% → 9% is not a failure — it's the paper's O(V) fusion overhead theorem playing out in real data. With only 3 agents on a 50-node graph, traditional BFS only does 74 visits total. MAFS saves 32 visits in exploration but spends most of that back on the memory union. This empirically defines the minimum viable configuration for MAFS: around Na ≥ 5–6 for small graphs, and Na/V ≥ 8% as a general rule.

~ Result 2 (V=300, Na=30, 84.5% net) is your headline number. It's also the honest one — it includes fusion overhead. 4,500 traditional BFS visits compressed to ~715 net MAFS visits at scale. This is the regime to target in your paper's empirical section.