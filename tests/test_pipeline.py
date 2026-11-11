import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from shapely.geometry import shape,Point
from fastapi.testclient import TestClient
from backend.core import ROOT,study_area,grid,normalize_csv,replace_provisional,match_observations,TO_UTM,TO_WGS
from backend.train import features,training_features
from backend.api import app

HEADER='latitude,longitude,acq_date,acq_time,instrument,satellite,confidence,version,frp\n'
def load(lines,aoi=None):return normalize_csv((HEADER+'\n'.join(lines)).encode(),'test.csv',aoi)

class PipelineTests(unittest.TestCase):
 def test_dedup_provenance_coordinates_and_quality(self):
  row='18.5,95.9,2024-03-01,0530,MODIS,Terra,70,6.1,10'
  d,s=load([row,row,'18.5,95.9,2024-03-01,0530,VIIRS,N,n,1,8','99,95.9,2024-03-01,0530,MODIS,Terra,80,6.1,10','18.5,95.9,2024-02-30,0530,MODIS,Terra,80,6.1,10'])
  self.assertEqual(s['duplicate'],1);self.assertEqual(s['invalid'],2);self.assertEqual(len(d),2)
  self.assertEqual(set(d.sensor),{'MODIS','VIIRS'});self.assertEqual(set(d.confidence),{'70','n'});self.assertTrue(d.qualifies.all());self.assertEqual(str(d.datetime.dt.tz),'UTC')
 def test_missing_time_is_not_midnight(self):
  d,s=load(['18.5,95.9,2024-03-01,,MODIS,T,70,6.1,10','18.5,95.9,2024-03-01,0,MODIS,T,70,6.1,10'])
  self.assertEqual(s['invalid'],1);self.assertEqual(len(d),1)
 def test_api_import_preserves_raw_and_matches(self):
  content=(HEADER+'18.5,95.9,2024-03-01,0530,MODIS,T,70,6.1,10\n18.5001,95.9001,2024-03-01,0540,VIIRS,N,n,1,8').encode()
  with tempfile.TemporaryDirectory() as tmp,patch('backend.api.runtime',Path(tmp)),patch.dict(os.environ,{'FIREWATCH_API_KEY':'test-only-key'}):
   c=TestClient(app);r=c.post('/api/import',files={'file':('test.csv',content,'text/csv')},headers={'X-API-Key':'test-only-key'})
   self.assertEqual(r.status_code,200);digest=r.json()['sha256'];self.assertEqual((Path(tmp)/'imports'/(digest+'.csv')).read_bytes(),content)
   matched=c.post('/api/match',json={'sha256':digest},headers={'X-API-Key':'test-only-key'})
   self.assertEqual(matched.status_code,200);self.assertEqual(len(matched.json()['matches']),1)
 def test_confidence_scales_never_convert(self):
  d,_=load(['18.5,95.9,2024-03-01,0530,VIIRS,N,90,1,8','18.6,95.9,2024-03-01,0530,MODIS,Terra,150,6.1,8'])
  self.assertFalse(d.qualifies.any());self.assertEqual(d.iloc[0].confidence,'90')
 def test_standard_supersedes_nrt_without_changing_raw(self):
  d,_=load(['18.5,95.9,2024-03-01,0530,MODIS,Terra,60,6.1NRT,8','18.5,95.9,2024-03-01,0530,MODIS,Terra,70,6.1,10'])
  self.assertEqual(len(d),2);r=replace_provisional(d);self.assertEqual(len(r),1);self.assertEqual(r.iloc[0].version,'6.1');self.assertEqual(len(d),2)
 def test_aoi_and_utm_roundtrip(self):
  a=study_area();g=grid(a);self.assertIn('Approximate',a['properties']['status']);self.assertEqual(len(g['features']),589)
  for f in g['features']:self.assertLess(shape(f['geometry']).difference(shape(a['geometry'])).area,1e-10)
  x,y=TO_UTM(95.9,18.5);lon,lat=TO_WGS(x,y);self.assertAlmostEqual(lon,95.9,8);self.assertAlmostEqual(lat,18.5,8)
  d,s=load(['18.5,95.9,2024-03-01,0530,MODIS,T,70,6.1,10','22,97,2024-03-01,0530,MODIS,T,70,6.1,10'],a)
  self.assertEqual(s['outside_aoi'],1);self.assertEqual(len(d),1)
 def test_matching_crosses_midnight_and_respects_time(self):
  d,_=load(['18.5,95.9,2024-03-01,2355,MODIS,T,70,6.1,10','18.5001,95.9001,2024-03-02,0005,VIIRS,N,n,1,8'])
  self.assertEqual(len(match_observations(d,1000,15)),1);self.assertEqual(len(match_observations(d,1000,5)),0)
 def test_temporal_features_ignore_future_labels(self):
  d=pd.DataFrame([dict(cell_id='a',m=3,year=y,lat=18.5,lon=95.9,y=int(y%2)) for y in range(2015,2023)])
  first=training_features(d);d.loc[d.year>=2021,'y']=1-d.loc[d.year>=2021,'y'];second=training_features(d)
  np.testing.assert_allclose(first.loc[d.year<=2021],second.loc[d.year<=2021])
  target=d[d.year==2022];prior=d[d.year<2022];x=features(prior,target);target=target.assign(y=1-target.y);np.testing.assert_allclose(x,features(prior,target))
 def test_coverage_semantics_and_split_integrity(self):
  r=json.loads((ROOT/'public/data/model-report.json').read_text());c=json.loads((ROOT/'public/data/calendar.json').read_text())
  self.assertFalse(r['probability_calibrated']);self.assertLess(max(r['train_years']),min(r['validation_years']));self.assertLess(max(r['validation_years']),min(r['test_years']))
  self.assertTrue(all(x['coverage']=='unknown' for x in c));self.assertTrue(any(x['MODIS']==x['VIIRS']==0 for x in c))
 def test_api_validation_auth_and_model_inference(self):
  client=TestClient(app);self.assertEqual(client.get('/api/health').status_code,200)
  self.assertEqual(client.get('/api/hotspots?month=13').status_code,422)
  self.assertEqual(client.post('/api/predict',json={'months':49}).status_code,422)
  with patch.dict(os.environ,{'FIREWATCH_API_KEY':'test-only-key'}):self.assertEqual(client.post('/api/train').status_code,401)
  cell=json.loads((ROOT/'public/data/grid.geojson').read_text())['features'][0]['id']
  r=client.post('/api/predict',json={'months':36,'cell_ids':[cell]}).json();self.assertEqual(len(r['items']),36);self.assertIn('not fire probability',r['units'])
  self.assertAlmostEqual(r['items'][0]['index'],r['items'][12]['index']);self.assertTrue(all(0<=x['index']<=100 for x in r['items']))
  with patch('backend.api.runtime',Path('/nonexistent-firewatch-model')):self.assertEqual(client.post('/api/predict',json={}).status_code,503)

if __name__=='__main__':unittest.main()
