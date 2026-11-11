"""Trusted loopback-only FastAPI service: python -m uvicorn backend.api:app --host 127.0.0.1"""
import os,json,secrets,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import joblib,numpy as np,pandas as pd
from fastapi import FastAPI,UploadFile,File,Header,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .core import ROOT,normalize_csv,study_area,match_observations,replace_provisional
from .train import run,features
app=FastAPI(title='Bago Yoma FireWatch',version='1.0');app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:4173','http://127.0.0.1:4173'],allow_methods=['GET','POST'],allow_headers=['Content-Type','X-API-Key'])
runtime=ROOT/'data/runtime';runtime.mkdir(exist_ok=True,parents=True);jobs={};pool=ThreadPoolExecutor(max_workers=1)
@lru_cache(maxsize=12)
def read_json(path:str,mtime:int):return json.loads(Path(path).read_text(encoding='utf-8'))
def cached_json(path):return read_json(str(path),path.stat().st_mtime_ns)
def auth(key):
 expected=os.getenv('FIREWATCH_API_KEY')
 if not expected:raise HTTPException(503,'Set FIREWATCH_API_KEY for local mutations')
 if not key or not secrets.compare_digest(key,expected):raise HTTPException(401,'Invalid API key')
@app.get('/api/health')
def health():return {'status':'ok','model_exists':(runtime/'model.joblib').exists(),'mode':'local'}
@app.get('/api/model')
def model():
 p=ROOT/'public/data/model-report.json'
 if not p.exists():raise HTTPException(503,'No model evaluation available')
 return cached_json(p)
@app.get('/api/hotspots')
def hotspots(year:int=2025,month:int|None=None,sensor:str='both',offset:int=0,limit:int=500):
 if not 2000<=year<=2100 or month is not None and not 1<=month<=12 or sensor not in ['MODIS','VIIRS','both']:raise HTTPException(422,'Invalid filter')
 p=ROOT/f'public/data/hotspots-{year}.json'
 if not p.exists():raise HTTPException(404,'No records for this year')
 rows=[r for r in cached_json(p) if (sensor=='both' or r['sensor']==sensor) and (month is None or int(r['date'][5:7])==month)]
 return {'total':len(rows),'items':rows[max(0,offset):max(0,offset)+min(max(1,limit),5000)],'coverage':'unknown'}
@app.post('/api/import')
async def import_csv(file:UploadFile=File(...),x_api_key:str|None=Header(None)):
 auth(x_api_key);content=await file.read(25*1024*1024+1)
 if len(content)>25*1024*1024:raise HTTPException(413,'Maximum 25 MB')
 try:d,stats=normalize_csv(content,file.filename or 'import.csv',study_area())
 except Exception as e:raise HTTPException(422,str(e))
 d=replace_provisional(d);stats['retained_after_revision']=len(d)
 digest=hashlib.sha256(content).hexdigest();folder=runtime/'imports';folder.mkdir(exist_ok=True);target=folder/(digest+'.csv')
 if not target.exists():target.write_bytes(content)
 d.to_json(folder/(digest+'.processed.json'),orient='records',date_format='iso');(folder/(digest+'.metadata.json')).write_text(json.dumps({'filename':file.filename,**stats}))
 return {'sha256':digest,'model_retrained':False,**stats}
class Match(BaseModel):
 sha256:str=Field(pattern='^[0-9a-f]{64}$');meters:float=Field(default=1000,ge=50,le=5000);minutes:float=Field(default=90,ge=1,le=1440)
@app.post('/api/match')
def match(req:Match,x_api_key:str|None=Header(None)):
 auth(x_api_key);p=runtime/'imports'/(req.sha256+'.csv')
 if not p.exists():raise HTTPException(404,'Import not found')
 meta=json.loads(p.with_suffix('.metadata.json').read_text());d,_=normalize_csv(p.read_bytes(),meta['filename'],study_area())
 return {'matches':match_observations(d,req.meters,req.minutes),'meaning':'Candidate sensor pairs, not confirmed incidents'}
@app.post('/api/train')
def train(x_api_key:str|None=Header(None)):
 auth(x_api_key)
 if any(j['status']=='running' for j in jobs.values()):raise HTTPException(409,'Training already running')
 id=secrets.token_hex(10);jobs[id]={'status':'running'}
 def work():
  try:r=run();jobs[id]={'status':'complete','selected_model':r['selected_model']}
  except Exception as e:jobs[id]={'status':'failed','error':str(e)}
 pool.submit(work);return {'job_id':id,'source':'Verified annual archives in data/raw; staged imports are not automatically promoted'}
@app.get('/api/jobs/{id}')
def job(id:str):
 if id not in jobs:raise HTTPException(404,'No job')
 return jobs[id]
class Predict(BaseModel):
 months:int=Field(default=48,ge=1,le=48);scenario:str='baseline';cell_ids:list[str]|None=None
@app.post('/api/predict')
def predict(req:Predict):
 if req.scenario not in ['baseline','dry','wet']:raise HTTPException(422,'Unknown scenario')
 p=runtime/'model.joblib'
 if not p.exists():raise HTTPException(503,'No model trained')
 bundle=joblib.load(p);history=bundle['history'];report=bundle['report'];cells=history[['cell_id','lat','lon']].drop_duplicates()
 if req.cell_ids is not None:cells=cells[cells.cell_id.isin(req.cell_ids)]
 if cells.empty:raise HTTPException(422,'No known cells')
 dates=pd.date_range(report['forecast_origin'],periods=req.months,freq='MS');future=pd.concat([cells.assign(m=d.month,period=d.strftime('%Y-%m')) for d in dates],ignore_index=True);x=features(history,future);name=bundle['selected_model'];pred=x.season_frequency.values if name=='Seasonal baseline' else bundle['models'][name].predict_proba(x)[:,1];k={'baseline':1,'dry':1.25,'wet':.8}[req.scenario];pred=pred*k/(1-pred+pred*k);ref=np.sort([r['raw_proxy'] for r in json.loads((ROOT/'public/data/seasonal-risk.json').read_text())]);future['index']=np.searchsorted(ref,pred,side='right')/len(ref)*100
 lookup={(r['cell_id'],r['month']):r for r in cached_json(ROOT/'public/data/seasonal-risk.json')}
 if req.scenario=='baseline':future['index']=[lookup[(r.cell_id,r.m)]['index'] for r in future.itertuples()]
 future['baseline_spread_low']=[lookup[(r.cell_id,r.m)]['spread_low'] for r in future.itertuples()];future['baseline_spread_high']=[lookup[(r.cell_id,r.m)]['spread_high'] for r in future.itertuples()]
 return {'target':report['target'],'units':'relative percentile index, not fire probability','origin':report['forecast_origin'],'scenario':req.scenario,'model_version':report['version'],'uncertainty':report['uncertainty_method'],'items':future[['cell_id','period','index','baseline_spread_low','baseline_spread_high']].round(3).to_dict('records')}

# A built frontend and the API can run together locally; data updates do not need a UI rebuild.
app.mount('/data',StaticFiles(directory=ROOT/'public/data'),name='data')
if (ROOT/'dist/index.html').exists():app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
