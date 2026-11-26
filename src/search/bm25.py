import math
from collections import Counter, defaultdict


class BM25:
    def __init__(self, docs_tokens, k1=1.4, b=0.75):
        self.k1, self.b = k1, b
        self.N = len(docs_tokens)
        self.dl = [len(d) for d in docs_tokens]
        self.avgdl = sum(self.dl) / max(self.N, 1)
        self.inv = defaultdict(list)
        for i, d in enumerate(docs_tokens):
            for t, tf in Counter(d).items():
                self.inv[t].append((i, tf))
        self.idf = {t: math.log(1 + (self.N - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.inv.items()}

    def search(self, q_tokens, k=50):
        scores = defaultdict(float)
        for t in set(q_tokens):
            if t not in self.inv:
                continue
            for i, tf in self.inv[t]:
                denom = tf + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
                scores[i] += self.idf[t] * tf * (self.k1 + 1) / denom
        return sorted(scores.items(), key=lambda x: -x[1])[:k]
