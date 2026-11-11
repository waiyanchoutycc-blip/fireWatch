"""Optional backend-only FIRMS area ingestion. No credential is written to files or logs."""
import argparse,hashlib,json,os,sys
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.core import normalize_csv,study_area

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',choices=['MODIS_SP','VIIRS_SNPP_SP','MODIS_NRT','VIIRS_SNPP_NRT'],default='VIIRS_SNPP_SP')
 p.add_argument('--date',required=True);p.add_argument('--days',type=int,choices=range(1,6),default=1);a=p.parse_args();date.fromisoformat(a.date)
 key=os.getenv('FIRMS_MAP_KEY')
 if not key:raise SystemExit('Set FIRMS_MAP_KEY in the backend environment. No request sent.')
 # Bounds cover the default study polygon. Polygon clipping happens after retrieval.
 url=f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{a.source}/95.4,17.4,96.5,19.3/{a.days}/{a.date}'
 try:
  with urlopen(url,timeout=60) as response:content=response.read()
 except Exception:raise SystemExit('FIRMS request failed. Check key, product availability and network; no synthetic data substituted.') from None
 if not content.lstrip().startswith(b'latitude,longitude'):raise SystemExit('FIRMS returned an error or unavailable product, not a CSV.')
 digest=hashlib.sha256(content).hexdigest();folder=ROOT/'data/raw/api';folder.mkdir(parents=True,exist_ok=True);name=f'{a.source}_{a.date}_{digest[:12]}.csv';path=folder/name
 if not path.exists():path.write_bytes(content)
 data,stats=normalize_csv(content,name,study_area());data['processing_type']='NRT' if a.source.endswith('NRT') else 'standard'
 output=ROOT/'data/runtime/api';output.mkdir(parents=True,exist_ok=True)
 data.to_json(output/(digest+'.json'),orient='records',date_format='iso')
 (output/(digest+'.manifest.json')).write_text(json.dumps({'source':'NASA FIRMS area API','product':a.source,'sha256':digest,'raw_file':name,'ingested_at':datetime.now(timezone.utc).isoformat(),'coverage':'unknown','model_retrained':False,**stats},indent=2))
 print(json.dumps({'saved':str(path),'sha256':digest,'model_retrained':False,**stats}))

if __name__=='__main__':main()
