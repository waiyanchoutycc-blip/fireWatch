"""Build a portable source + processed data + fitted model ZIP without credentials/raw downloads."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'public/firewatch-source.zip'
roots=['.github','backend','frontend','scripts','tests','docs','public/data']
files=[ROOT/name for name in ['README.md','package.json','package-lock.json','tsconfig.json','vite.config.ts','index.html','requirements.txt','requirements.lock.txt','requirements-gee.txt','.env.example','.gitignore','Dockerfile','.dockerignore','data/runtime/model.joblib']]
for name in roots:files.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for p in sorted(set(files)):
  if not p.exists():raise FileNotFoundError(p)
  z.write(p,p.relative_to(ROOT))
 z.writestr('PACKAGE-MANIFEST.json',json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))},indent=2))
print(json.dumps({'path':str(target),'bytes':target.stat().st_size,'files':len(set(files)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
