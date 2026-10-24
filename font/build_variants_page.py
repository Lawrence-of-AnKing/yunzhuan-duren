"""生成字体对比网页 font/variants.html（数据来自 font/variants.json）。
生成编号取 variants.json 内容的哈希：只要不重新聚类，重新生成网页不会让已存选择失效。"""
import json, hashlib, glob
raw = open('font/variants.json', 'rb').read()
V = json.loads(raw)
build = hashlib.md5(raw).hexdigest()[:10]
info = {}
for f in glob.glob('glyphs/p??/items.json'):
    for it in json.load(open(f, encoding='utf-8')):
        info[it['id']] = f"第{it['page']}页 第{it['reg']}栏 第{it['col']}列 第{it['idx']}字"
data = dict(build=build, chars=V['chars'], info=info)
html = open('font/variants_template.html', encoding='utf-8').read().replace('__DATA__', json.dumps(data, ensure_ascii=False))
open('font/variants.html', 'w', encoding='utf-8').write(html)
print('font/variants.html', build, len(html) // 1024, 'KB')
