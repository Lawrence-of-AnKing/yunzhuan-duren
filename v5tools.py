"""v5 数据工具：载入/保存列数据、着色复查图、按归属导出字形 PNG。"""
import json, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

D = os.environ.get('YZ_DATA', 'v5')     # 数据目录：第 1 页 v5，第 2 页起每页一个目录（如 v6p02）
YZC = [(40, 90, 220), (20, 150, 60), (150, 50, 190), (0, 140, 150)]
KAI = (220, 30, 30); NONE = (160, 160, 160)
PAGES = os.environ.get('YZ_PAGES_DIR', 'pages')

def load(key):
    z = np.load(f'{D}/{key}.npz'); d = json.load(open(f'{D}/{key}.json', encoding='utf-8'))
    d['owner'] = {int(k): v for k, v in d['owner'].items()}
    return z['ink'], z['P'].copy(), d

def save(key, P, d):
    z = np.load(f'{D}/{key}.npz')
    np.savez_compressed(f'{D}/{key}.npz', ink=z['ink'], P=P)
    out = dict(d); out['owner'] = {str(k): v for k, v in d['owner'].items()}
    json.dump(out, open(f'{D}/{key}.json', 'w', encoding='utf-8'), ensure_ascii=False)

def columns():
    return [m for m in json.load(open(f'{D}/columns.json', encoding='utf-8')) if not m['title']]

def color_strip(P, d):
    H, W = P.shape
    img = np.full((H, W, 3), 255, np.uint8)
    order = {c['cid']: n for n, c in enumerate(sorted(d['cells'], key=lambda c: c['y']))}
    for pid, o in d['owner'].items():
        m = P == pid
        if o is None or o[0] not in order: img[m] = NONE
        elif o[1] == 'kai': img[m] = KAI
        else: img[m] = YZC[order[o[0]] % len(YZC)]
    return img

def review_image(keys, out):
    font_path = os.environ.get('YZ_LABEL_FONT')
    if not font_path:
        raise ValueError('生成带字复查图时请用 YZ_LABEL_FONT 指定中文字体文件')
    FONT = ImageFont.truetype(font_path, 15)
    SMALL = ImageFont.truetype(font_path, 10)
    tiles = []
    for key in keys:
        ink, P, d = load(key)
        H, W = P.shape
        orig = np.where(ink[..., None] > 0, 0, 255).astype(np.uint8).repeat(3, 2)
        col = color_strip(P, d)
        lab = Image.new('RGB', (34, H), 'white'); dr = ImageDraw.Draw(lab)
        for n, c in enumerate(sorted(d['cells'], key=lambda c: c['y'])):
            dr.text((2, c['y'] - 10), c['label'], fill=(0, 0, 0) if c['status'] == 'ok' else (200, 110, 0), font=FONT)
            dr.text((20, c['y'] + 4), str(n + 1), fill=(120, 120, 120), font=SMALL)
        sep = np.full((H, 3, 3), 200, np.uint8)
        t = np.hstack([orig, sep, col, np.array(lab), np.full((H, 14, 3), 235, np.uint8)])
        head = Image.new('RGB', (t.shape[1], 16), (235, 235, 235))
        ImageDraw.Draw(head).text((3, 2), key[3:], fill=0, font=SMALL)
        tiles.append(np.vstack([np.array(head), t]))
    h = max(t.shape[0] for t in tiles)
    tiles = [np.vstack([t, np.full((h - t.shape[0], t.shape[1], 3), 255, np.uint8)]) for t in tiles]
    Image.fromarray(np.hstack(tiles[::-1])).save(out)

def export_glyphs(outdir='glyphs_v5', rim=2, soft=250):
    """导出单字透明 PNG。笔画按切分结果（灰度<128 的墨迹）归属；另外把墨迹外 rim 像素内、灰度<soft 的
    扫描灰边按“最近的笔画片”分给对应字，透明度取 255-灰度，避免字比原图细一圈、边缘发锯齿。"""
    from scipy import ndimage as ndi
    os.makedirs(outdir, exist_ok=True)
    items = []
    pages = {}
    for m in columns():
        ink, P, d = load(m['key'])
        H, W = P.shape
        pg = m['pg']
        if pg not in pages:
            pages[pg] = cv2.imread(os.path.join(PAGES, f'p{pg:02d}.png'), 0)
            if pages[pg] is None:
                raise ValueError(f'缺少原扫描页：{PAGES}/p{pg:02d}.png')
        oy, ox = d['origin']
        gray = pages[pg][oy:oy + H, ox:ox + W].astype(np.int32)
        # 每个像素归最近的笔画片（只在墨迹外 rim 像素内生效）
        dist, (iy, ix) = ndi.distance_transform_edt(P == 0, return_indices=True)
        Pn = np.where((dist <= rim) & (gray < soft), P[iy, ix], 0)
        alpha = np.clip((255 - gray) * 255 // 200, 0, 255).astype(np.uint8)   # 灰度≤55 视为全不透明
        alpha[P > 0] = 255
        # 列边缘的小碎块多半是相邻列的笔画尖，导出时忽略
        stray = set()
        for p in np.unique(P[P > 0]):
            ys, xs = np.nonzero(P == p)
            if len(ys) < 60 and (xs.min() <= 1 or xs.max() >= W - 2): stray.add(int(p))
        for n, c in enumerate(sorted(d['cells'], key=lambda c: c['y'])):
            pids = [p for p, o in d['owner'].items() if o and o[0] == c['cid'] and p not in stray]
            yz = np.isin(Pn, [p for p in pids if d['owner'][p][1] == 'yz'])
            kai = np.isin(Pn, [p for p in pids if d['owner'][p][1] == 'kai'])
            gid = f"{m['key']}g{n + 1}"
            rec = dict(id=gid, key=m['key'], page=m['pg'], reg=m['reg'], col=m['col'], idx=n + 1,
                       label=c['label'], status=c['status'], ocr=c.get('ocr', ''), conf=c.get('conf', 0),
                       edited=c.get('edited', False), has_yz=bool(yz.any()))
            for name, mask in (('', yz), ('_kai', kai)):
                ys, xs = np.nonzero(mask)
                if not len(ys): continue
                sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
                rgba = np.zeros(mask[sl].shape + (4,), np.uint8); rgba[..., 3] = np.where(mask[sl], alpha[sl], 0)
                cv2.imencode('.png', rgba)[1].tofile(f'{outdir}/{gid}{name}.png')
            items.append(rec)
    json.dump(items, open(f'{outdir}/items.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return items

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'review':
        ks = [m['key'] for m in columns()]
        per = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        os.makedirs('rv', exist_ok=True)
        for i in range(0, len(ks), per):
            review_image(ks[i:i + per], f'rv/rv_{i // per + 1:02d}.png')
            print(f'rv/rv_{i // per + 1:02d}.png', ks[i][3:], '..', ks[min(i + per, len(ks)) - 1][3:])
    elif cmd == 'export':
        it = export_glyphs(sys.argv[2] if len(sys.argv) > 2 else 'glyphs_v5'); print('glyphs', len(it))
