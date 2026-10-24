"""生成第 N 页的云篆修正网页（笔画级编辑）。用法：python build_editor.py 1
主界面：总览各列，点任意位置打开该列大图并定位到点击处。编辑只在大图里进行。
大图：底层为原页裁图（列左右各多露 M 像素，可看到相邻列），墨迹外扩一圈；上层为切分着色，幕帘对比。
网页模板在 editor_template.html。
"""
import json, base64, sys, os, hashlib
import numpy as np, cv2
from v5tools import load, columns

M = 60
pg = int(sys.argv[1]) if len(sys.argv) > 1 else 1
page_path = os.path.join(os.environ.get('YZ_PAGES_DIR', 'pages'), f'p{pg:02d}.png')
gray = cv2.imread(page_path, 0)
if gray is None:
    raise SystemExit(f'缺少原扫描页：{page_path}；本仓库不分发扫描页，请参阅 docs/校对.md')
page = gray < 128
cols = []
for m in columns():
    if m['pg'] != pg: continue
    ink, P, d = load(m['key'])
    H, W = P.shape
    img = np.zeros((H, W, 3), np.uint8)
    img[..., 2] = (P & 255).astype(np.uint8)
    img[..., 1] = (P >> 8).astype(np.uint8)
    png = base64.b64encode(cv2.imencode('.png', img)[1].tobytes()).decode()
    oy, ox = d['origin']
    ctx = np.zeros((H, W + 2 * M), np.uint8)
    xa, xb = ox - M, ox + W + M
    sa, sb = max(0, xa), min(page.shape[1], xb)
    ctx[:, sa - xa:sb - xa] = page[oy:oy + H, sa:sb]
    ctxpng = base64.b64encode(cv2.imencode('.png', ctx * 255)[1].tobytes()).decode()
    cells = [dict(cid=c['cid'], y=c['y'], label=c['label'], status=c['status'],
                  qa=[q for q in c.get('qa', []) if q != '释文推定'])
             for c in sorted(d['cells'], key=lambda c: c['y'])]
    cols.append(dict(key=m['key'], reg=m['reg'], col=m['col'], W=W, H=H, png=png, ctx=ctxpng,
                     owner={str(k): v for k, v in d['owner'].items()}, cells=cells))

small = cv2.resize((~page).astype(np.uint8) * 255, (page.shape[1] // 2, page.shape[0] // 2), interpolation=cv2.INTER_AREA)
page_b64 = base64.b64encode(cv2.imencode('.png', small)[1].tobytes()).decode()

HTML = open('editor_template.html', encoding='utf-8').read()
BUILD = str(int(hashlib.sha256(json.dumps(cols, ensure_ascii=False, sort_keys=True).encode('utf-8') + HTML.encode('utf-8')).hexdigest()[:20], 16))
PAGES = [int(x) for x in os.environ.get('YZ_PAGES', str(pg)).split(',')]
html = (HTML.replace('__BUILD__', BUILD).replace('__PAGES__', json.dumps(PAGES)).replace('__PG__', str(pg)).replace('__PAGE__', page_b64).replace('__M__', str(M))
        .replace('__DATA__', json.dumps(cols, ensure_ascii=False)))
out = f'editor_p{pg:02d}.html'
edit = f'edits/yunzhuan_p{pg:02d}_edits.json'
if os.path.exists(edit):
    saved = json.load(open(edit, encoding='utf-8'))
    if saved.get('build') != BUILD and saved.get('columns'):
        raise SystemExit(f'{edit} 仍含未清理的修订；请先导入并归档，拒绝覆盖生成页面')
open(out, 'w', encoding='utf-8').write(html)
print(out, len(html) // 1024, 'KB', 'columns', len(cols))
