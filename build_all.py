"""一次生成全部复核网页 + 总目录：python build_all.py
每页的数据目录见 PAGE_DATA；只生成数据目录存在的页。总目录 index.html 显示各页列数、疑点数，
从复核服务读取已看/已改进度（需从 http://127.0.0.1:8765/index.html 打开）。"""
import json, os, subprocess, sys
import v5tools as T

PAGE_DATA = {1: 'v5', **{p: f'v6p{p:02d}' for p in range(2, 13)}}
pages = [p for p, d in PAGE_DATA.items() if os.path.exists(os.path.join(d, 'columns.json'))]
env = dict(os.environ, YZ_PAGES=','.join(map(str, pages)))
info = []
for p in pages:
    env['YZ_DATA'] = PAGE_DATA[p]
    r = subprocess.run([sys.executable, 'build_editor.py', str(p)], env=env, capture_output=True, text=True, encoding='utf-8')
    if r.returncode: print(r.stderr); sys.exit(1)
    print(r.stdout.strip())
    T.D = PAGE_DATA[p]
    cols = T.columns(); ncell = nflag = 0; first = last = ''
    labs = []
    for m in cols:
        d = json.load(open(f"{T.D}/{m['key']}.json", encoding='utf-8'))
        cs = sorted(d['cells'], key=lambda c: c['y'])
        ncell += len(cs); nflag += sum(1 for c in cs if [q for q in c.get('qa', []) if q != '释文推定'])
        labs += [c['label'] for c in cs]
    info.append(dict(page=p, cols=len(cols), cells=ncell, flags=nflag, head=''.join(labs[:8]), tail=''.join(labs[-8:])))

rows = ''.join(f"""<tr data-p="{i['page']}"><td><a href="editor_p{i['page']:02d}.html">第 {i['page']} 页</a></td><td>{i['cols']}</td><td>{i['cells']}</td>
<td>{i['flags']}</td><td class="seen">–</td><td class="ed">–</td><td class="t">–</td><td class="txt">{i['head']}……{i['tail']}</td></tr>""" for i in info)
html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>云篆度人妙经 · 复核总目录</title>
<style>body{{font-family:"LXGW WenKai","Microsoft YaHei",sans-serif;background:#f6f3ec;color:#222;margin:20px 28px}}
h1{{font-size:20px}} table{{border-collapse:collapse;background:#fff}} td,th{{border:1px solid #ddd5c4;padding:5px 10px;font-size:14px}}
th{{background:#efe8d8}} a{{color:#1a4fb0}} .done td{{background:#e3f4e8}} .txt{{color:#666;font-size:13px}} .hint{{color:#555;font-size:14px;line-height:1.8}}
#st{{font-size:13px;margin:6px 0}}</style></head><body>
<h1>云篆度人妙经 · 复核总目录（共 {len(info)} 页，{sum(i['cells'] for i in info)} 字）</h1>
<div class="hint">点页码进入该页；每页顶部有翻页条（Alt+← / Alt+→ 也能翻页）。修改<b>自动保存</b>，审完运行 import_all.py 导入。<a href="font/variants.html">默认字形与异体选择</a><br>
“已看”= 在大图里打开过的列；看完一页、已看列数等于总列数时整行变绿。疑点数 = 程序标了 ⚠ 的字。</div>
<div id="st"></div>
<table><tr><th>页</th><th>列</th><th>字</th><th>疑点</th><th>已看列</th><th>已改列 / 步</th><th>最后保存</th><th>首尾释文</th></tr>{rows}</table>
<script>
async function upd(){{try{{const r=await fetch('/status?'+Date.now());const s=await r.json();
 document.querySelectorAll('tr[data-p]').forEach(tr=>{{const p=tr.dataset.p,x=s[p],cols=+tr.children[1].textContent;
  if(!x)return;tr.querySelector('.seen').textContent=x.seen+' / '+cols;tr.querySelector('.ed').textContent=x.cols+' 列 / '+x.ops+' 步';tr.querySelector('.t').textContent=x.mtime;
  tr.classList.toggle('done',x.seen>=cols)}});document.getElementById('st').textContent='进度已从复核服务读取 '+new Date().toLocaleTimeString()}}
 catch(e){{document.getElementById('st').innerHTML='<b style="color:#b42020">读不到复核服务</b>：请从 http://127.0.0.1:8765/index.html 打开'}}}}
upd();setInterval(upd,15000);
</script></body></html>"""
open('index.html', 'w', encoding='utf-8').write(html)
print('index.html', len(info), 'pages')
