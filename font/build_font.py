"""从定稿轮廓构建全字版：python font/build_font.py → dist/YunZhuanDuRen-Unmerged.ttf
- 默认字形：font/variants.json，再叠加用户在对比网页里的选择 edits/font_choices.json（生成编号一致才用）。
- 每个释文字（简体）映射默认字形；opencc 转出的繁体若不同且不是别的释文字，也映射同一字形。
- 其余各组代表作异体：uniXXXX.v01…，放进 aalt / salt（排版软件的“字形/替代字”面板可选）。
- calt（上下文替代，默认开启）：按前一个字形做伪随机轮换，同一个字重复出现时换不同写法。只用前 M 种写法。
- 轮廓直接来自 font/outlines.json，保留定稿的大小和位置；带竖排度量。"""
import argparse, json, os, hashlib
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from opencc import OpenCC

UPM, ADV = 1000, 1000
M = 12                         # calt 轮换用的写法数上限
FAMILY_ZH, FAMILY_EN = '云篆度人经', 'YunZhuan DuRen'
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'

def main():
    parser = argparse.ArgumentParser(description='从定稿二次曲线构建全字版字体（不重新矢量化 PNG）')
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    nomerge = True
    raw = (ROOT / 'font/variants.json').read_bytes(); V_ = json.loads(raw); build = hashlib.md5(raw).hexdigest()[:10]
    chars = V_['chars']
    orig_members = {c: sorted(m for g in v['clusters'] for m in g['members']) for c, v in chars.items()}
    ch_path = ROOT / 'edits/font_choices.json'
    if os.path.exists(ch_path):
        ch = json.load(open(ch_path, encoding='utf-8'))
        if ch.get('build') == build:
            for k, v in ch.get('choices', {}).items(): chars[k] = v
            print('已套用网页选择', len(ch.get('choices', {})), '字')
        else: raise ValueError('网页选择的生成编号不符，请先核对 font/variants.json')
    for c, v in chars.items():   # 网页改动只能重组、换代表，不能增删字形
        assert sorted(m for g in v['clusters'] for m in g['members']) == orig_members[c], c
        assert v['default'] in [g['rep'] for g in v['clusters']], c
        assert all(g['rep'] in g['members'] for g in v['clusters']), c
    # 需要矢量化的字形
    need = []
    plan = {}
    for c, v in chars.items():
        reps = [v['default']] + [g['rep'] for g in v['clusters'] if g['rep'] != v['default']]
        if nomerge:   # 不合并版：每处出现都单独成字形；先放各组代表（轮换优先轮到不同写法），再放其余组员
            reps += [m for g in v['clusters'] for m in g['members'] if m not in reps]
        plan[c] = reps; need += reps
    source = json.loads((ROOT / 'font/outlines.json').read_text(encoding='utf-8'))
    assert source['format'] == 1 and source['unitsPerEm'] == UPM
    cache = source['glyphs']
    assert len(need) == len(set(need)) == 4616 and set(need) == set(cache), '字形源与映射不一致'
    # 字形与 cmap
    cc = OpenCC('s2t')
    order = ['.notdef']; glyphs = {}; cmap = {}; alts = {}
    def make(rec):
        tp = TTGlyphPen(None)
        for command, points in rec:
            if command not in {'moveTo', 'lineTo', 'qCurveTo', 'closePath', 'endPath'}:
                raise ValueError(f'不支持的轮廓指令：{command}')
            getattr(tp, command)(*(None if p is None else tuple(p) for p in points))
        return tp.glyph()
    nd = TTGlyphPen(None)
    for pts in (((100, -120), (100, 880), (900, 880), (900, -120)), ((160, -60), (840, -60), (840, 820), (160, 820))):
        nd.moveTo(pts[0]); [nd.lineTo(p) for p in pts[1:]]; nd.closePath()     # 外框顺时针、内框逆时针
    glyphs['.notdef'] = nd.glyph()
    glyphs['space'] = TTGlyphPen(None).glyph(); order.append('space'); cmap[0x20] = cmap[0x3000] = 'space'
    labels = set(chars)
    for c in sorted(chars, key=lambda c: ord(c)):
        base = f'uni{ord(c):04X}' if ord(c) < 0x10000 else f'u{ord(c):05X}'
        names = [base] + [f'{base}.v{i:02d}' for i in range(1, len(plan[c]))]
        for n, gid in zip(names, plan[c]): glyphs[n] = make(cache[gid]); order.append(n)
        cmap[ord(c)] = base
        t = cc.convert(c)
        if len(t) == 1 and t != c and t not in labels and ord(t) not in cmap: cmap[ord(t)] = base
        if len(names) > 1: alts[base] = names[1:]
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    gt = fb.font['glyf']; bb = {}
    for n in order:
        g = gt[n]; g.recalcBounds(gt)
        bb[n] = (g.xMin, g.yMax) if g.numberOfContours else (0, 880)
    fb.setupHorizontalMetrics({n: (ADV, bb[n][0]) for n in order})   # 空格也给一字宽，竖排时对齐字格
    fb.setupHorizontalHeader(ascent=880, descent=-120)
    fb.setupVerticalMetrics({n: (UPM, 880 - bb[n][1]) for n in order})
    fb.setupVerticalHeader(ascent=500, descent=-500)
    # 两版用不同字体名，可同时安装
    zh, tw, en, ps, fname = ((FAMILY_ZH + ' 未合并', '雲篆度人經 未合併', FAMILY_EN + ' Unmerged', 'YunZhuanDuRenUnmerged-Regular', 'YunZhuanDuRen-Unmerged.ttf')
                             if nomerge else (FAMILY_ZH, '雲篆度人經', FAMILY_EN, 'YunZhuanDuRen-Regular', 'YunZhuanDuRen.ttf'))
    fb.setupNameTable({'familyName': {'en': en, 'zh': zh, 'zh-TW': tw}, 'styleName': 'Regular',
                       'uniqueFontIdentifier': f'{en} {build}', 'fullName': {'en': en, 'zh': zh, 'zh-TW': tw},
                       'psName': ps, 'version': 'Version 1.000',
                       'copyright': 'Copyright 2026 执笔之龙',
                       'licenseDescription': 'This Font Software is licensed under the SIL Open Font License, Version 1.1.',
                       'licenseInfoURL': 'https://openfontlicense.org/',
                       'description': '字形取自正统道藏本《元始无量度人上品妙经》云篆，逐字抠图矢量化。'})
    fb.setupOS2(fsType=0, sTypoAscender=880, sTypoDescender=-120, sTypoLineGap=0, usWinAscent=1000, usWinDescent=300,
                ulCodePageRange1=(1 << 18) | (1 << 20), ulUnicodeRange2=(1 << (59 - 32)))
    fb.setupPost()
    from fontTools.misc.timeTools import timestampSinceEpoch
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', '1792800000'))
    fb.setupHead(unitsPerEm=UPM, created=timestampSinceEpoch(epoch), modified=timestampSinceEpoch(epoch))
    fb.font.recalcTimestamp = False
    # GSUB
    fea = []
    if alts:
        fea.append('feature salt {'); fea += [f'  sub {b} from [{" ".join(a)}];' for b, a in alts.items()]; fea.append('} salt;')
        # calt 伪随机：前一个字形所属类（字形序号 mod M）决定换成哪种写法
        # 前一个字形所属的类 k 决定当前默认字形换成 opts[(k+h)%L]。
        # 同一字的各写法按环分类：opts[i] 归类 (i+1-h) mod L，于是连续重复同一字时依次走遍 L 种写法；
        # 其余字形（无异体的字、第 M 种以后的异体）按序号取模分类，不同字之间呈伪随机。
        cls_of = {}
        for b, a in alts.items():
            opts = [b] + a[:M - 1]; L = len(opts); h = int(hashlib.md5(b.encode()).hexdigest(), 16) % L
            for i, n in enumerate(opts): cls_of[n] = (i + 1 - h) % L
        cls = {k: [] for k in range(M)}
        for i, n in enumerate([n for n in order[1:] if n != 'space']): cls[cls_of.get(n, i % M)].append(n)
        for k in range(M): fea.append(f'@P{k} = [{" ".join(cls[k])}];')
        src = {k: [] for k in range(M)}; dst = {k: [] for k in range(M)}
        for b, a in alts.items():
            opts = [b] + a[:M - 1]; L = len(opts); h = int(hashlib.md5(b.encode()).hexdigest(), 16) % L
            for k in range(M):
                pick = opts[(k + h) % L]
                if pick != b: src[k].append(b); dst[k].append(pick)
        fea.append('feature calt {')
        for k in range(M):
            if src[k]: fea.append(f'  sub @P{k} [{" ".join(src[k])}]\' by [{" ".join(dst[k])}];')
        fea.append('} calt;')
        fea.append('feature aalt { feature salt; } aalt;')
    addOpenTypeFeaturesFromString(fb.font, '\n'.join(fea))
    args.output.mkdir(parents=True, exist_ok=True)
    fn = args.output / fname; fb.save(fn)
    print(f'{fn}  云篆字形 {len(order) - 2}（字种 {len(chars)}，异体 {sum(len(a) for a in alts.values())}），cmap {len(cmap)}')

if __name__ == '__main__':
    main()
