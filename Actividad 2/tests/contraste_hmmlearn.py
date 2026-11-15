"""Contrasta la implementación propia (src/hmm.py) con hmmlearn: log-verosimilitud, Viterbi y posteriores."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import numpy as np
from hmm import HMM
from hmmlearn.hmm import CategoricalHMM

A = [[.9, .08, .02], [.2, .7, .1], [.3, .4, .3]]; B = [[.9, .1], [.5, .5], [.1, .9]]; pi = [.7, .2, .1]
h = HMM(A, B, pi); q, o = h.muestrear(200, np.random.default_rng(0))
r = CategoricalHMM(3); r.startprob_ = np.array(pi); r.transmat_ = np.array(A); r.emissionprob_ = np.array(B)
X = o.reshape(-1, 1)
assert abs(h.loglik(o) - r.score(X)) < 1e-8, "log-verosimilitud difiere"
assert (h.viterbi(o)[0] == r.decode(X)[1]).all(), "Viterbi difiere"
assert np.abs(h.posterior(o) - r.predict_proba(X)).max() < 1e-8, "posteriores difieren"
print("OK: la implementación propia coincide con hmmlearn")
