# Exact ferromagnetic min-cut verification

This model permits an exact s–t min-cut only when every tie is symmetric and
ferromagnetic: `J_ij = J_ji >= 0`. `IsingModel` rejects negative/frustrated,
asymmetric, or self ties before graph construction.

For `h_i=A-r_i` and

`E(s) = -Σ_(i,j) J_ij s_i s_j - Σ_i h_i s_i`,

the source side represents **digital** nodes (`s_i=+1`, computational bit
`0`). Build the directed graph as follows:

- For every undirected tie, add `i→j` and `j→i`, each capacity `2J_ij`.
- Add `source→i` capacity `2 max(h_i, 0)`.
- Add `i→sink` capacity `2 max(-h_i, 0)`.

For every assignment, not merely an optimum,

`E(s) = cut(s) - Σ_edges J_ij - Σ_i |h_i|`.

The source-reachable residual set is the most-paper optimal state (paper wins
an exact tie); the complement of the nodes that can reach the sink is the
most-digital optimal state. Their difference identifies legitimate exact
degeneracy.

## Worked regression: J12=4, h=(3,-2)

The constant is `-4 - (3+2) = -9`.

| s1,s2 | E(s) | cut | cut - 9 |
|---|---:|---:|---:|
| +1,+1 | -5 | 4 | -5 |
| +1,-1 | -1 | 8 | -1 |
| -1,+1 | 9 | 18 | 9 |
| -1,-1 | -3 | 6 | -3 |

Thus the exact solution is `(+1,+1)` with energy `-5`, cut value `4`. This
example is encoded in `tests/test_exact.py`.

## Test coverage

`pytest -q` checks the worked table, all fields signs including zero fields,
disconnected systems, engineered degeneracy, fixed-seed random ferromagnetic
systems against exhaustive enumeration, and min-cut extremal states against
the enumerated minimum set.
