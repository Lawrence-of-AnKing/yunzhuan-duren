"""仅本机使用的校对服务。只开放页面、字形及指定修订文件。"""
import argparse, hashlib, json, os, re, shutil, threading, time
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
EDITS = ROOT / 'edits'
LOCK = threading.Lock()
MAX_BODY = 16 * 1024 * 1024

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save_json(path, data):
    if path.exists():
        shutil.copy2(path, str(path) + '.bak')
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)

class H(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "frame-ancestors 'none'")
        super().end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def trusted(self):
        port = self.server.server_port
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        return host in allowed and (not origin or origin == f'http://{host}')

    def static_allowed(self):
        path = unquote(urlsplit(self.path).path).lstrip('/') or 'font/variants.html'
        allowed = re.fullmatch(
            r'(?:index\.html|editor_p(?:0[1-9]|1[0-2])\.html|font/variants\.html|'
            r'glyphs/p\d\d/p\d\dr\d+c\d+g\d+\.png|'
            r'edits/yunzhuan_p(?:0[1-9]|1[0-2])_edits\.json|'
            r'dist/YunZhuanDuRen-Unmerged\.ttf)', path)
        if not allowed:
            return False
        target = (ROOT / path).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            return False
        self.path = '/' + path
        return True

    def do_GET(self):
        if not self.trusted():
            return self._json(403, {'ok': False, 'error': '只接受本机同源请求'})
        path = urlsplit(self.path).path
        try:
            if path == '/ping':
                return self._json(200, {'ok': True})
            if path == '/fontchoices':
                with LOCK:
                    data = read_json(EDITS / 'font_choices.json') if (EDITS / 'font_choices.json').exists() else {}
                return self._json(200, data)
            if path == '/status':
                with LOCK:
                    out = {}
                    for fn in EDITS.glob('yunzhuan_p??_edits.json'):
                        d = read_json(fn)
                        out[str(d['page'])] = dict(build=d['build'], seen=len(d.get('seen', {})),
                            cols=len(d['columns']), ops=sum(len(v) for v in d.get('ops', {}).values()),
                            mtime=time.strftime('%m-%d %H:%M', time.localtime(fn.stat().st_mtime)))
                return self._json(200, out)
            if self.static_allowed():
                return super().do_GET()
            return self._json(404, {'ok': False, 'error': '文件未开放或尚未生成'})
        except ConnectionError:
            return
        except (ValueError, OSError) as e:
            return self._json(500, {'ok': False, 'error': str(e)})

    def do_HEAD(self):
        if not self.trusted() or not self.static_allowed():
            self.send_response(404); self.end_headers(); return
        super().do_HEAD()

    def do_POST(self):
        if not self.trusted():
            return self._json(403, {'ok': False, 'error': '只接受本机同源请求'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                return self._json(413, {'ok': False, 'error': '请求大小须在 1 字节至 16 MiB 内'})
            if self.headers.get_content_type() != 'application/json':
                return self._json(415, {'ok': False, 'error': '须使用 application/json'})
            self.connection.settimeout(10)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('修订必须是 JSON 对象')
            path = urlsplit(self.path).path
            with LOCK:
                if path == '/savefont':
                    raw = (ROOT / 'font/variants.json').read_bytes()
                    build = hashlib.md5(raw).hexdigest()[:10]
                    original = json.loads(raw)['chars']
                    choices = data.get('choices')
                    if not isinstance(choices, dict):
                        raise ValueError('choices 必须是对象')
                    for ch, value in choices.items():
                        expected = sorted(m for g in original[ch]['clusters'] for m in g['members'])
                        members = sorted(m for g in value['clusters'] for m in g['members'])
                        if members != expected or value['default'] not in [g['rep'] for g in value['clusters']] or not all(g['rep'] in g['members'] for g in value['clusters']):
                            raise ValueError('选择只能重组字形或更换默认，不能增删字形')
                    target = EDITS / 'font_choices.json'
                else:
                    match = re.fullmatch(r'/save/(\d{1,2})', path)
                    if not match or not 1 <= int(match[1]) <= 12:
                        return self._json(404, {'ok': False, 'error': '路径不对'})
                    pg = int(match[1])
                    if data.get('page') != pg or not isinstance(data.get('columns'), dict):
                        raise ValueError('页码或 columns 无效')
                    html = (ROOT / f'editor_p{pg:02d}.html').read_text(encoding='utf-8')
                    build = re.search(r"const BUILD='(\d+)'", html)[1]
                    for key in data['columns']:
                        if not re.fullmatch(fr'p{pg:02d}r\d+c\d+', key):
                            raise ValueError('列键不属于当前页')
                    target = EDITS / f'yunzhuan_p{pg:02d}_edits.json'
                previous = read_json(target) if target.exists() else {}
                if data.get('build') != build or (previous.get('build') and previous['build'] != build):
                    return self._json(409, {'ok': False, 'error': '生成编号不符，禁止覆盖；请先导入或归档旧修订'})
                save_json(target, data)
            return self._json(200, {'ok': True})
        except (ValueError, KeyError, TypeError, OSError) as e:
            return self._json(400, {'ok': False, 'error': str(e)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    EDITS.mkdir(exist_ok=True)
    with ThreadingHTTPServer(('127.0.0.1', args.port), H) as server:
        print(f'校对服务：http://127.0.0.1:{server.server_port}/font/variants.html', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
