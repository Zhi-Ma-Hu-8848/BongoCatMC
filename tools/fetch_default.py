import urllib.request,json,pathlib,subprocess,base64,concurrent.futures,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
token=subprocess.check_output(['gh','auth','token'],text=True).strip()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base='https://api.github.com/repos/vladelaina/BongoCat/'
def read(url,raw=False):
 h={'User-Agent':'BongoCatMC-prototype','Authorization':'Bearer '+token,'Accept':'application/vnd.github.raw+json' if raw else 'application/vnd.github+json'}
 with opener.open(urllib.request.Request(url,headers=h),timeout=30) as r:return r.read()
tree=json.loads(read(base+'git/trees/main?recursive=1'))
source=root/'assets/source/standard';source.mkdir(parents=True,exist_ok=True)
prefix='resources/assets/models/standard/'
items=[x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith(prefix) or x['path']=='resources/assets/LICENSE-MIT')]
def get(x):
 rel=x['path'][len(prefix):] if x['path'].startswith(prefix) else 'LICENSE-MIT'
 dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists() and dest.stat().st_size==x['size']:return
 data=read(base+'git/blobs/'+x['sha'],True)
 if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=x['sha']:raise ValueError('Hash mismatch: '+rel)
 dest.write_bytes(data)
 print(rel,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(get,items))
(root/'assets/source/provenance.json').write_text(json.dumps({'repository':'https://github.com/vladelaina/BongoCat','tree':tree['sha'],'files':items},ensure_ascii=False,indent=2),encoding='utf8')
print('DONE',len(items),flush=True)
