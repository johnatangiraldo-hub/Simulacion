"""
hmm.py - Implementación propia (NumPy) de un Modelo Oculto de Markov discreto.

Notación (Rabiner, 1989):  lambda = (A, B, pi)
  A[i, j] = P(q_{t+1}=j | q_t=i)      matriz de transición (filas suman 1)
  B[i, k] = P(o_t=k | q_t=i)          matriz de emisión    (filas suman 1)
  pi[i]   = P(q_1=i)                  distribución inicial

Incluye: muestreo, Forward/Backward con escalado, Viterbi en log-espacio y
Baum-Welch (EM) con varias secuencias y *máscaras de estados permitidos*
(permiten EM con etiquetas parciales: ver validacion_real.py).
"""
from __future__ import annotations
import numpy as np


class HMM:
    def __init__(self, A, B, pi, estados=None, simbolos=None):
        self.A = np.asarray(A, dtype=float)
        self.B = np.asarray(B, dtype=float)
        self.pi = np.asarray(pi, dtype=float)
        self.N, self.M = self.B.shape
        self.estados = list(estados) if estados is not None else [f"S{i}" for i in range(self.N)]
        self.simbolos = list(simbolos) if simbolos is not None else [f"v{k}" for k in range(self.M)]
        self.validar()

    # ------------------------------------------------------------------
    def validar(self, tol=1e-8):
        assert self.A.shape == (self.N, self.N), "A debe ser N x N"
        assert self.pi.shape == (self.N,), "pi debe tener N elementos"
        for nombre, P in (("A", self.A), ("B", self.B)):
            assert np.all(P >= -tol), f"{nombre} tiene probabilidades negativas"
            assert np.allclose(P.sum(axis=1), 1.0, atol=1e-6), f"las filas de {nombre} deben sumar 1"
        assert np.all(self.pi >= -tol) and abs(self.pi.sum() - 1) < 1e-6, "pi debe sumar 1"

    def copia(self):
        return HMM(self.A.copy(), self.B.copy(), self.pi.copy(), self.estados, self.simbolos)

    # ------------------------------------------------------------------
    def muestrear(self, T, rng):
        """Simula (q_1..q_T, o_1..o_T) con el generador `rng` (np.random.Generator)."""
        q = np.empty(T, dtype=int)
        o = np.empty(T, dtype=int)
        q[0] = rng.choice(self.N, p=self.pi)
        o[0] = rng.choice(self.M, p=self.B[q[0]])
        for t in range(1, T):
            q[t] = rng.choice(self.N, p=self.A[q[t - 1]])
            o[t] = rng.choice(self.M, p=self.B[q[t]])
        return q, o

    # ------------------------------------------------------------------
    def forward(self, obs, mask=None):
        """Forward escalado. Devuelve (alpha_hat [T,N], c [T], loglik).
        alpha_hat[t] = P(q_t | o_1..o_t)  (distribución de filtrado)."""
        T = len(obs)
        a = np.zeros((T, self.N))
        c = np.zeros(T)
        e = self.B[:, obs].T                       # (T, N) emisiones
        if mask is not None:
            e = e * mask
        v = self.pi * e[0]
        c[0] = v.sum()
        a[0] = v / c[0]
        for t in range(1, T):
            v = (a[t - 1] @ self.A) * e[t]
            c[t] = v.sum()
            a[t] = v / c[t]
        return a, c, float(np.log(c).sum())

    def backward(self, obs, c, mask=None):
        T = len(obs)
        b = np.zeros((T, self.N))
        e = self.B[:, obs].T
        if mask is not None:
            e = e * mask
        b[-1] = 1.0
        for t in range(T - 2, -1, -1):
            b[t] = (self.A @ (e[t + 1] * b[t + 1])) / c[t + 1]
        return b

    def loglik(self, obs, mask=None):
        return self.forward(obs, mask)[2]

    def posterior(self, obs, mask=None):
        """Suavizado gamma[t,i] = P(q_t=i | o_1..o_T)."""
        a, c, _ = self.forward(obs, mask)
        b = self.backward(obs, c, mask)
        g = a * b
        return g / g.sum(axis=1, keepdims=True)

    # ------------------------------------------------------------------
    def viterbi(self, obs):
        """Secuencia de estados más probable (log-espacio)."""
        T = len(obs)
        with np.errstate(divide="ignore"):
            lA, lB, lpi = np.log(self.A), np.log(self.B), np.log(self.pi)
        d = np.zeros((T, self.N))
        psi = np.zeros((T, self.N), dtype=int)
        d[0] = lpi + lB[:, obs[0]]
        for t in range(1, T):
            s = d[t - 1][:, None] + lA
            psi[t] = s.argmax(axis=0)
            d[t] = s.max(axis=0) + lB[:, obs[t]]
        path = np.zeros(T, dtype=int)
        path[-1] = d[-1].argmax()
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]
        return path, float(d[-1].max())

    # ------------------------------------------------------------------
    def baum_welch(self, secuencias, n_iter=100, tol=1e-4, mascaras=None, suavizado=1e-3):
        """EM (Baum-Welch) con varias secuencias. Devuelve (HMM ajustado, historia de loglik).
        mascaras: lista opcional de arreglos (T,N) con 1 = estado permitido (EM con etiquetas parciales).
        suavizado: pseudo-conteo de Dirichlet para evitar probabilidades exactamente 0."""
        m = self.copia()
        hist = []
        prev = -np.inf
        for it in range(n_iter):
            nA = np.zeros((m.N, m.N)); nB = np.zeros((m.N, m.M)); npi = np.zeros(m.N)
            ll = 0.0
            for s, obs in enumerate(secuencias):
                mk = None if mascaras is None else mascaras[s]
                a, c, l = m.forward(obs, mk)
                b = m.backward(obs, c, mk)
                ll += l
                g = a * b
                g /= g.sum(axis=1, keepdims=True)
                e = m.B[:, obs].T
                if mk is not None:
                    e = e * mk
                o = np.asarray(obs)
                # xi acumulado (vectorizado): sum_t a_t(i) A_ij e_{t+1}(j) b_{t+1}(j) / c_{t+1}
                w = (e[1:] * b[1:]) / c[1:, None]
                nA += m.A * (a[:-1].T @ w)
                npi += g[0]
                onehot = np.zeros((len(o), m.M)); onehot[np.arange(len(o)), o] = 1.0
                nB += g.T @ onehot
            hist.append(ll)
            m.A = (nA + suavizado) / (nA + suavizado).sum(axis=1, keepdims=True)
            m.B = (nB + suavizado) / (nB + suavizado).sum(axis=1, keepdims=True)
            m.pi = (npi + suavizado) / (npi + suavizado).sum()
            if abs(ll - prev) < tol * max(1.0, abs(ll)):
                break
            prev = ll
        return m, hist
