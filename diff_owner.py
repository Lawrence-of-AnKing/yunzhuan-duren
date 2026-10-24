"""按像素比较两版归属，按“第N字 云/楷 → 第M字 云/楷”汇总：python diff_owner.py <旧目录> <新目录> [页PNG]"""
import sys, json, numpy as np, cv2
import v5tools as T
from collections import Counter
def load(D, k):
    T.D = D; ink, P, d = T.load(k); cs = sorted(d['cells'], key=lambda c: c['y'])
    n = {c['cid']: (i + 1, c['label']) for i, c in enumerate(cs)}
    own = np.full(P.shape, '', object)
    for p, o in d['owner'].items():
        m = P == p
        own[m] = f"{n[o[0]][0]}{n[o[0]][1]}{'云' if o[1]=='yz' else '楷'}" if o and o[0] in n else '无'
    return own, P
A, B = sys.argv[1], sys.argv[2]
T.D = B; keys = [m['key'] for m in T.columns()]
for k in keys:
    oa, Pa = load(A, k); ob, Pb = load(B, k)
    ch = (oa != ob) & (Pa > 0)
    if not ch.any(): continue
    cnt = Counter(zip(oa[ch], ob[ch])); ys = np.nonzero(ch)[0]
    print(k[3:], f'y{ys.min()}-{ys.max()}', '；'.join(f'{a}→{b} {n}px' for (a, b), n in cnt.most_common()))
