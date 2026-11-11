"""FireWatch data processing: records are detections, never confirmed wildfire incidents."""
import io,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import shape,Point,box,mapping
from shapely.ops import transform,unary_union
ROOT=Path(__file__).resolve().parents[1]
TO_UTM=Transformer.from_crs(4326,32647,always_xy=True).transform
TO_WGS=Transformer.from_crs(32647,4326,always_xy=True).transform
APPROX={'type':'Feature','properties':{'name':'Bago Yoma study area','status':'Approximate study boundary','source':'Analyst-defined forest-and-hill envelope; not an official forest boundary','version':'1.0','crs':'EPSG:4326','area_crs':'EPSG:32647'},'geometry':{'type':'Polygon','coordinates':[[[95.65,17.45],[96.03,17.45],[96.36,18.20],[96.40,18.95],[96.18,19.22],[95.90,19.18],[95.62,18.65],[95.42,18.05],[95.65,17.45]]]}}
def study_area():
 a=shape(APPROX['geometry']);p=ROOT/'public/data/bago-admin.geojson'
 if p.exists():
  raw=json.loads(p.read_text());a=a.intersection(unary_union([shape(f['geometry']) for f in raw.get('features',[raw])]))
 return {**APPROX,'properties':{**APPROX['properties'],'administrative_clip':p.exists(),'area_km2':round(transform(TO_UTM,a).area/1e6,2)},'geometry':mapping(a)}
def grid(aoi,size=5000):
 a=transform(TO_UTM,shape(aoi['geometry']));x0,y0,x1,y1=a.bounds;fs=[]
 for x in range(int(x0//size)*size,int(x1)+size,size):
  for y in range(int(y0//size)*size,int(y1)+size,size):
   c=box(x,y,x+size,y+size).intersection(a)
   if c.is_empty or c.area<1e5:continue
   center=transform(TO_WGS,c.centroid);id=f'{x//size}_{y//size}'
   fs.append({'type':'Feature','id':id,'properties':{'cell_id':id,'lon':center.x,'lat':center.y,'area_km2':round(c.area/1e6,3)},'geometry':mapping(transform(TO_WGS,c).intersection(shape(aoi['geometry'])))})
 return {'type':'FeatureCollection','features':fs}
def normalize_csv(content,source,aoi=None):
 d=pd.read_csv(io.BytesIO(content),dtype={'acq_time':str,'confidence':str,'version':str},low_memory=False);d.columns=d.columns.str.strip().str.lower()
 missing={'latitude','longitude','acq_date','acq_time'}-set(d.columns)
 if missing:raise ValueError('Missing columns: '+','.join(sorted(missing)))
 total=len(d);dups=int(d.duplicated().sum());d=d.drop_duplicates().copy()
 for c in ['latitude','longitude','frp','scan','track']:d[c]=pd.to_numeric(d[c],errors='coerce') if c in d else np.nan
 d['datetime']=pd.to_datetime(d.acq_date.astype(str)+' '+d.acq_time.fillna('').str.replace(r'\.0$','',regex=True).str.zfill(4),format='%Y-%m-%d %H%M',utc=True,errors='coerce')
 ok=d.latitude.between(-90,90)&d.longitude.between(-180,180)&d.datetime.notna()&d.acq_time.fillna('').str.match(r'^\d{1,4}(\.0)?$');invalid=int((~ok).sum());d=d[ok].copy()
 if 'instrument' in d:d['sensor']=d.instrument.astype(str).str.upper()
 elif 'sensor' not in d:d['sensor']='VIIRS' if 'viirs' in source.lower() else 'MODIS' if 'modis' in source.lower() else 'UNKNOWN'
 if not d.sensor.isin(['MODIS','VIIRS']).all():raise ValueError('Unknown sensor; supply instrument MODIS or VIIRS')
 for c in ['confidence','satellite','daynight','version']:
  if c not in d:d[c]='unknown'
 d['confidence']=d.confidence.fillna('unknown').astype(str);d['processing_type']=np.where(d.version.str.contains('NRT',case=False,na=False),'NRT','standard_or_unspecified')
 d['source']=source;d['ingested_at']=datetime.now(timezone.utc).isoformat();outside=0
 if aoi:
  a=shape(aoi['geometry']);b=a.bounds;s=d[d.longitude.between(b[0],b[2])&d.latitude.between(b[1],b[3])];s=s[s.apply(lambda r:a.covers(Point(r.longitude,r.latitude)),axis=1).astype(bool)];outside=len(d)-len(s);d=s.copy()
 d['qualifies']=((d.sensor=='MODIS')&(pd.to_numeric(d.confidence,errors='coerce').between(30,100)))|((d.sensor=='VIIRS')&d.confidence.str.lower().isin(['n','h','nominal','high']))
 x,y=TO_UTM(d.longitude.to_numpy(),d.latitude.to_numpy());d['cell_id']=[f'{int(a//5000)}_{int(b//5000)}' for a,b in zip(x,y)];d['month']=d.datetime.dt.strftime('%Y-%m');d['year']=d.datetime.dt.year
 d['id']=[hashlib.sha256(f'{a}|{b}|{c}|{e}|{f}'.encode()).hexdigest()[:18] for a,b,c,e,f in zip(d.latitude,d.longitude,d.datetime,d.sensor,d.satellite)]
 return d,{'input':total,'invalid':invalid,'duplicate':dups,'outside_aoi':outside,'retained':len(d),'qualified':int(d.qualifies.sum())}
def replace_provisional(d):
 d=d.copy();d['_priority']=(d.processing_type!='NRT').astype(int)
 return d.sort_values('_priority',ascending=False).drop_duplicates(['latitude','longitude','datetime','sensor','satellite']).drop(columns='_priority')
def match_observations(d,meters=1000,minutes=90):
 from scipy.spatial import cKDTree
 q=d[d.qualifies].sort_values('datetime');pairs=[]
 # Join adjacent UTC days as well so pairs crossing midnight are not missed.
 v=q[q.sensor=='VIIRS'];m=q[q.sensor=='MODIS']
 if v.empty or m.empty:return pairs
 vx,vy=TO_UTM(v.longitude.values,v.latitude.values);mx,my=TO_UTM(m.longitude.values,m.latitude.values);tree=cKDTree(np.c_[vx,vy]);used=set();vt=v.datetime.astype('int64').to_numpy();mt=m.datetime.astype('int64').to_numpy();vi=v.id.to_numpy();mi=m.id.to_numpy()
 for i,candidates in enumerate(tree.query_ball_point(np.c_[mx,my],meters)):
  cs=[j for j in candidates if j not in used and abs(int(mt[i])-int(vt[j]))<=minutes*60*1e9]
  if cs:
   j=min(cs,key=lambda k:(vx[k]-mx[i])**2+(vy[k]-my[i])**2);used.add(j);pairs.append({'modis':mi[i],'viirs':vi[j]})
 return pairs
