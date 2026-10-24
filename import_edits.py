"""导入网页导出的修正文件：python import_edits.py <json路径>"""
import json, sys, base64
import numpy as np, cv2
from v5tools import load, save

src = json.load(open(sys.argv[1], encoding='utf-8'))
for key, e in src['columns'].items():
    ink, P_old, d = load(key)
    raw = base64.b64decode(e['P'].split(',', 1)[1])
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_UNCHANGED)
    P = img[..., 2].astype(np.int32) + 256 * img[..., 1].astype(np.int32)
    assert P.shape == P_old.shape and ((P > 0) == (P_old > 0)).all(), f'{key}: 墨迹范围不一致'
    d['owner'] = {int(k): v for k, v in e['owner'].items()}
    for c in d['cells']:
        new = e['labels'].get(str(c['cid']))
        if new and new != c['label']:
            c['label'] = new; c['status'] = 'fixed'; c['edited'] = True
    save(key, P, d)
    print(key, 'ops', len(e['ops']))
