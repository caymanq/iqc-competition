"""Independent tiny Qiskit/direct-statevector sign-convention check."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

h = np.array([0.4, -0.7])
j01, gamma, beta = 0.3, 0.37, 0.21
energies = np.array([
    -j01 - h[0] - h[1],  # |00>, s=(+1,+1)
    +j01 + h[0] - h[1],  # |01>, s=(-1,+1) little-endian q0
    +j01 - h[0] + h[1],  # |10>
    -j01 + h[0] + h[1],  # |11>
])

# Independent NumPy application of the C++ cost/mixer convention.
psi = np.ones(4, dtype=complex) / 2
psi *= np.exp(-1j * gamma * energies)
c, s = np.cos(beta), np.sin(beta)
for q in range(2):
    stride = 1 << q
    for base in range(0, 4, 2 * stride):
        for off in range(stride):
            a, b = base + off, base + off + stride
            va, vb = psi[a], psi[b]
            psi[a], psi[b] = c * va - 1j * s * vb, c * vb - 1j * s * va

qc = QuantumCircuit(2)
qc.h([0, 1])
qc.rz(-2 * gamma * h[0], 0)
qc.rz(-2 * gamma * h[1], 1)
qc.rzz(-2 * gamma * j01, 0, 1)
qc.rx(2 * beta, [0, 1])
qiskit = Statevector.from_instruction(qc).data
assert np.allclose(np.abs(psi) ** 2, np.abs(qiskit) ** 2, atol=1e-12)
assert np.isclose(np.dot(np.abs(psi) ** 2, energies), np.dot(np.abs(qiskit) ** 2, energies))
print("PASS: Qiskit/direct p=1 probabilities and expectation agree")
