from flask import Flask, request, jsonify, send_from_directory, Response, send_file
from pathlib import Path
from threading import Thread, Lock
import os, json, time, uuid, shutil, subprocess, urllib.parse, urllib.request, re, socket, mimetypes, zipfile, io

app = Flask(__name__)

PROJECTS = Path('/storage/emulated/0/GodotProjects/Games/ZihadGameStudio/Projects')
HOME = Path.home() / 'Zihad3DGameStudio'
BUILD_HOME = Path.home() / '.zihad3d-build'
APK_OUT = PROJECTS.parent / 'APK-Output'
ANDROID_HOME = Path(os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT') or Path.home() / 'android-sdk')

def find_port(start=3030):
    for p in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', p)); return p
            except OSError: continue
    return start

PORT = int(os.environ.get('ZI3D_PORT') or find_port())
for p in (PROJECTS, HOME, BUILD_HOME, APK_OUT):
    p.mkdir(parents=True, exist_ok=True)

state_lock = Lock()
build_state = {'busy': False, 'status': 'idle', 'project': '', 'log': [], 'apk': '', 'error': '', 'progress': 0, 'queue': []}

# ============ Engine Templates ============
BABYLON_HTML = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>Babylon Game</title><style>html,body,#renderCanvas{width:100%;height:100%;margin:0;overflow:hidden;background:#0b1020;touch-action:none}#hud{position:fixed;left:12px;top:12px;color:#fff;font:14px sans-serif;background:#101828cc;padding:10px;border-radius:10px;z-index:3}</style><script src="https://cdn.babylonjs.com/babylon.js"></script><script src="https://cdn.babylonjs.com/loaders/babylonjs.loaders.min.js"></script></head><body><div id="hud">Babylon.js • Zihad 3D Studio</div><canvas id="renderCanvas"></canvas><script src="game.js"></script></body></html>'''

BABYLON_JS = '''const canvas=document.getElementById("renderCanvas");const engine=new BABYLON.Engine(canvas,true,{preserveDrawingBuffer:false,stencil:false,adaptToDeviceRatio:false});const scene=new BABYLON.Scene(engine);scene.clearColor=new BABYLON.Color4(.025,.04,.08,1);const camera=new BABYLON.ArcRotateCamera("camera",-Math.PI/2,Math.PI/2.5,8,BABYLON.Vector3.Zero(),scene);camera.attachControl(canvas,true);const light=new BABYLON.HemisphericLight("hemi",new BABYLON.Vector3(0,1,0),scene);const box=BABYLON.MeshBuilder.CreateBox("box",{size:1.5},scene);box.position.y=1;const mat=new BABYLON.StandardMaterial("m",scene);mat.diffuseColor=new BABYLON.Color3(.15,.65,.95);box.material=mat;scene.onBeforeRenderObservable.add(()=>{box.rotation.y+=engine.getDeltaTime()*.0005});engine.runRenderLoop(()=>scene.render());window.addEventListener("resize",()=>engine.resize());'''

THREE_HTML = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>Three.js Game</title><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#0b1020;touch-action:none}canvas{display:block}</style></head><body><script type="module" src="game.js"></script></body></html>'''

THREE_JS = '''import * as THREE from 'https://unpkg.com/three@0.180.0/build/three.module.js';const scene=new THREE.Scene();scene.background=new THREE.Color(0x0b1020);const camera=new THREE.PerspectiveCamera(65,innerWidth/innerHeight,.1,1000);camera.position.set(4,3,6);const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setPixelRatio(1);renderer.setSize(innerWidth,innerHeight);document.body.appendChild(renderer.domElement);scene.add(new THREE.HemisphereLight(0xbdd8ff,0x202030,2));const cube=new THREE.Mesh(new THREE.BoxGeometry(1.5,1.5,1.5),new THREE.MeshStandardMaterial({color:0x36a9ff}));cube.position.y=1;scene.add(cube);function animate(){requestAnimationFrame(animate);cube.rotation.y+=.006;renderer.render(scene,camera)}animate();addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});'''

# ============ Starter Templates ============
TEMPLATES = {
    'platformer': {
        'name': 'Platformer', 'icon': '🏃', 'engine': 'babylon',
        'desc': '2.5D platformer with jump, gravity',
        'files': {'index.html': BABYLON_HTML, 'game.js': BABYLON_JS}
    },
    'fps': {
        'name': 'FPS Shooter', 'icon': '🎯', 'engine': 'three',
        'desc': 'First-person controller',
        'files': {'index.html': THREE_HTML, 'game.js': THREE_JS}
    },
    'viewer': {
        'name': 'GLB Viewer', 'icon': '🧊', 'engine': 'babylon',
        'desc': 'Orbit viewer for GLB models',
        'files': {'index.html': BABYLON_HTML, 'game.js': BABYLON_JS}
    }
}

# ============ Helpers ============
def safe_path(project, rel=''):
    base = (PROJECTS / project).resolve()
    if not base.is_dir() or base.parent != PROJECTS.resolve():
        raise ValueError('Invalid project')
    rel = (rel or '').strip('/')
    p = (base / rel).resolve() if rel else base
    if p != base and base not in p.parents:
        raise ValueError('Path traversal blocked')
    return base, p

def dir_size(p):
    total = 0
    try:
        for f in p.rglob('*'):
            if f.is_file():
                try: total += f.stat().st_size
                except: pass
    except: pass
    return total

def get_project_settings(project):
    base, _ = safe_path(project)
    meta = base / 'studio.json'
    try: return json.loads(meta.read_text()) if meta.exists() else {}
    except: return {}

def save_project_settings(project, data):
    base, _ = safe_path(project)
    meta = base / 'studio.json'
    meta.write_text(json.dumps(data, indent=2))

# ============ Routes ============
@app.get('/')
def index(): return Response(INDEX_HTML, mimetype='text/html')

@app.get('/api/status')
def status():
    return jsonify(ok=True, port=PORT, projects=str(PROJECTS),
                   sdk=str(ANDROID_HOME), sdk_exists=ANDROID_HOME.exists(),
                   java=shutil.which('java'), gradle=shutil.which('gradle'))

@app.get('/api/templates')
def list_templates():
    return jsonify([{'id': k, 'name': v['name'], 'icon': v['icon'], 'engine': v['engine'], 'desc': v['desc']}
                    for k, v in TEMPLATES.items()])

@app.post('/api/templates/<tid>/apply/<project>')
def apply_template(tid, project):
    if tid not in TEMPLATES: return jsonify(error='Not found'), 404
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    for name, content in TEMPLATES[tid]['files'].items():
        (base / name).write_text(content)
    meta = get_project_settings(project)
    meta['template'] = tid
    save_project_settings(project, meta)
    return jsonify(ok=True, applied=tid)

@app.get('/api/projects')
def list_projects():
    items = []
    for p in sorted(PROJECTS.iterdir()):
        if p.is_dir() and not p.name.startswith('.'):
            data = get_project_settings(p.name)
            count = sum(1 for f in p.rglob('*') if f.is_file())
            items.append({
                'name': p.name, 'engine': data.get('engine','unknown'),
                'engines': data.get('engines', [data.get('engine','unknown')]),
                'path': str(p), 'files': count, 'size': dir_size(p),
                'created': data.get('created', 0), 'modified': int(p.stat().st_mtime),
                'app_name': data.get('app_name', p.name),
                'package': data.get('package', 'com.zihad.game'),
                'version_name': data.get('version_name', '1.0'),
                'version_code': data.get('version_code', 1),
                'orientation': data.get('orientation', 'unspecified'),
                'has_icon': (p / 'icon.png').exists()
            })
    return jsonify(items)

@app.post('/api/projects')
def create_project():
    data = request.get_json(force=True)
    name = re.sub(r'[^A-Za-z0-9_-]', '_', str(data.get('name','My3DGame')).strip())[:50] or 'My3DGame'
    engines = data.get('engines') or [data.get('engine','babylon')]
    engines = [e for e in engines if e in ('babylon','three')] or ['babylon']
    target = PROJECTS / name
    if target.exists(): return jsonify(error='Project already exists.'), 409
    for d in ('models','textures','audio','scripts','scenes'):
        (target/d).mkdir(parents=True, exist_ok=True)
    if 'babylon' in engines:
        (target/'engines/babylon').mkdir(parents=True, exist_ok=True)
        (target/'engines/babylon/index.html').write_text(BABYLON_HTML)
        (target/'engines/babylon/game.js').write_text(BABYLON_JS)
    if 'three' in engines:
        (target/'engines/three').mkdir(parents=True, exist_ok=True)
        (target/'engines/three/index.html').write_text(THREE_HTML)
        (target/'engines/three/game.js').write_text(THREE_JS)
    primary = engines[0]
    (target/'index.html').write_text((target/f'engines/{primary}/index.html').read_text())
    (target/'game.js').write_text((target/f'engines/{primary}/game.js').read_text())
    (target/'README.txt').write_text(f'Zihad 3D Game Studio\nEngines: {", ".join(engines)}\n')
    (target/'studio.json').write_text(json.dumps({
        'name': name, 'engine': primary, 'engines': engines,
        'app_name': name, 'package': 'com.zihad.game',
        'version_name': '1.0', 'version_code': 1,
        'orientation': 'unspecified',
        'created': int(time.time()), 'version': 3
    }, indent=2))
    return jsonify(ok=True, name=name, path=str(target))

@app.delete('/api/projects/<project>')
def delete_project(project):
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    try: shutil.rmtree(base); return jsonify(ok=True)
    except Exception as e: return jsonify(error=str(e)), 500

@app.post('/api/projects/<project>/rename')
def rename_project(project):
    data = request.get_json(force=True)
    new = re.sub(r'[^A-Za-z0-9_-]', '_', str(data.get('name','')).strip())[:50]
    if not new: return jsonify(error='Name required'), 400
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    target = PROJECTS / new
    if target.exists(): return jsonify(error='Name used'), 409
    try:
        base.rename(target)
        meta = target / 'studio.json'
        if meta.exists():
            d = json.loads(meta.read_text()); d['name'] = new
            meta.write_text(json.dumps(d, indent=2))
        return jsonify(ok=True, name=new)
    except Exception as e: return jsonify(error=str(e)), 500

@app.get('/api/projects/<project>/settings')
def get_settings(project):
    try: return jsonify(get_project_settings(project))
    except Exception as e: return jsonify(error=str(e)), 400

@app.post('/api/projects/<project>/settings')
def set_settings(project):
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    data = request.get_json(force=True) or {}
    meta = get_project_settings(project)
    for k in ('app_name','package','version_name','version_code','orientation'):
        if k in data: meta[k] = data[k]
    save_project_settings(project, meta)
    return jsonify(ok=True)

@app.post('/api/projects/<project>/icon')
def upload_icon(project):
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    f = request.files.get('icon')
    if not f: return jsonify(error='No icon'), 400
    if not f.filename.lower().endswith(('.png','.jpg','.jpeg')): return jsonify(error='Must be PNG/JPG'), 400
    (base / 'icon.png').write_bytes(f.read())
    meta = get_project_settings(project); meta['icon'] = 'icon.png'
    save_project_settings(project, meta)
    return jsonify(ok=True)

@app.get('/api/tree/<project>')
def list_dir(project):
    rel = request.args.get('path', '')
    try: base, p = safe_path(project, rel)
    except Exception as e: return jsonify(error=str(e)), 400
    if not p.is_dir(): return jsonify(error='Not a directory'), 400
    items = []
    try:
        for entry in p.iterdir():
            if entry.name.startswith('.'): continue
            st = entry.stat()
            if entry.is_dir():
                items.append({'name': entry.name, 'type': 'folder', 'size': dir_size(entry),
                    'modified': int(st.st_mtime), 'path': entry.relative_to(base).as_posix()})
            else:
                items.append({'name': entry.name, 'type': 'file', 'size': st.st_size,
                    'modified': int(st.st_mtime), 'path': entry.relative_to(base).as_posix(),
                    'ext': entry.suffix.lower().lstrip('.')})
    except Exception as e:
        return jsonify(error=str(e)), 500
    return jsonify(path=rel, items=items)

@app.get('/api/search/<project>')
def search_project(project):
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2: return jsonify(results=[])
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    results = []
    text_exts = {'.html','.js','.css','.json','.txt','.md','.tscn','.gd','.py','.xml','.svg','.glsl'}
    for f in base.rglob('*'):
        if not f.is_file() or f.stat().st_size > 2_000_000: continue
        if f.suffix.lower() not in text_exts: continue
        try:
            lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
            for i, line in enumerate(lines):
                if q.lower() in line.lower():
                    results.append({'path': f.relative_to(base).as_posix(),
                                   'line': i+1, 'text': line.strip()[:200]})
                    if len(results) >= 100: return jsonify(results=results)
        except: pass
    return jsonify(results=results)

@app.get('/api/file/<project>')
def read_file(project):
    rel = request.args.get('path','')
    try: base, p = safe_path(project, rel)
    except Exception as e: return jsonify(error=str(e)), 400
    if not p.is_file(): return jsonify(error='Not found'), 404
    if p.stat().st_size > 5_000_000: return jsonify(error='Too large'), 413
    try:
        return jsonify(path=rel, content=p.read_text(encoding='utf-8'),
                       size=p.stat().st_size, modified=int(p.stat().st_mtime))
    except UnicodeDecodeError:
        return jsonify(error='Binary file'), 415

@app.put('/api/file/<project>')
def save_file(project):
    data = request.get_json(force=True)
    rel = str(data.get('path','')).strip()
    content = str(data.get('content',''))
    if not rel: return jsonify(error='Missing path'), 400
    if len(content) > 5_000_000: return jsonify(error='Too large'), 400
    try: base, p = safe_path(project, rel)
    except Exception as e: return jsonify(error=str(e)), 400
    if p.suffix.lower() in ('.glb','.gltf','.png','.jpg','.jpeg','.webp','.mp3','.wav','.zip','.apk','.ico'):
        return jsonify(error='Binary files cannot be saved'), 400
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return jsonify(ok=True, size=p.stat().st_size)
    except Exception as e: return jsonify(error=str(e)), 500

@app.post('/api/mkdir/<project>')
def mkdir(project):
    data = request.get_json(force=True)
    rel = str(data.get('path','')).strip('/')
    if not rel: return jsonify(error='Missing path'), 400
    try: base, p = safe_path(project, rel)
    except Exception as e: return jsonify(error=str(e)), 400
    try:
        p.mkdir(parents=True, exist_ok=False); return jsonify(ok=True)
    except FileExistsError: return jsonify(error='Exists'), 409
    except Exception as e: return jsonify(error=str(e)), 500

@app.post('/api/rename/<project>')
def rename_item(project):
    data = request.get_json(force=True)
    old = str(data.get('path','')).strip()
    new = str(data.get('name','')).strip()
    if not old or not new: return jsonify(error='path+name required'), 400
    if '/' in new or '\\' in new: return jsonify(error='Invalid'), 400
    try: base, src = safe_path(project, old)
    except Exception as e: return jsonify(error=str(e)), 400
    if not src.exists(): return jsonify(error='Not found'), 404
    dest = src.parent / new
    if dest.exists(): return jsonify(error='Taken'), 409
    try:
        src.rename(dest); return jsonify(ok=True, path=dest.relative_to(base).as_posix())
    except Exception as e: return jsonify(error=str(e)), 500

@app.delete('/api/file/<project>')
def delete_item(project):
    rel = request.args.get('path','')
    if not rel: return jsonify(error='path required'), 400
    try: base, p = safe_path(project, rel)
    except Exception as e: return jsonify(error=str(e)), 400
    if p == base: return jsonify(error='Cannot delete root'), 400
    if not p.exists(): return jsonify(error='Not found'), 404
    try:
        if p.is_dir(): shutil.rmtree(p)
        else: p.unlink()
        return jsonify(ok=True)
    except Exception as e: return jsonify(error=str(e)), 500

@app.post('/api/upload/<project>')
def upload(project):
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    f = request.files.get('file')
    rel = request.form.get('path','').strip('/')
    if not f or not f.filename: return jsonify(error='Choose a file'), 400
    filename = Path(f.filename).name
    if len(filename) > 200: return jsonify(error='Name too long'), 400
    target = (rel + '/' + filename).strip('/') if rel else filename
    try:
        _, dest = safe_path(project, target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        f.save(dest)
        return jsonify(ok=True, path=dest.relative_to(base).as_posix(), size=dest.stat().st_size)
    except Exception as e: return jsonify(error=str(e)), 500

@app.post('/api/download-url/<project>')
def download_url(project):
    data = request.get_json(force=True)
    url = str(data.get('url','')).strip()
    rel = str(data.get('path','')).strip('/')
    filename = Path(str(data.get('filename') or urllib.parse.urlparse(url).path.split('/')[-1] or 'file.bin')).name
    if not url.startswith(('http://','https://')): return jsonify(error='Invalid URL'), 400
    target = (rel + '/' + filename).strip('/') if rel else filename
    try: base, dest = safe_path(project, target)
    except Exception as e: return jsonify(error=str(e)), 400
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent':'Zihad3DStudio/3.0'})
        with urllib.request.urlopen(req, timeout=60) as resp, dest.open('wb') as out:
            total = 0
            while True:
                chunk = resp.read(1024*256)
                if not chunk: break
                total += len(chunk)
                if total > 200*1024*1024: raise ValueError('>200MB')
                out.write(chunk)
        return jsonify(ok=True, path=dest.relative_to(base).as_posix(), size=dest.stat().st_size)
    except Exception as e: return jsonify(error=str(e)), 400

@app.post('/api/export-zip/<project>')
def export_zip(project):
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in base.rglob('*'):
            if f.is_file():
                z.write(f, f.relative_to(base))
    buf.seek(0)
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=f'{project}.zip')

@app.post('/api/import-zip/<project>')
def import_zip(project):
    try: base, _ = safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    f = request.files.get('file')
    if not f: return jsonify(error='No file'), 400
    try:
        with zipfile.ZipFile(io.BytesIO(f.read())) as z:
            for name in z.namelist():
                if name.startswith('/') or '..' in name: continue
                z.extract(name, base)
        return jsonify(ok=True)
    except Exception as e: return jsonify(error=str(e)), 500

@app.get('/preview/<project>/')
def preview(project):
    try: base, _ = safe_path(project)
    except Exception as e: return str(e), 400
    if not (base/'index.html').exists(): return 'index.html not found', 404
    return send_from_directory(base, 'index.html')

@app.get('/preview/<project>/<path:filename>')
def preview_file(project, filename):
    try: base, file_path = safe_path(project, filename)
    except Exception as e: return str(e), 400
    if not file_path.is_file(): return 'Not found', 404
    return send_from_directory(file_path.parent, file_path.name)

@app.get('/api/apks')
def apks():
    return jsonify([{'name': p.name, 'size': p.stat().st_size, 'path': str(p), 'modified': int(p.stat().st_mtime)}
                    for p in sorted(APK_OUT.glob('*.apk'), key=lambda x: -x.stat().st_mtime)])

@app.get('/api/download-apk/<name>')
def download_apk(name):
    p = APK_OUT / Path(name).name
    if not p.is_file(): return jsonify(error='Not found'), 404
    return send_file(p, as_attachment=True, download_name=p.name)

@app.post('/api/install-apk')
def install_apk():
    data = request.get_json(force=True)
    name = Path(str(data.get('name',''))).name
    if not name.endswith('.apk'): return jsonify(error='Invalid'), 400
    p = APK_OUT / name
    if not p.is_file(): return jsonify(error='Not found'), 404
    try:
        subprocess.Popen(['termux-open', str(p)])
        return jsonify(ok=True, message='Installer opened')
    except Exception as e:
        return jsonify(error=f'Could not open: {e}', path=str(p)), 500

# ============ Build ============
def run_build(project, jobid):
    with state_lock:
        build_state.update(busy=True, status='preparing', project=project, log=[], apk='', error='', progress=5)
    def log(s):
        with state_lock:
            build_state['log'].append(str(s)[-2000:])
            build_state['log'] = build_state['log'][-300:]
    try:
        src, _ = safe_path(project)
        if not (src/'index.html').exists(): raise RuntimeError('index.html missing')
        settings = get_project_settings(project)
        app_name = settings.get('app_name') or project
        pkg = settings.get('package') or 'com.zihad.game'
        ver_name = settings.get('version_name') or '1.0'
        try: ver_code = int(settings.get('version_code') or 1)
        except: ver_code = 1
        orientation = settings.get('orientation') or 'unspecified'

        wrapper = BUILD_HOME / 'WebGameWrapper'
        appsrc = wrapper / 'app/src/main/assets/game'
        if wrapper.exists(): shutil.rmtree(wrapper)
        appsrc.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name.startswith('.') or item.name == 'icon.png': continue
            dest = appsrc / item.name
            if item.is_dir(): shutil.copytree(item, dest)
            else: shutil.copy2(item, dest)

        icon_dir = wrapper / 'app/src/main/res/mipmap-xxxhdpi'
        icon_dir.mkdir(parents=True, exist_ok=True)
        icon_src = src / 'icon.png'
        if icon_src.exists():
            shutil.copy2(icon_src, icon_dir / 'ic_launcher.png')
            log('Icon: custom icon.png')
        else:
            icon_png = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000100000001008060000001ff3ff610000001a49444154789c63fcffff3f0305fc1f4a4a4a4c0c0c0c0c000000ffffff0300000000000000000000000000000000000000000000000049454e44ae426082')
            (icon_dir / 'ic_launcher.png').write_bytes(icon_png)

        (wrapper/'settings.gradle').write_text(
            "pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n"
            "dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\n"
            "rootProject.name='ZihadWebGame'\ninclude ':app'\n")
        (wrapper/'build.gradle').write_text("plugins { id 'com.android.application' version '8.7.3' apply false }\n")
        (wrapper/'gradle.properties').write_text(
            "org.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\nandroid.enableJetifier=true\n")
        app = wrapper/'app'
        (app/'build.gradle').write_text(
            "plugins { id 'com.android.application' }\n\n"
            "android { namespace '" + pkg + "'; compileSdk 35; "
            "defaultConfig { applicationId '" + pkg + "'; minSdk 23; targetSdk 35; "
            "versionCode " + str(ver_code) + "; versionName '" + ver_name + "' } }\n")

        manifest = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
            '<uses-permission android:name="android.permission.INTERNET"/>'
            '<uses-permission android:name="android.permission.VIBRATE"/>'
            '<application android:theme="@android:style/Theme.Material.NoActionBar" '
            'android:label="' + app_name + '" android:icon="@mipmap/ic_launcher" '
            'android:usesCleartextTraffic="true" android:hardwareAccelerated="true" android:largeHeap="true">'
            '<activity android:name=".MainActivity" '
            'android:configChanges="orientation|screenSize|keyboardHidden|screenLayout" '
            'android:screenOrientation="' + orientation + '" android:exported="true">'
            '<intent-filter><action android:name="android.intent.action.MAIN"/>'
            '<category android:name="android.intent.category.LAUNCHER"/></intent-filter>'
            '</activity></application></manifest>')
        (app/'src/main/AndroidManifest.xml').write_text(manifest)

        # ⚡ OPTIMIZED WebView with hardware acceleration
        java = '''package ''' + pkg + ''';
import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.webkit.*;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
public class MainActivity extends Activity {
  private WebView w;
  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    requestWindowFeature(Window.FEATURE_NO_TITLE);
    getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    w = new WebView(this);
    w.setLayoutParams(new ViewGroup.LayoutParams(-1,-1));
    w.setBackgroundColor(0xFF05050F);
    WebSettings s = w.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setDatabaseEnabled(true);
    s.setAllowFileAccess(true);
    s.setAllowContentAccess(true);
    s.setAllowFileAccessFromFileURLs(true);
    s.setAllowUniversalAccessFromFileURLs(true);
    s.setMediaPlaybackRequiresUserGesture(false);
    s.setLoadWithOverviewMode(true);
    s.setUseWideViewPort(true);
    s.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
    if (Build.VERSION.SDK_INT >= 21) {
      s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
    }
    w.setLayerType(WebView.LAYER_TYPE_HARDWARE, null);
    w.setWebViewClient(new WebViewClient() {
      @Override public boolean shouldOverrideUrlLoading(WebView v, String url) { v.loadUrl(url); return true; }
    });
    w.setWebChromeClient(new WebChromeClient());
    WebView.setWebContentsDebuggingEnabled(false);
    setContentView(w);
    w.loadUrl("file:///android_asset/game/index.html");
  }
  @Override public void onPause(){ super.onPause(); if(w!=null) w.onPause(); }
  @Override public void onResume(){ super.onResume(); if(w!=null) w.onResume(); }
  @Override public void onBackPressed(){ super.onBackPressed(); }
}'''
        # ✅ FIXED: Path + str bug — safe path join
        java_dir = app / 'src' / 'main' / 'java' / pkg.replace('.', '/')
        java_dir.mkdir(parents=True, exist_ok=True)
        (java_dir / 'MainActivity.java').write_text(java)

        sdk = ANDROID_HOME
        if not sdk.exists():
            for cand in [Path.home()/'android-sdk', Path(os.environ.get('PREFIX',''))/'opt/Android/sdk']:
                if cand.exists(): sdk = cand; break
        if not (sdk/'platforms/android-35').exists():
            raise RuntimeError(f'Android SDK platform 35 not found at {sdk}')
        (wrapper/'local.properties').write_text(f'sdk.dir={sdk}\n')

        aapt2 = shutil.which('aapt2')
        if aapt2:
            with (wrapper/'gradle.properties').open('a') as f:
                f.write(f'\nandroid.aapt2FromMavenOverride={aapt2}\n')

        gradle = shutil.which('gradle')
        if not gradle:
            for cand in [Path.home()/'android-sdk/gradle/bin/gradle', Path.home()/'gradle-8/bin/gradle']:
                if cand.exists(): gradle = str(cand); break
        if not gradle: raise RuntimeError('Gradle not found')

        with state_lock: build_state['progress'] = 25
        log(f'Building {app_name} v{ver_name}')
        log(f'Package: {pkg}')
        log(f'SDK: {sdk}')
        env = os.environ.copy()
        env['ANDROID_HOME'] = str(sdk); env['ANDROID_SDK_ROOT'] = str(sdk)
        proc = subprocess.Popen([gradle,'--no-daemon','assembleDebug'],
                                cwd=str(wrapper), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, env=env)
        pct = 25
        for line in proc.stdout:
            log(line.rstrip())
            if pct < 90:
                pct += 1
                with state_lock: build_state['progress'] = pct
        code = proc.wait()
        if code != 0: raise RuntimeError('Gradle build failed')
        built = app/'build/outputs/apk/debug/app-debug.apk'
        if not built.exists(): raise RuntimeError('APK not found')
        out = APK_OUT / f'{project}-debug.apk'
        shutil.copy2(built, out)
        with state_lock: build_state.update(busy=False, status='success', apk=str(out), error='', progress=100)
        log(f'APK ready: {out}')
    except Exception as e:
        log(f'ERROR: {e}')
        with state_lock: build_state.update(busy=False, status='failed', error=str(e))

