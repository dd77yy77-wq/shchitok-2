#!/usr/bin/env python3
"""Build Shchitok2.apk without Android SDK. Usage: build.py <versionCode> <versionName> <out.apk>"""
import sys, os, struct, subprocess, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import apkbuild as A
from apkbuild import N, T_REF, T_STR, T_INT, T_HEX, T_BOOL

HERE = os.path.dirname(os.path.abspath(__file__))
code, name, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
PKG = 'com.dd.shchitok2'
DXCP = os.environ.get('DXCP', '/tmp/dalvik/dxout')   # см. tools/setup_dx.sh
KEYDIR = os.environ.get('KEYDIR', os.path.join(HERE, 'keys'))
B = os.path.join(HERE, 'build'); shutil.rmtree(B, ignore_errors=True)
for d in ('stubcls', 'classes', 'dex'): os.makedirs(os.path.join(B, d))

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    err = '\n'.join(l for l in (r.stdout + r.stderr).splitlines() if 'JAVA_TOOL_OPTIONS' not in l)
    if r.returncode: sys.exit('FAILED: %s\n%s' % (' '.join(cmd), err))
    return err

# 1. dex
srcs = lambda root: [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(HERE, root)) for f in fs if f.endswith('.java')]
run(['javac', '-nowarn', '-source', '8', '-target', '8', '-Xlint:-options', '-d', B + '/stubcls'] + srcs('stubs'))
run(['javac', '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-Xlint:-options', '-g:none', '-cp', B + '/stubcls', '-d', B + '/classes'] + srcs('src'))
run(['java', '-cp', DXCP, 'com.android.dx.command.Main', '--dex', '--min-sdk-version=24', '--output=' + B + '/dex/classes.dex', B + '/classes'])
dex = open(B + '/dex/classes.dex', 'rb').read()

# 2. icon resources: готовые слои «Щиток 86» из утверждённого комплекта.
ICON_RES = os.path.join(HERE, 'icons')
def icon_bytes(relative):
    with open(os.path.join(ICON_RES, relative), 'rb') as source:
        return source.read()
files = {}  # path -> bytes (stored)
dens = [(160, 'mdpi'), (240, 'hdpi'), (320, 'xhdpi'), (480, 'xxhdpi'), (640, 'xxxhdpi')]
def cfg(density, sdk=0):
    c = bytearray(64); struct.pack_into('<I', c, 0, 64); struct.pack_into('<H', c, 14, density); struct.pack_into('<H', c, 24, sdk); return bytes(c)
bg_cfgs, fg_cfgs, mip_cfgs, round_cfgs = [], [], [], []
for dpi, q in dens:
    density_cfg = cfg(dpi)
    for kind, configs in (('background', bg_cfgs), ('foreground', fg_cfgs)):
        source = 'drawable-%s-v4/ic_launcher_%s.png' % (q, kind)
        target = 'res/' + source
        files[target] = icon_bytes(source)
        configs.append((density_cfg, target))
    for icon_name, configs in (('ic_launcher', mip_cfgs), ('ic_launcher_round', round_cfgs)):
        source = 'mipmap-%s-v4/%s.png' % (q, icon_name)
        target = 'res/' + source
        files[target] = icon_bytes(source)
        configs.append((density_cfg, target))
adaptive = A.build_axml(N('adaptive-icon', [], [
    N('background', [(True, 'drawable', T_REF, 0x7f010000)]),
    N('foreground', [(True, 'drawable', T_REF, 0x7f010001)]),
]), True)
for icon_name, configs in (('ic_launcher', mip_cfgs), ('ic_launcher_round', round_cfgs)):
    target = 'res/mipmap-anydpi-v26/%s.xml' % icon_name
    files[target] = adaptive
    configs.append((cfg(0xfffe, 26), target))
arsc = A.build_arsc(PKG, [
    ('drawable', [('ic_launcher_background', bg_cfgs), ('ic_launcher_foreground', fg_cfgs)], 0x100),
    ('mipmap', [('ic_launcher', mip_cfgs), ('ic_launcher_round', round_cfgs)], 0x500),
])

# 3. manifest
a = lambda n, t, v: (True, n, t, v)
A.ATTR_IDS.update({'configChanges': 0x0101001f, 'authorities': 0x01010018, 'grantUriPermissions': 0x0101001b, 'roundIcon': 0x010102a7})
manifest = A.build_axml(N('manifest', [a('versionCode', T_INT, code), a('versionName', T_STR, name), (False, 'package', T_STR, PKG)], [
    N('uses-permission', [a('name', T_STR, 'android.permission.INTERNET')]),
    N('uses-permission', [a('name', T_STR, 'android.permission.REQUEST_INSTALL_PACKAGES')]),
    N('uses-sdk', [a('minSdkVersion', T_INT, 24), a('targetSdkVersion', T_INT, 34)]),
    N('application', [a('theme', T_REF, 0x0103022e), a('label', T_STR, 'Щиток 86'), a('icon', T_REF, 0x7f020000), a('roundIcon', T_REF, 0x7f020001), a('allowBackup', T_BOOL, 0xffffffff)], [
        N('activity', [a('name', T_STR, PKG + '.MainActivity'), a('exported', T_BOOL, 0xffffffff),
                       a('configChanges', T_HEX, 0x40003fb4), a('windowSoftInputMode', T_HEX, 0x10)], [
            N('intent-filter', [], [N('action', [a('name', T_STR, 'android.intent.action.MAIN')]),
                                    N('category', [a('name', T_STR, 'android.intent.category.LAUNCHER')])])]),
        N('provider', [a('name', T_STR, PKG + '.ApkProvider'), a('exported', T_BOOL, 0), a('authorities', T_STR, PKG + '.files'),
                       a('grantUriPermissions', T_BOOL, 0xffffffff)])])]), False)

# 4. entries
entries = [('AndroidManifest.xml', manifest, 'deflate'), ('resources.arsc', arsc, 'stored')]
for p in sorted(files): entries.append((p, files[p], 'stored'))
entries.append(('classes.dex', dex, 'deflate'))
for dp, _, fs in sorted(os.walk(os.path.join(HERE, 'assets'))):
    for f in sorted(fs):
        full = os.path.join(dp, f); rel = 'assets/' + os.path.relpath(full, os.path.join(HERE, 'assets')).replace(os.sep, '/')
        entries.append((rel, open(full, 'rb').read(), 'stored' if f.endswith(('.jpg', '.png')) else 'deflate'))

# 5. sign
from cryptography.hazmat.primitives.serialization import pkcs12
key_password = os.environ.get('SIGNING_PASSWORD', 'android').encode('utf-8')
key, cert, _ = pkcs12.load_key_and_certificates(open(os.path.join(KEYDIR, 'shchitok2.p12'), 'rb').read(), key_password)
meta = A.v1_files([(n, d) for n, d, _ in entries], cert, key)
# order: manifest first like apksigner does, then everything else, META-INF last
entries = entries + [(n, d, 'deflate') for n, d in meta]
apk = A.write_zip(entries)
apk = A.v2_sign(apk, cert, key)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, 'wb').write(apk)
print('built', out, len(apk), 'bytes')
