"""一次导入全部页的自动保存修订：python import_all.py [--dry]
对 edits/yunzhuan_pNN_edits.json 逐页：核对生成编号与当前网页一致 → 备份数据目录到 _preimport/<目录>_<时间> →
导入 → 用 diff_owner 思路按笔画汇总改动 → 重新导出该页单字 PNG 到 glyphs/pNN。"""
import json, os, re, shutil, subprocess, sys, time
PAGE_DATA = {1: 'v5', **{p: f'v6p{p:02d}' for p in range(2, 13)}}
dry = '--dry' in sys.argv
stamp = time.strftime('%Y%m%d_%H%M%S') + '_' + str(time.time_ns())
py = sys.executable
for fn in sorted(os.listdir('edits')):
    m = re.fullmatch(r'yunzhuan_p(\d\d)_edits\.json', fn)
    if not m: continue
    pg = int(m.group(1)); D = PAGE_DATA[pg]; path = os.path.join('edits', fn)
    e = json.load(open(path, encoding='utf-8'))
    html = open(f'editor_p{pg:02d}.html', encoding='utf-8').read()
    cur = re.search(r"const BUILD='(\d+)'", html).group(1)
    nops = sum(len(c['ops']) for c in e['columns'].values())
    print(f'== 第 {pg} 页：改动 {len(e["columns"])} 列 {nops} 步，已看 {len(e.get("seen", {}))} 列', end='')
    if e.get('build') != cur: print(f'  ✗ 生成编号不符（修订 {e.get("build")}，网页 {cur}），跳过'); continue
    if not e['columns']: print('  无改动'); continue
    if dry: print('  （试运行，不导入）'); continue
    bak = f'_preimport/{D}_{stamp}'
    shutil.copytree(D, bak)
    env = dict(os.environ, YZ_DATA=D)
    r = subprocess.run([py, 'import_edits.py', path], env=env, capture_output=True, text=True, encoding='utf-8')
    if r.returncode: print('\n  导入失败：', r.stderr[-800:]); shutil.rmtree(D); shutil.copytree(bak, D); continue
    print(f'  已导入（备份 {bak}）')
    print(subprocess.run([py, 'diff_owner.py', bak, D], capture_output=True, text=True, encoding='utf-8').stdout, end='')
    result = subprocess.run([py, 'v5tools.py', 'export', f'glyphs/p{pg:02d}'], env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('PNG 导出失败；数据备份仍保留：' + bak + '\n' + result.stderr)
    print('  PNG 已更新；font/outlines.json 不会自动改变，修改轮廓须单独同步，见 docs/校对.md')