@app.post('/api/build/<project>')
def build(project):
    try: safe_path(project)
    except Exception as e: return jsonify(error=str(e)), 400
    with state_lock:
        if build_state['busy']: return jsonify(error='Already running'), 409
        build_state.update(busy=True, status='queued', project=project, log=[], apk='', error='', progress=0)
    Thread(target=run_build, args=(project, str(uuid.uuid4())), daemon=True).start()
    return jsonify(ok=True, status='queued')

@app.get('/api/build-status')
def get_build_status():
    with state_lock: return jsonify(build_state)

# ============ Full Studio UI ============
INDEX_HTML = r'''<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0a0a1a">
<title>Zihad 3D Game Studio</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/lib/codemirror.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/theme/dracula.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/dialog/dialog.css">
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{color-scheme:dark;--bg:#0a0a1a;--bg2:#0d0d20;--panel:rgba(20,20,40,.85);--panel2:rgba(15,15,32,.9);--line:#252548;--line2:#353568;--text:#eaeaff;--muted:#8b8bb5;--blue:#4aa8ff;--purple:#a855f7;--gold:#ffc857;--green:#22c55e;--red:#ef4444;--radius:16px;--shadow:0 8px 32px rgba(0,0,0,.5);--grad:linear-gradient(135deg,#4aa8ff,#a855f7)}
[data-theme="light"]{color-scheme:light;--bg2:#fff;--panel:rgba(255,255,255,.9);--panel2:rgba(245,245,250,.95);--line:#e0e0ec;--line2:#c8c8dc;--text:#1a1a2e;--muted:#5f5f7a}
html,body{margin:0;padding:0;background:var(--bg2);color:var(--text);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,Arial;min-height:100vh;overflow-x:hidden;width:100%;max-width:100vw}
body::before{content:"";position:fixed;inset:0;background:radial-gradient(circle at 15% 0%,rgba(74,168,255,.15),transparent 50%),radial-gradient(circle at 100% 100%,rgba(168,85,247,.15),transparent 50%);pointer-events:none;z-index:0}
body>*{position:relative;z-index:1}
header{padding:12px 16px;background:var(--panel);backdrop-filter:blur(24px);border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;position:sticky;top:0;z-index:100}
h1{font-size:16px;margin:0;font-weight:800;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
h2{font-size:12px;margin:0 0 10px;color:var(--blue);text-transform:uppercase;letter-spacing:1.5px;font-weight:700}
main{padding:14px;max-width:1600px;margin:auto;overflow-x:hidden}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;min-width:0}
.stack{display:grid;gap:12px;min-width:0}
.btn{cursor:pointer;background:linear-gradient(180deg,rgba(30,30,60,.9),rgba(20,20,40,.9));border:1px solid var(--line2);color:var(--text);padding:12px 16px;border-radius:12px;font:inherit;font-weight:600;font-size:13.5px;transition:all .15s;display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:46px;white-space:nowrap}
.btn:active{transform:scale(.96)}
.btn:hover{border-color:var(--blue)}
.btn.primary{background:var(--grad);border:0}
.btn.gold{background:linear-gradient(135deg,#ffc857,#e69c1e);border:0;color:#2a1a00}
.btn.green{background:linear-gradient(135deg,#22c55e,#16a34a);border:0}
.btn.red{background:linear-gradient(135deg,#ef4444,#dc2626);border:0}
.btn.purple{background:linear-gradient(135deg,#a855f7,#7c3aed);border:0}
.btn.sm{padding:8px 12px;font-size:12px;min-height:38px;border-radius:10px}
.btn.icon{padding:10px;min-width:44px;min-height:44px;font-size:16px}
.btn.ghost{background:transparent;border:1px solid var(--line2)}
.pill{padding:5px 12px;border-radius:999px;background:var(--panel2);color:var(--muted);font-size:11.5px;border:1px solid var(--line);font-weight:600;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.pill.ok{background:rgba(34,197,94,.15);color:#6ee7a3;border-color:rgba(34,197,94,.35)}
.pill.warn{background:rgba(255,200,87,.15);color:#ffd77a;border-color:rgba(255,200,87,.35)}
.pill.err{background:rgba(239,68,68,.15);color:#fca5a5;border-color:rgba(239,68,68,.35)}
.pill.info{background:rgba(74,168,255,.15);color:#8ec8ff;border-color:rgba(74,168,255,.35)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);backdrop-filter:blur(12px);min-width:0}
input,select,textarea{font:inherit;border-radius:12px;border:1px solid var(--line2);background:var(--panel2);color:var(--text);padding:12px 14px;width:100%;min-height:46px;font-size:14px}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--blue);box-shadow:0 0 0 3px rgba(74,168,255,.2)}
#home{display:grid;gap:14px}
.homeGrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:800px){.homeGrid{grid-template-columns:1fr}}
.projectsGrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
@media(max-width:560px){.projectsGrid{grid-template-columns:1fr}}
.pcard{background:linear-gradient(145deg,rgba(30,40,80,.7),rgba(15,20,40,.9));border:1px solid var(--line2);border-radius:var(--radius);padding:16px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.pcard::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:var(--grad);opacity:.7}
.pcard:active{transform:scale(.98)}
.pcard:hover{border-color:var(--blue);transform:translateY(-2px)}
.pcard .eng{position:absolute;top:12px;right:12px;font-size:10px;font-weight:700;background:rgba(74,168,255,.2);color:#9ecfff;padding:4px 10px;border-radius:999px;border:1px solid rgba(74,168,255,.4);text-transform:uppercase}
.pcard h3{padding-right:80px;font-size:15px;font-weight:700;margin:0 0 6px;word-break:break-word}
.pcard .meta{color:var(--muted);font-size:12px;display:grid;gap:4px;margin-top:8px}
.pcard .actions{display:flex;gap:6px;margin-top:12px}
.pcard .actions .btn{flex:1}
.empty{padding:50px 20px;text-align:center;color:var(--muted);border:2px dashed var(--line2);border-radius:var(--radius);font-size:14px;background:var(--panel2)}
#workspace{display:none;grid-template-columns:1fr;gap:14px}
.workspaceHead{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center;padding:12px 14px;background:linear-gradient(135deg,rgba(30,50,90,.6),rgba(20,25,50,.8));border:1px solid var(--line2);border-radius:var(--radius);position:sticky;top:64px;z-index:50;backdrop-filter:blur(12px);min-width:0;overflow:hidden}
.workspaceHead>div{min-width:0}
.workspaceHead .wsTitle{font-weight:700;font-size:14px;display:flex;align-items:center;gap:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wsBody{display:grid;grid-template-columns:320px minmax(0,1fr);gap:14px;min-width:0}
@media(max-width:900px){.wsBody{grid-template-columns:1fr}}
.breadcrumb{display:flex;gap:4px;flex-wrap:wrap;align-items:center;padding:8px 10px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;font-size:12px;font-family:ui-monospace,monospace;margin-bottom:10px;min-height:38px;overflow-x:auto;white-space:nowrap}
.crumb{padding:4px 8px;border-radius:6px;cursor:pointer;color:var(--blue);font-weight:600;flex-shrink:0}
.crumb:hover{background:rgba(74,168,255,.15)}
.crumb.last{color:var(--text);cursor:default}
.crumbSep{color:var(--muted);flex-shrink:0}
.fileList{display:grid;gap:6px;max-height:420px;overflow-y:auto;padding-right:4px}
@media(max-width:900px){.fileList{max-height:340px}}
.fileItem{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 12px;border-radius:10px;cursor:pointer;font-size:13px;background:var(--panel2);border:1px solid transparent;min-height:52px;user-select:none}
.fileItem:active{transform:scale(.98)}
.fileItem:hover{background:rgba(74,168,255,.08);border-color:var(--line2)}
.fileItem.active{background:linear-gradient(90deg,rgba(74,168,255,.2),rgba(168,85,247,.1));border-color:var(--blue)}
.fileItem .ico{font-size:20px;flex-shrink:0;width:26px;text-align:center}
.fileItem .info{flex:1;min-width:0;overflow:hidden}
.fileItem .name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:ui-monospace,monospace;font-size:12.5px}
.fileItem .sub{font-size:10.5px;color:var(--muted);margin-top:2px;display:flex;gap:8px}
.fileItem .acts{display:flex;gap:3px;opacity:.7;flex-shrink:0}
.fileItem .acts button{background:var(--panel);border:1px solid var(--line);color:var(--muted);padding:6px 8px;border-radius:7px;cursor:pointer;font-size:12px;min-width:32px;min-height:32px}
.fileTabsBar{display:flex;gap:4px;overflow-x:auto;padding:4px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;min-height:44px}
.fileTab{display:inline-flex;align-items:center;gap:6px;padding:8px 12px;background:var(--panel);border:1px solid transparent;border-radius:8px;cursor:pointer;font-size:12px;font-family:ui-monospace,monospace;white-space:nowrap;color:var(--muted)}
.fileTab.active{background:linear-gradient(135deg,rgba(74,168,255,.2),rgba(168,85,247,.15));color:var(--text);border-color:var(--blue)}
.fileTab .close{padding:0 4px;opacity:.6;font-size:14px}
.fileTab .dot{width:6px;height:6px;border-radius:50%;background:var(--gold);display:inline-block}
.toolbar{display:flex;gap:5px;flex-wrap:wrap;padding:8px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;margin-bottom:10px}
.editorHead{display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px;min-width:0}
.editorPath{padding:8px 12px;background:var(--panel2);border:1px solid var(--line);border-radius:9px;font-family:ui-monospace,monospace;font-size:12px;color:var(--blue);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.CodeMirror{height:460px!important;border-radius:12px;border:1px solid var(--line);font-size:13px}
@media(max-width:900px){.CodeMirror{height:380px!important;font-size:12.5px}}
.tabs{display:flex;gap:4px;background:var(--panel2);padding:5px;border-radius:12px;border:1px solid var(--line);margin-bottom:14px;overflow-x:auto}
.tab{padding:10px 14px;cursor:pointer;border-radius:9px;color:var(--muted);font-size:13px;font-weight:600;white-space:nowrap;flex:1;text-align:center;min-height:42px;display:inline-flex;align-items:center;justify-content:center;gap:6px;min-width:80px}
.tab.active{background:var(--grad);color:#fff}
.tabPane{display:none}
.tabPane.active{display:block}
.preview{width:100%;height:460px;border:1px solid var(--line);border-radius:12px;background:#05080f;display:block}
@media(max-width:900px){.preview{height:360px}}
.progressBar{height:10px;background:var(--panel2);border-radius:999px;overflow:hidden;margin:10px 0;border:1px solid var(--line)}
.progressBar>div{height:100%;width:0;background:var(--grad);transition:width .4s ease}
.log{height:280px;overflow:auto;background:#03060d;border:1px solid var(--line);padding:14px;border-radius:10px;white-space:pre-wrap;font:12px/1.5 ui-monospace,monospace;color:#b8e2ff;word-break:break-all}
.apkItem{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px;background:var(--panel2);border:1px solid var(--line);border-radius:12px;flex-wrap:wrap}
.apkItem .apkInfo{flex:1;min-width:140px;overflow:hidden}
.apkItem .apkName{font-weight:700;word-break:break-all;font-size:13px}
.apkItem .apkSize{font-size:11px;color:var(--muted);margin-top:3px}
.apkItem .apkBtns{display:flex;gap:6px;flex-shrink:0}
.sortWrap{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.sortWrap select{width:auto;min-width:130px;min-height:38px;padding:8px 12px;font-size:12px;flex:1}
.tplGrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.tplCard{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:14px;cursor:pointer;text-align:center}
.tplCard:hover{border-color:var(--blue);transform:translateY(-2px)}
.tplCard .tplIcon{font-size:32px;margin-bottom:6px}
.tplCard .tplName{font-weight:700;font-size:13px}
.tplCard .tplDesc{font-size:11px;color:var(--muted);margin-top:4px}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.8);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;z-index:1000;padding:20px}
.modal.show{display:flex}
.modalBox{background:var(--panel);border:1px solid var(--line2);border-radius:18px;padding:22px;max-width:520px;width:100%;max-height:85vh;overflow-y:auto}
.modalBox h3{margin:0 0 14px;font-size:17px;font-weight:800}
.modalBox p{color:var(--muted);margin:0 0 14px;font-size:13px;line-height:1.5}
.modalBox label{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:6px}
.modalBox input,.modalBox select{margin-bottom:12px}
.modalBox .row{margin-top:16px;justify-content:flex-end}
.toast{position:fixed;bottom:20px;left:50%;transform:translate(-50%,120px);background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;padding:14px 20px;border-radius:14px;box-shadow:0 16px 48px rgba(0,0,0,.6);z-index:2000;opacity:0;transition:all .35s;max-width:calc(100vw - 40px);font-weight:700;font-size:13px}
.toast.show{transform:translate(-50%,0);opacity:1}
.toast.err{background:linear-gradient(135deg,#ef4444,#b91c1c)}
.toast.info{background:linear-gradient(135deg,#4aa8ff,#1678d3)}
.cmdPalette{position:fixed;inset:0;background:rgba(0,0,0,.8);backdrop-filter:blur(8px);display:none;z-index:1500;padding:60px 16px;align-items:flex-start;justify-content:center}
.cmdPalette.show{display:flex}
.cmdBox{background:var(--panel);border:1px solid var(--line2);border-radius:16px;width:100%;max-width:560px;overflow:hidden}
.cmdBox input{border:0;border-radius:0;border-bottom:1px solid var(--line);font-size:16px;padding:16px;min-height:56px}
.cmdList{max-height:400px;overflow-y:auto;padding:8px}
.cmdItem{padding:12px 14px;border-radius:10px;cursor:pointer;display:flex;align-items:center;gap:12px;font-size:13.5px}
.cmdItem:hover,.cmdItem.selected{background:rgba(74,168,255,.15)}
.cmdItem .ico{font-size:18px;width:24px;text-align:center}
.hide{display:none!important}
.fab{position:fixed;bottom:24px;right:18px;width:56px;height:56px;border-radius:50%;background:var(--grad);color:#fff;border:0;font-size:24px;cursor:pointer;z-index:200;box-shadow:0 8px 28px rgba(74,168,255,.5);display:flex;align-items:center;justify-content:center}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:var(--line2);border-radius:999px}
</style>
</head>
<body>

<header>
  <h1>⚡ ZIHAD 3D STUDIO</h1>
  <div class="row" style="gap:6px">
    <span id="statusPill" class="pill info">…</span>
    <button class="btn icon ghost" onclick="openCmdPalette()" title="Ctrl+K">⌘</button>
    <button class="btn icon ghost" onclick="toggleTheme()">🌓</button>
    <button class="btn icon ghost" onclick="refreshAll()">🔄</button>
  </div>
</header>

<main>

<div id="home">
  <div class="homeGrid">
    <section class="panel">
      <h2>➕ New Project</h2>
      <div class="stack">
        <input id="newName" placeholder="Project name" value="My3DGame">
        <div>
          <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;font-weight:700;text-transform:uppercase">Engine(s)</label>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <label style="display:flex;align-items:center;gap:6px;padding:10px 14px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;cursor:pointer;font-size:13px;font-weight:600">
              <input type="checkbox" id="engBabylon" checked style="width:auto;min-height:auto"> 🔵 Babylon
            </label>
            <label style="display:flex;align-items:center;gap:6px;padding:10px 14px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;cursor:pointer;font-size:13px;font-weight:600">
              <input type="checkbox" id="engThree" style="width:auto;min-height:auto"> 🟢 Three.js
            </label>
          </div>
        </div>
        <button class="btn primary" onclick="createProject()" style="width:100%">🚀 Create</button>
      </div>
    </section>
    <section class="panel">
      <h2>📦 APK Packages</h2>
      <div id="apksHome" class="stack"><small class="muted">Loading…</small></div>
    </section>
  </div>

  <section class="panel">
    <div class="row" style="justify-content:space-between;margin-bottom:12px">
      <h2 style="margin:0">🎮 Projects <span id="projCount" class="pill info" style="margin-left:6px">0</span></h2>
      <select id="projSort" onchange="refreshProjects()" style="width:auto;min-width:130px;min-height:38px;font-size:12px">
        <option value="modified-desc">🕒 Newest</option>
        <option value="modified-asc">🕒 Oldest</option>
        <option value="name-asc">🔤 A-Z</option>
        <option value="name-desc">🔤 Z-A</option>
        <option value="size-desc">📊 Largest</option>
        <option value="size-asc">📊 Smallest</option>
      </select>
    </div>
    <div id="projectsGrid" class="projectsGrid"><div class="empty">Loading…</div></div>
  </section>
</div>

<div id="workspace">
  <div class="workspaceHead">
    <div style="flex:1">
      <div class="row" style="gap:8px">
        <button class="btn sm ghost" onclick="goHome()">←</button>
        <div class="wsTitle">📁 <span id="wsTitle">Project</span></div>
        <span id="wsEngine" class="pill info">…</span>
      </div>
    </div>
    <div class="row">
      <button class="btn sm ghost" onclick="openSettings()">⚙️</button>
      <button class="btn sm primary" onclick="openPreview()">▶</button>
      <button class="btn sm gold" onclick="buildApk()">🔨 Build</button>
    </div>
  </div>

  <div class="wsBody">
    <aside class="stack">
      <section class="panel">
        <div class="row" style="justify-content:space-between;margin-bottom:10px">
          <h2 style="margin:0">📂 Files</h2>
          <div class="row" style="gap:4px">
            <button class="btn icon sm" onclick="promptNewFile()" title="New file">📄</button>
            <button class="btn icon sm" onclick="promptNewFolder()" title="New folder">📁</button>
            <button class="btn icon sm" onclick="openSearch()" title="Search">🔍</button>
            <button class="btn icon sm" onclick="navigateTo(currentDir)">🔄</button>
          </div>
        </div>
        <div class="breadcrumb" id="breadcrumb"></div>
        <input id="fileFilter" placeholder="🔍 filter…" style="margin-bottom:10px;font-size:12.5px" oninput="renderFileList()">
        <div class="sortWrap">
          <select id="fileSort" onchange="renderFileList()">
            <option value="type-name">📁 Folders first</option>
            <option value="name-asc">🔤 A-Z</option>
            <option value="size-desc">📊 Largest</option>
            <option value="size-asc">📊 Smallest</option>
            <option value="date-desc">🕒 Newest</option>
          </select>
        </div>
        <div id="fileList" class="fileList"><small class="muted">Loading…</small></div>
      </section>

      <section class="panel">
        <h2>⬆ Upload to <span id="uploadHere" style="color:var(--gold)">/</span></h2>
        <form id="uploadForm" class="stack">
          <input type="file" id="assetFile" multiple style="font-size:12px;padding:8px">
          <button class="btn sm primary" type="submit">📤 Upload</button>
        </form>
        <hr style="border:0;border-top:1px solid var(--line);margin:12px 0">
        <h2 style="font-size:11px">🌐 Download URL</h2>
        <input id="dlUrl" placeholder="https://…" style="font-size:12px;margin-bottom:8px">
        <input id="dlName" placeholder="filename" style="font-size:12px;margin-bottom:8px">
        <button class="btn sm purple" onclick="downloadUrl()" style="width:100%">⬇ Download</button>
        <div class="row" style="gap:6px;margin-top:10px">
          <button class="btn sm ghost" onclick="exportZip()" style="flex:1">📦 ZIP</button>
          <button class="btn sm ghost" onclick="importZip()" style="flex:1">📥 Import</button>
        </div>
      </section>
    </aside>

    <div class="stack">
      <section class="panel">
        <div class="tabs">
          <div class="tab active" data-tab="editor" onclick="switchTab('editor')">📝 Editor</div>
          <div class="tab" data-tab="preview" onclick="switchTab('preview')">👁 Preview</div>
          <div class="tab" data-tab="build" onclick="switchTab('build')">🔨 Build</div>
        </div>

        <div id="tab-editor" class="tabPane active">
          <div id="fileTabsBar" class="fileTabsBar hide"></div>
          <div class="editorHead">
            <div class="editorPath" id="currentPath">No file open</div>
            <span id="dirtyPill" class="pill warn hide">● Unsaved</span>
            <span id="fileSizePill" class="pill hide"></span>
          </div>
          <div class="toolbar">
            <button class="btn sm primary" onclick="saveFile()" title="Ctrl+S">💾 Save</button>
            <button class="btn sm" onclick="reloadFile()">↻</button>
            <button class="btn sm" onclick="editorAction('undo')">↶</button>
            <button class="btn sm" onclick="editorAction('redo')">↷</button>
            <button class="btn sm" onclick="editorAction('copy')">📋</button>
            <button class="btn sm" onclick="editorAction('paste')">📥</button>
            <button class="btn sm" onclick="editorAction('cut')">✂</button>
            <button class="btn sm red" onclick="editorAction('clear')">🗑</button>
            <button class="btn sm" onclick="editorAction('find')">🔍</button>
            <button class="btn sm" onclick="editorAction('replace')">🔁</button>
            <button class="btn sm" onclick="editorAction('indent')">✨</button>
            <button class="btn sm" onclick="editorAction('fontUp')">A+</button>
            <button class="btn sm" onclick="editorAction('fontDown')">A-</button>
            <button class="btn sm" onclick="editorAction('goto')">→</button>
          </div>
          <textarea id="editor"></textarea>
        </div>

        <div id="tab-preview" class="tabPane">
          <div class="row" style="justify-content:space-between;margin-bottom:10px">
            <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);font-weight:600">
              <input type="checkbox" id="autoReload" checked style="width:auto;min-height:auto"> Live reload
            </label>
            <div class="row">
              <button class="btn sm ghost" onclick="toggleFullPreview()">⛶</button>
              <button class="btn sm" onclick="openPreview()">↻</button>
            </div>
          </div>
          <iframe id="preview" class="preview" sandbox="allow-scripts allow-same-origin allow-pointer-lock allow-modals allow-forms allow-popups"></iframe>
        </div>

        <div id="tab-build" class="tabPane">
          <div class="row" style="justify-content:space-between;margin-bottom:12px">
            <span id="buildStatus" class="pill">Idle</span>
            <div class="row">
              <button class="btn sm green" onclick="buildApk()">🔨 Build Now</button>
              <button class="btn sm ghost" onclick="refreshBuild()">↻</button>
            </div>
          </div>
          <div class="progressBar"><div id="progressFill"></div></div>
          <div id="buildLog" class="log">Build logs appear here…</div>
        </div>
      </section>
    </div>
  </div>
</div>

</main>

<button class="fab" onclick="openCmdPalette()">⌘</button>

<div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
  <div class="modalBox">
    <h3 id="modalTitle">Title</h3>
    <div id="modalBody"></div>
    <div class="row" id="modalActions">
      <button class="btn ghost" onclick="closeModal()">Cancel</button>
      <button class="btn primary" id="modalOk">OK</button>
    </div>
  </div>
</div>

<div id="cmdPalette" class="cmdPalette" onclick="if(event.target===this)closeCmdPalette()">
  <div class="cmdBox">
    <input id="cmdInput" placeholder="Type a command…" autocomplete="off">
    <div id="cmdList" class="cmdList"></div>
  </div>
</div>

<div id="toast" class="toast"></div>

<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/lib/codemirror.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/mode/javascript/javascript.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/mode/xml/xml.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/mode/css/css.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/mode/htmlmixed/htmlmixed.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/edit/closebrackets.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/edit/matchbrackets.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/selection/active-line.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/search/search.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/search/searchcursor.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/dialog/dialog.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/fold/foldcode.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/fold/foldgutter.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/fold/brace-fold.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/fold/xml-fold.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/comment/comment.js"></script>
<script>
var selectedProject='',selectedFile='',currentDir='',fileItems=[],openTabs={},activeTab=null,cm=null,editorFontSize=13;
var theme = localStorage.getItem('z3d_theme') || 'dark';
function $(id){ return document.getElementById(id); }
function esc(s){ return String(s).replace(/[&<>"']/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function fmtSize(b){ if(b<1024)return b+' B'; if(b<1048576)return (b/1024).toFixed(1)+' KB'; if(b<1073741824)return (b/1048576).toFixed(2)+' MB'; return (b/1073741824).toFixed(2)+' GB'; }
function fmtTime(t){ if(!t)return '—'; var d=new Date(t*1000); var diff=(Date.now()-d)/1000; if(diff<60)return 'just now'; if(diff<3600)return Math.floor(diff/60)+'m'; if(diff<86400)return Math.floor(diff/3600)+'h'; return d.toLocaleDateString(); }
async function api(url,opts){ opts=opts||{}; var r=await fetch(url,opts); var d={}; try{d=await r.json();}catch(e){} if(!r.ok)throw Error(d.error||('HTTP '+r.status)); return d; }
function toast(msg,kind){ var t=$('toast'); t.textContent=(kind==='err'?'❌ ':kind==='info'?'ℹ️ ':'✅ ')+msg; t.className='toast show'+(kind==='err'?' err':kind==='info'?' info':''); clearTimeout(toast._t); toast._t=setTimeout(function(){t.className='toast';},2600); }
function confetti(){ for(var i=0;i<50;i++){ var c=document.createElement('div'); c.style.cssText='position:fixed;top:-10px;width:10px;height:10px;background:'+['#4aa8ff','#a855f7','#ffc857','#22c55e','#ef4444'][Math.floor(Math.random()*5)]+';left:'+Math.random()*100+'vw;pointer-events:none;z-index:9999;animation:fall linear forwards;animation-duration:'+(1.5+Math.random()*1.5)+'s'; document.body.appendChild(c); setTimeout((function(el){return function(){el.remove();};})(c),3500); } }
var style=document.createElement('style'); style.textContent='@keyframes fall{to{transform:translateY(100vh) rotate(720deg);opacity:0}}'; document.head.appendChild(style);
function applyTheme(){ document.documentElement.setAttribute('data-theme',theme); localStorage.setItem('z3d_theme',theme); if(cm)cm.setOption('theme',theme==='light'?'default':'dracula'); }
function toggleTheme(){ theme=theme==='dark'?'light':'dark'; applyTheme(); toast('Theme: '+theme,'info'); }
function showModal(opts){ var body=$('modalBody'); body.innerHTML=''; $('modalTitle').textContent=opts.title||''; if(opts.fields){ opts.fields.forEach(function(f){ var l=document.createElement('label'); l.textContent=f.label; body.appendChild(l); var inp; if(f.type==='select'){ inp=document.createElement('select'); (f.options||[]).forEach(function(o){ var op=document.createElement('option'); op.value=o.v; op.textContent=o.t; inp.appendChild(op); }); } else { inp=document.createElement('input'); inp.type=f.type||'text'; inp.placeholder=f.placeholder||''; } if(f.value!==undefined)inp.value=f.value; inp.id='mf_'+f.key; body.appendChild(inp); }); } else if(opts.html){ body.innerHTML=opts.html; } else if(opts.message){ var p=document.createElement('p'); p.textContent=opts.message; body.appendChild(p); } $('modalActions').innerHTML=''; var c=document.createElement('button'); c.className='btn ghost'; c.textContent=opts.cancelText||'Cancel'; c.onclick=closeModal; $('modalActions').appendChild(c); var ok=document.createElement('button'); ok.className='btn '+(opts.okClass||'primary'); ok.textContent=opts.okText||'OK'; ok.onclick=function(){ var vals={}; if(opts.fields){ opts.fields.forEach(function(f){ vals[f.key]=$('mf_'+f.key).value.trim(); }); } closeModal(); if(opts.onOk)opts.onOk(vals); }; $('modalActions').appendChild(ok); $('modal').classList.add('show'); }
function closeModal(){ $('modal').classList.remove('show'); }
var cmds=[];
function openCmdPalette(){ $('cmdPalette').classList.add('show'); $('cmdInput').value=''; renderCmds(''); setTimeout(function(){$('cmdInput').focus();},50); }
function closeCmdPalette(){ $('cmdPalette').classList.remove('show'); }
function buildCmds(){ cmds=[{ico:'➕',lbl:'New Project',act:function(){goHome();$('newName').focus();}},{ico:'🔄',lbl:'Refresh All',act:refreshAll},{ico:'🌓',lbl:'Toggle Theme',act:toggleTheme}]; if(selectedProject){ cmds.push({ico:'🏠',lbl:'Back to Home',act:goHome},{ico:'▶',lbl:'Preview',act:openPreview},{ico:'🔨',lbl:'Build APK',act:buildApk},{ico:'💾',lbl:'Save File',act:saveFile},{ico:'📄',lbl:'New File',act:promptNewFile},{ico:'📁',lbl:'New Folder',act:promptNewFolder},{ico:'🔍',lbl:'Search Project',act:openSearch},{ico:'⚙️',lbl:'Settings',act:openSettings},{ico:'📦',lbl:'Export ZIP',act:exportZip}); } }
function renderCmds(q){ buildCmds(); var list=cmds.filter(function(c){ return !q||c.lbl.toLowerCase().indexOf(q.toLowerCase())>=0; }); var el=$('cmdList'); el.innerHTML=''; if(!list.length){ el.innerHTML='<div style="padding:20px;text-align:center;color:var(--muted)">No commands</div>'; return; } list.forEach(function(c,i){ var d=document.createElement('div'); d.className='cmdItem'+(i===0?' selected':''); d.innerHTML='<span class="ico">'+c.ico+'</span><span>'+esc(c.lbl)+'</span>'; d.onclick=function(){ closeCmdPalette(); c.act(); }; el.appendChild(d); }); }
document.addEventListener('keydown',function(e){ if((e.ctrlKey||e.metaKey)&&e.key==='k'){ e.preventDefault(); openCmdPalette(); return; } if((e.ctrlKey||e.metaKey)&&e.key==='s'){ e.preventDefault(); saveFile(); return; } if(e.key==='Escape'){ closeModal(); closeCmdPalette(); } if($('cmdPalette').classList.contains('show')){ if(e.key==='ArrowDown'||e.key==='ArrowUp'){ e.preventDefault(); var items=document.querySelectorAll('.cmdItem'); var cur=document.querySelector('.cmdItem.selected'); var idx=Array.prototype.indexOf.call(items,cur); if(e.key==='ArrowDown')idx=Math.min(idx+1,items.length-1); else idx=Math.max(idx-1,0); items.forEach(function(x){x.classList.remove('selected');}); if(items[idx]){ items[idx].classList.add('selected'); items[idx].scrollIntoView({block:'nearest'}); } } if(e.key==='Enter'){ var sel=document.querySelector('.cmdItem.selected'); if(sel)sel.click(); } } });
async function refreshAll(){ try{ var s=await api('/api/status'); var ok=s.sdk_exists&&s.java&&s.gradle; $('statusPill').className='pill '+(ok?'ok':'warn'); $('statusPill').textContent=':'+s.port+(ok?' • Ready':' • Setup'); await refreshProjects(); await refreshApks(); await refreshBuild(); }catch(e){ $('statusPill').className='pill err'; $('statusPill').textContent='Error'; } }
async function refreshProjects(){ try{ var a=await api('/api/projects'); var parts=$('projSort').value.split('-'); var key=parts[0],dir=parts[1]; a.sort(function(x,y){ var r=key==='name'?x.name.localeCompare(y.name):key==='size'?x.size-y.size:x.modified-y.modified; return dir==='desc'?-r:r; }); $('projCount').textContent=a.length; var g=$('projectsGrid'); if(!a.length){ g.innerHTML='<div class="empty">🎮 No projects yet</div>'; return; } g.innerHTML=''; a.forEach(function(p){ var c=document.createElement('div'); c.className='pcard'; var engs=(p.engines||[p.engine]).map(function(e){ return e==='babylon'?'🔵':'🟢'; }).join(''); c.innerHTML='<span class="eng">'+esc(p.engine)+'</span><h3>'+engs+' '+esc(p.app_name||p.name)+'</h3><div class="meta"><span>📄 '+p.files+' · '+fmtSize(p.size)+'</span><span>🕒 '+fmtTime(p.modified)+'</span></div><div class="actions"><button class="btn sm primary" data-a="o">📂 Open</button><button class="btn sm ghost" data-a="r">✏️</button><button class="btn sm red" data-a="d">🗑</button></div>'; c.querySelector('[data-a="o"]').onclick=function(e){ e.stopPropagation(); openProject(p.name); }; c.querySelector('[data-a="r"]').onclick=function(e){ e.stopPropagation(); renameProject(p.name); }; c.querySelector('[data-a="d"]').onclick=function(e){ e.stopPropagation(); deleteProject(p.name); }; c.onclick=function(){ openProject(p.name); }; g.appendChild(c); }); }catch(e){} }
function renameProject(name){ showModal({title:'Rename',fields:[{key:'name',label:'New name',value:name}],onOk:async function(v){ try{ await api('/api/projects/'+encodeURIComponent(name)+'/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:v.name})}); toast('Renamed'); refreshProjects(); }catch(e){ toast(e.message,'err'); } }}); }
function deleteProject(name){ showModal({title:'Delete?',message:'Delete "'+name+'"?',okText:'Delete',okClass:'red',onOk:async function(){ try{ await api('/api/projects/'+encodeURIComponent(name),{method:'DELETE'}); toast('Deleted'); refreshProjects(); }catch(e){ toast(e.message,'err'); } }}); }
async function createProject(){ var name=$('newName').value.trim(); if(!name)return toast('Enter name','err'); var engines=[]; if($('engBabylon').checked)engines.push('babylon'); if($('engThree').checked)engines.push('three'); if(!engines.length)return toast('Select engine','err'); try{ var d=await api('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,engines:engines})}); toast('Created '+d.name); await refreshProjects(); openProject(d.name); }catch(e){ toast(e.message,'err'); } }
async function openSettings(){ if(!selectedProject)return; try{ var s=await api('/api/projects/'+encodeURIComponent(selectedProject)+'/settings'); showModal({title:'⚙️ Settings',html:'<label>App Name</label><input id="set_app" value="'+esc(s.app_name||selectedProject)+'" style="margin-bottom:10px"><label>Package ID</label><input id="set_pkg" value="'+esc(s.package||'com.zihad.game')+'" style="margin-bottom:10px"><label>Version Name</label><input id="set_vname" value="'+esc(s.version_name||'1.0')+'" style="margin-bottom:10px"><label>Version Code</label><input id="set_vcode" type="number" value="'+(s.version_code||1)+'" style="margin-bottom:10px"><label>Orientation</label><select id="set_orient" style="margin-bottom:10px">'+['unspecified','portrait','landscape','sensor'].map(function(o){return '<option value="'+o+'"'+(s.orientation===o?' selected':'')+'>'+o+'</option>';}).join('')+'</select><label>App Icon (PNG)</label><input id="set_icon" type="file" accept="image/png,image/jpeg" style="padding:8px;margin-bottom:6px"><p style="font-size:11px;color:var(--muted);margin:0">512×512 recommended</p>',okText:'Save',onOk:async function(){ try{ await api('/api/projects/'+encodeURIComponent(selectedProject)+'/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({app_name:$('set_app').value,package:$('set_pkg').value,version_name:$('set_vname').value,version_code:parseInt($('set_vcode').value)||1,orientation:$('set_orient').value})}); var fi=$('set_icon'); if(fi&&fi.files&&fi.files[0]){ var fd=new FormData(); fd.append('icon',fi.files[0]); await api('/api/projects/'+encodeURIComponent(selectedProject)+'/icon',{method:'POST',body:fd}); } toast('Saved'); refreshProjects(); }catch(e){ toast(e.message,'err'); } }}); }catch(e){} }
async function openProject(n){ selectedProject=n; selectedFile=''; currentDir=''; openTabs={}; activeTab=null; $('home').classList.add('hide'); $('workspace').style.display='grid'; try{ var list=await api('/api/projects'); var p=list.find(function(x){return x.name===n;}); if(p){ $('wsTitle').textContent=p.app_name||p.name; $('wsEngine').textContent=(p.engines||[p.engine]).join(' + '); } }catch(e){} if(!cm)initEditor(); cm.setValue('// Select a file\n'); $('currentPath').textContent='No file'; $('fileSizePill').classList.add('hide'); $('dirtyPill').classList.add('hide'); renderFileTabs(); await navigateTo(''); openPreview(); switchTab('editor'); window.scrollTo({top:0,behavior:'smooth'}); }
function goHome(){ selectedProject=''; selectedFile=''; currentDir=''; openTabs={}; activeTab=null; $('workspace').style.display='none'; $('home').classList.remove('hide'); refreshProjects(); refreshApks(); }
async function navigateTo(rel){ currentDir=rel; try{ var d=await api('/api/tree/'+encodeURIComponent(selectedProject)+'?path='+encodeURIComponent(rel)); fileItems=d.items||[]; renderBreadcrumb(rel); renderFileList(); $('uploadHere').textContent='/'+(rel||'(root)'); }catch(e){ toast(e.message,'err'); } }
function renderBreadcrumb(rel){ var bc=$('breadcrumb'); bc.innerHTML=''; var root=document.createElement('span'); root.className='crumb'+(rel?'':' last'); root.textContent='🏠 root'; root.onclick=function(){navigateTo('');}; bc.appendChild(root); if(rel){ var parts=rel.split('/'),acc=''; parts.forEach(function(p,i){ acc=acc?(acc+'/'+p):p; var sep=document.createElement('span'); sep.className='crumbSep'; sep.textContent='/'; bc.appendChild(sep); var c=document.createElement('span'); c.className='crumb'+(i===parts.length-1?' last':''); c.textContent=p; var t=acc; c.onclick=function(){navigateTo(t);}; bc.appendChild(c); }); } }
function fileIcon(f){ if(f.type==='folder')return '📁'; var e=(f.ext||'').toLowerCase(); if(e==='glb'||e==='gltf')return '🧊'; if(e==='html')return '🌐'; if(e==='js')return '📜'; if(e==='json')return '⚙️'; if(e==='png'||e==='jpg'||e==='jpeg'||e==='webp'||e==='gif')return '🖼️'; if(e==='mp3'||e==='wav')return '🎵'; if(e==='md')return '📘'; if(e==='txt')return '📄'; return '📄'; }
function renderFileList(){ var list=fileItems.slice(); var filt=($('fileFilter').value||'').toLowerCase(); if(filt)list=list.filter(function(f){return f.name.toLowerCase().indexOf(filt)>=0;}); var sk=$('fileSort').value; list.sort(function(a,b){ if(sk==='type-name'){ if(a.type!==b.type)return a.type==='folder'?-1:1; return a.name.localeCompare(b.name); } if(sk==='name-asc')return a.name.localeCompare(b.name); if(sk==='size-desc')return b.size-a.size; if(sk==='size-asc')return a.size-b.size; if(sk==='date-desc')return b.modified-a.modified; return 0; }); var el=$('fileList'); if(!list.length){ el.innerHTML='<div class="empty" style="padding:30px 10px;font-size:12px">Empty folder</div>'; return; } el.innerHTML=''; list.forEach(function(f){ var row=document.createElement('div'); row.className='fileItem'+(f.path===selectedFile?' active':''); row.innerHTML='<div class="ico">'+fileIcon(f)+'</div><div class="info"><div class="name">'+esc(f.name)+'</div><div class="sub"><span>'+fmtSize(f.size)+'</span><span>'+fmtTime(f.modified)+'</span></div></div><div class="acts"><button data-a="r">✏️</button><button data-a="d">🗑</button></div>'; row.querySelector('[data-a="r"]').onclick=function(e){ e.stopPropagation(); renameItem(f); }; row.querySelector('[data-a="d"]').onclick=function(e){ e.stopPropagation(); deleteItem(f); }; row.onclick=function(){ if(f.type==='folder')navigateTo(f.path); else pickFile(f.path); }; el.appendChild(row); }); }
function renameItem(f){ showModal({title:'Rename',fields:[{key:'name',label:'New name',value:f.name}],onOk:async function(v){ try{ await api('/api/rename/'+encodeURIComponent(selectedProject),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:f.path,name:v.name})}); toast('Renamed'); navigateTo(currentDir); }catch(e){ toast(e.message,'err'); } }}); }
function deleteItem(f){ showModal({title:'Delete?',message:'Delete "'+f.name+'"?',okText:'Delete',okClass:'red',onOk:async function(){ try{ await api('/api/file/'+encodeURIComponent(selectedProject)+'?path='+encodeURIComponent(f.path),{method:'DELETE'}); toast('Deleted'); if(selectedFile===f.path){ selectedFile=''; cm.setValue(''); } navigateTo(currentDir); }catch(e){ toast(e.message,'err'); } }}); }
function promptNewFile(){ showModal({title:'New File',fields:[{key:'path',label:'Path',placeholder:'scripts/player.js'}],onOk:async function(v){ try{ var full=currentDir?(currentDir+'/'+v.path):v.path; await api('/api/file/'+encodeURIComponent(selectedProject),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:full,content:'// '+v.path+'\n'})}); toast('Created'); navigateTo(currentDir); pickFile(full); }catch(e){ toast(e.message,'err'); } }}); }
function promptNewFolder(){ showModal({title:'New Folder',fields:[{key:'path',label:'Path',placeholder:'scripts'}],onOk:async function(v){ try{ var full=currentDir?(currentDir+'/'+v.path):v.path; await api('/api/mkdir/'+encodeURIComponent(selectedProject),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:full})}); toast('Created'); navigateTo(currentDir); }catch(e){ toast(e.message,'err'); } }}); }
function openSearch(){ if(!selectedProject)return; showModal({title:'🔍 Search',fields:[{key:'q',label:'Text',placeholder:'function…'}],okText:'Search',onOk:async function(v){ if(!v.q||v.q.length<2)return toast('Min 2 chars','err'); try{ var d=await api('/api/search/'+encodeURIComponent(selectedProject)+'?q='+encodeURIComponent(v.q)); if(!d.results||!d.results.length){ toast('No results','info'); return; } showModal({title:'🔍 '+d.results.length+' results',html:'<div style="max-height:400px;overflow-y:auto">'+d.results.map(function(r){ return '<div style="padding:8px;background:var(--panel2);border-radius:6px;margin-bottom:4px;cursor:pointer" data-p="'+esc(r.path)+'" data-l="'+r.line+'"><div style="font-size:11px;color:var(--blue)">'+esc(r.path)+':'+r.line+'</div><div style="font-size:11px;font-family:monospace">'+esc(r.text)+'</div></div>'; }).join('')+'</div>',okText:'',cancelText:'Close',onOk:function(){}}); setTimeout(function(){ document.querySelectorAll('[data-p]').forEach(function(el){ el.onclick=function(){ var p=el.getAttribute('data-p'),l=parseInt(el.getAttribute('data-l')); closeModal(); pickFile(p).then(function(){ if(cm)cm.setCursor({line:l-1,ch:0}); cm.focus(); }); }; }); },50); }catch(e){ toast(e.message,'err'); } }}); }
function renderFileTabs(){ var bar=$('fileTabsBar'); var keys=Object.keys(openTabs); if(keys.length<2){ bar.classList.add('hide'); return; } bar.classList.remove('hide'); bar.innerHTML=''; keys.forEach(function(k){ var t=openTabs[k]; var d=document.createElement('div'); d.className='fileTab'+(k===activeTab?' active':''); var nm=k.split('/').pop(); d.innerHTML='<span>'+(t.dirty?'<span class="dot"></span> ':'')+esc(nm)+'</span><span class="close">×</span>'; d.onclick=function(e){ if(e.target.classList.contains('close')){ closeTab(k); return; } pickFile(k); }; bar.appendChild(d); }); }
function closeTab(path){ if(openTabs[path]&&openTabs[path].dirty&&!confirm('Unsaved. Close?'))return; delete openTabs[path]; if(activeTab===path){ var keys=Object.keys(openTabs); if(keys.length)pickFile(keys[keys.length-1]); else { selectedFile=''; activeTab=null; cm.setValue(''); $('currentPath').textContent='No file'; } } renderFileTabs(); }
async function pickFile(p){ try{ if(/\.(glb|gltf|png|jpe?g|webp|gif|mp3|wav|apk|zip|ico)$/i.test(p)){ selectedFile=p; activeTab=p; $('currentPath').textContent=p; $('fileSizePill').classList.add('hide'); $('dirtyPill').classList.add('hide'); if(/\.(png|jpe?g|webp|gif)$/i.test(p)){ var html='<div style="width:100%;height:200px;display:flex;align-items:center;justify-content:center;background:#1a1a2e;border-radius:12px"><img src="/preview/'+encodeURIComponent(selectedProject)+'/'+encodeURIComponent(p)+'" style="max-width:100%;max-height:100%"></div>'; showModal({title:p.split('/').pop(),html:html,okText:'',cancelText:'Close',onOk:function(){}}); } else { cm.setValue('// Binary file: '+p+'\n'); } renderFileList(); renderFileTabs(); return; } var d=await api('/api/file/'+encodeURIComponent(selectedProject)+'?path='+encodeURIComponent(p)); selectedFile=p; activeTab=p; if(!openTabs[p])openTabs[p]={content:d.content,dirty:false}; else openTabs[p].content=d.content; cm.setValue(d.content); openTabs[p].dirty=false; $('currentPath').textContent=p; $('fileSizePill').textContent='📄 '+fmtSize(d.size); $('fileSizePill').classList.remove('hide'); $('dirtyPill').classList.add('hide'); var mode='htmlmixed'; if(/\.js$/i.test(p))mode='javascript'; else if(/\.json$/i.test(p))mode={name:'javascript',json:true}; else if(/\.css$/i.test(p))mode='css'; else if(/\.txt$/i.test(p))mode=null; cm.setOption('mode',mode); setTimeout(function(){cm.refresh();},50); renderFileList(); renderFileTabs(); }catch(e){ toast(e.message,'err'); } }
function initEditor(){ cm=CodeMirror.fromTextArea($('editor'),{lineNumbers:true,mode:'htmlmixed',theme:theme==='light'?'default':'dracula',autoCloseBrackets:true,matchBrackets:true,lineWrapping:true,indentUnit:2,tabSize:2,styleActiveLine:true,extraKeys:{'Ctrl-S':saveFile,'Cmd-S':saveFile,'Ctrl-F':'findPersistent','Cmd-F':'findPersistent','Ctrl-H':'replace','Ctrl-/':'toggleComment','Tab':function(c){c.replaceSelection('  ');}}}); cm.setSize('100%','460px'); cm.on('change',function(){ if(activeTab&&openTabs[activeTab])openTabs[activeTab].dirty=true; $('dirtyPill').classList.remove('hide'); renderFileTabs(); scheduleAutoSave(); }); }
var autoSaveTimer=null; function scheduleAutoSave(){ clearTimeout(autoSaveTimer); autoSaveTimer=setTimeout(function(){ if(selectedFile)saveFile(true); },3000); }
async function saveFile(silent){ if(!selectedProject||!selectedFile){ if(!silent)toast('No file','err'); return; } try{ var d=await api('/api/file/'+encodeURIComponent(selectedProject),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:selectedFile,content:cm.getValue()})}); $('dirtyPill').classList.add('hide'); $('fileSizePill').textContent='📄 '+fmtSize(d.size); $('fileSizePill').classList.remove('hide'); if(activeTab&&openTabs[activeTab])openTabs[activeTab].dirty=false; renderFileTabs(); if(!silent)toast('Saved '+selectedFile.split('/').pop()); if($('autoReload').checked&&/\.(html?|css|js)$/i.test(selectedFile))openPreview(); }catch(e){ if(!silent)toast(e.message,'err'); } }
async function reloadFile(){ if(selectedFile)await pickFile(selectedFile); }
function editorAction(a){ if(!cm)return; if(a==='undo')cm.undo(); else if(a==='redo')cm.redo(); else if(a==='clear'){ showModal({title:'Clear?',message:'Remove all text?',okText:'Clear',okClass:'red',onOk:function(){cm.setValue('');cm.focus();}}); } else if(a==='copy'){ var txt=cm.getValue(); if(navigator.clipboard)navigator.clipboard.writeText(txt).then(function(){toast('Copied','info');},function(){toast('Failed','err');}); } else if(a==='paste'){ if(navigator.clipboard&&navigator.clipboard.readText){ navigator.clipboard.readText().then(function(t){ if(t){cm.replaceSelection(t);toast('Pasted','info');} },function(){toast('Tap & hold','err');}); } } else if(a==='cut'){ var txt=cm.getSelection()||cm.getValue(); if(navigator.clipboard)navigator.clipboard.writeText(txt); if(cm.getSelection())cm.replaceSelection(''); else cm.setValue(''); toast('Cut','info'); } else if(a==='find')cm.execCommand('findPersistent'); else if(a==='replace')cm.execCommand('replace'); else if(a==='goto')cm.execCommand('jumpToLine'); else if(a==='indent'){ var lines=cm.getValue().split('\n'),depth=0; var f=lines.map(function(l){ l=l.trim(); if(!l)return ''; if(l.match(/^[}\])]/))depth=Math.max(0,depth-1); var o='  '.repeat(depth)+l; if(l.match(/[{[(]$/))depth++; return o; }).join('\n'); cm.setValue(f); toast('Formatted','info'); } else if(a==='fontUp'){ editorFontSize=Math.min(22,editorFontSize+1); applyFontSize(); } else if(a==='fontDown'){ editorFontSize=Math.max(10,editorFontSize-1); applyFontSize(); } }
function applyFontSize(){ document.querySelectorAll('.CodeMirror').forEach(function(el){ el.style.fontSize=editorFontSize+'px'; }); if(cm)setTimeout(function(){cm.refresh();},30); }
document.addEventListener('DOMContentLoaded',function(){ $('uploadForm').addEventListener('submit',async function(e){ e.preventDefault(); if(!selectedProject)return toast('Open project','err'); var files=$('assetFile').files; if(!files||!files.length)return toast('Choose file','err'); var ok=0,fail=0; for(var i=0;i<files.length;i++){ var fd=new FormData(); fd.append('file',files[i]); fd.append('path',currentDir); try{ await api('/api/upload/'+encodeURIComponent(selectedProject),{method:'POST',body:fd}); ok++; }catch(e){ fail++; } } $('assetFile').value=''; toast('Uploaded '+ok+(fail?', failed '+fail:'')); navigateTo(currentDir); }); $('cmdInput').addEventListener('input',function(e){ renderCmds(e.target.value); }); });
async function downloadUrl(){ if(!selectedProject)return; var url=$('dlUrl').value.trim(); if(!url)return toast('Enter URL','err'); try{ var d=await api('/api/download-url/'+encodeURIComponent(selectedProject),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,path:currentDir,filename:$('dlName').value.trim()})}); toast('Downloaded '+fmtSize(d.size)); $('dlUrl').value=''; $('dlName').value=''; navigateTo(currentDir); }catch(e){ toast(e.message,'err'); } }
async function exportZip(){ if(!selectedProject)return; try{ var r=await fetch('/api/export-zip/'+encodeURIComponent(selectedProject),{method:'POST'}); var blob=await r.blob(); var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=selectedProject+'.zip'; a.click(); toast('Exported'); }catch(e){ toast(e.message,'err'); } }
function importZip(){ if(!selectedProject)return; var inp=document.createElement('input'); inp.type='file'; inp.accept='.zip'; inp.onchange=async function(){ if(!inp.files[0])return; var fd=new FormData(); fd.append('file',inp.files[0]); try{ await api('/api/import-zip/'+encodeURIComponent(selectedProject),{method:'POST',body:fd}); toast('Imported'); navigateTo(currentDir); }catch(e){ toast(e.message,'err'); } }; inp.click(); }
function switchTab(name){ document.querySelectorAll('.tab').forEach(function(t){ t.classList.toggle('active',t.dataset.tab===name); }); document.querySelectorAll('.tabPane').forEach(function(p){ p.classList.toggle('active',p.id==='tab-'+name); }); if(name==='editor'&&cm)setTimeout(function(){cm.refresh();},50); }
function openPreview(){ if(!selectedProject)return; $('preview').src='/preview/'+encodeURIComponent(selectedProject)+'/?t='+Date.now(); }
function toggleFullPreview(){ var f=$('preview'); if(f.requestFullscreen)f.requestFullscreen(); else if(f.webkitRequestFullscreen)f.webkitRequestFullscreen(); }
async function buildApk(){ if(!selectedProject)return; try{ await api('/api/build/'+encodeURIComponent(selectedProject),{method:'POST'}); switchTab('build'); toast('Build started…','info'); refreshBuild(); }catch(e){ toast(e.message,'err'); } }
async function refreshBuild(){ try{ var d=await api('/api/build-status'); var cls=d.error?'err':d.busy?'warn':(d.status==='success'?'ok':''); $('buildStatus').className='pill '+cls; $('buildStatus').textContent=(d.busy?'⏳ ':'')+d.status+(d.project?' • '+d.project:''); $('progressFill').style.width=(d.progress||0)+'%'; $('buildLog').textContent=(d.log||[]).join('\n')||'No logs'; $('buildLog').scrollTop=$('buildLog').scrollHeight; if(d.status==='success'&&!d.busy&&!refreshBuild._c){ refreshBuild._c=true; confetti(); toast('Build successful!','info'); refreshApks(); setTimeout(function(){refreshBuild._c=false;},30000); } }catch(e){} }
async function refreshApks(){ try{ var a=await api('/api/apks'); var el=$('apksHome'); el.innerHTML=''; if(!a.length){ el.innerHTML='<small class="muted">No APKs yet</small>'; return; } a.forEach(function(x){ var d=document.createElement('div'); d.className='apkItem'; d.innerHTML='<div class="apkInfo"><div class="apkName">📦 '+esc(x.name)+'</div><div class="apkSize">'+fmtSize(x.size)+' · '+fmtTime(x.modified)+'</div></div><div class="apkBtns"><button class="btn sm green" data-a="i">Install</button><a class="btn sm primary" href="/api/download-apk/'+encodeURIComponent(x.name)+'" download style="text-decoration:none">⬇</a></div>'; d.querySelector('[data-a="i"]').onclick=async function(){ try{ var r=await api('/api/install-apk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:x.name})}); toast(r.message||'Opened','info'); }catch(e){ toast(e.message,'err'); } }; el.appendChild(d); }); }catch(e){} }
applyTheme(); refreshAll(); setInterval(refreshBuild,2500);
</script>
</body>
</html>'''

if __name__ == '__main__':
    print(f'⚡ Zihad 3D Game Studio v3.1 — http://127.0.0.1:{PORT}')
    print(f'   Projects: {PROJECTS}')
    print(f'   APK out:  {APK_OUT}')
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
