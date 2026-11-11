"""Reproducible real-data training; no synthetic fallback. python -m backend.train"""
import json,hashlib,argparse,shutil
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,average_precision_score,brier_score_loss
from sklearn.calibration import calibration_curve
from .core import ROOT,study_area,grid,normalize_csv,replace_provisional,match_observations
SEED=42
FEATURES=['lat','lon','sin_month','cos_month','season_frequency','cell_frequency']
def features(train,rows):
 season=train.groupby('m').y.mean();overall=float(train.y.mean());sm=train.groupby(['cell_id','m']).y.agg(['sum','count']);cell=train.groupby('cell_id').y.agg(['sum','count']);out=rows[['lat','lon']].copy();out['sin_month']=np.sin(2*np.pi*rows.m/12);out['cos_month']=np.cos(2*np.pi*rows.m/12)
 out['season_frequency']=[(sm.loc[(c,m),'sum']+2*season.get(m,overall))/(sm.loc[(c,m),'count']+2) if (c,m) in sm.index else season.get(m,overall) for c,m in zip(rows.cell_id,rows.m)]
 out['cell_frequency']=[(cell.loc[c,'sum']+2*overall)/(cell.loc[c,'count']+2) if c in cell.index else overall for c in rows.cell_id]
 return out[FEATURES]
def training_features(train):
 blocks=[]
 for year in sorted(train.year.unique()):
  prior=train[train.year<year]
  if len(prior):blocks.append(features(prior,train[train.year==year]))
 return pd.concat(blocks).sort_index()
def fit_models(train):
 x=training_features(train);y=train.loc[x.index].y
 if y.nunique()<2:raise ValueError('Both classes required')
 models={'Logistic regression':make_pipeline(StandardScaler(),LogisticRegression(max_iter=600,class_weight='balanced',random_state=SEED)),'Random forest':RandomForestClassifier(n_estimators=100,max_depth=10,min_samples_leaf=20,class_weight='balanced_subsample',n_jobs=2,random_state=SEED)}
 for model in models.values():model.fit(x,y)
 return models

def metrics(y,p,t=.5):
 pred=p>=t;a,b=calibration_curve(y,p,n_bins=8,strategy='quantile')
 return {'accuracy':float(accuracy_score(y,pred)),'precision':float(precision_score(y,pred,zero_division=0)),'recall':float(recall_score(y,pred,zero_division=0)),'f1':float(f1_score(y,pred,zero_division=0)),'pr_auc':float(average_precision_score(y,p)) if np.any(y) else 0.,'brier':float(brier_score_loss(y,p)),'threshold':float(t),'samples':len(y),'positive_rate':float(np.mean(y)),'calibration':{'observed':a.tolist(),'predicted':b.tolist()}}
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=lambda o:o.item() if hasattr(o,'item') else str(o),allow_nan=False))
def run(rawdir=ROOT/'data/raw',outdir=ROOT/'public/data'):
 outdir.mkdir(parents=True,exist_ok=True);aoi=study_area();g=grid(aoi);write(outdir/'aoi.geojson',aoi);write(outdir/'grid.geojson',g)
 files=sorted(Path(rawdir).glob('*.csv'))
 if not files:raise ValueError('No NASA archives; run acquisition first')
 blocks=[];manifest=[]
 for f in files:
  d,stats=normalize_csv(f.read_bytes(),f.name,aoi);blocks.append(d);manifest.append({'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),**stats})
 d=replace_provisional(pd.concat(blocks,ignore_index=True));q=d[d.qualifies];ids={f['id'] for f in g['features']};q=q[q.cell_id.isin(ids)];vi=q[q.sensor=='VIIRS'];mod=q[q.sensor=='MODIS'];years=sorted(set(vi.year)&set(mod.year))
 if len(years)<7:raise ValueError('At least 7 overlapping full years required')
 cutoff=years[-5];val_years=years[-4:-2];test_years=years[-2:];meta=pd.DataFrame([f['properties'] for f in g['features']])
 panel=pd.MultiIndex.from_product([meta.cell_id,pd.period_range(f'{years[0]}-01',f'{years[-1]}-12',freq='M').astype(str)],names=['cell_id','month']).to_frame(index=False).merge(meta[['cell_id','lat','lon']],on='cell_id');panel['year']=panel.month.str[:4].astype(int);panel['m']=panel.month.str[5:7].astype(int);panel=panel[panel.year.isin(years)].reset_index(drop=True)
 counts=vi.groupby(['cell_id','month']).size().rename('count').reset_index();panel=panel.merge(counts,on=['cell_id','month'],how='left');panel['y']=(panel['count'].fillna(0)>0).astype(int)
 tr=panel[panel.year<=cutoff];va=panel[panel.year.isin(val_years)];te=panel[panel.year.isin(test_years)];models=fit_models(tr);xv=features(tr,va);xt=features(tr,te)
 preds={'Seasonal baseline':(xv.season_frequency.values,xt.season_frequency.values)}
 for name,model in models.items():preds[name]=(model.predict_proba(xv)[:,1],model.predict_proba(xt)[:,1])
 results={};thresholds={}
 for name,(pv,pt) in preds.items():
  threshold=float(max(np.arange(.05,.96,.05),key=lambda t:f1_score(va.y,pv>=t,zero_division=0)));thresholds[name]=threshold;results[name]={'validation':metrics(va.y,pv,threshold),'test':metrics(te.y,pt,threshold),'by_season':{label:metrics(te.y.values[te.m.isin(ms)],pt[te.m.isin(ms)],threshold) for label,ms in {'dry_Nov_Apr':[11,12,1,2,3,4],'wet_May_Oct':[5,6,7,8,9,10]}.items()}}
 chosen=min(results,key=lambda n:results[n]['validation']['brier'])
 hold=set(meta.sort_values('lon').tail(max(1,len(meta)//5)).cell_id);st=tr[~tr.cell_id.isin(hold)];se=te[te.cell_id.isin(hold)];sm=fit_models(st)['Random forest'];spatial=metrics(se.y,sm.predict_proba(features(st,se))[:,1],thresholds['Random forest'])
 rolling=[]
 for origin in [years[-7],years[-5]]:
  rt=panel[panel.year<=origin];re=panel[(panel.year>origin)&(panel.year<=origin+4)]
  if rt.year.nunique()<3:continue
  rm=fit_models(rt)['Random forest'];rx=features(rt,re);rp=rm.predict_proba(rx)[:,1]
  for y in sorted(re.year.unique()):
   ix=(re.year==y).values;rolling.append({'origin':int(origin),'lead_year':int(y-origin),'random_forest':metrics(re.y.values[ix],rp[ix]),'baseline':metrics(re.y.values[ix],rx.season_frequency.values[ix])})
 # Use only training-era pairs for experimental sensor adjustment.
 monthly=q.groupby(['month','sensor']).size().unstack(fill_value=0).reindex(columns=['MODIS','VIIRS'],fill_value=0).reindex(panel.month.unique(),fill_value=0).sort_index();cal=monthly[monthly.index.str[:4].astype(int)<=cutoff];ratio=float((cal.VIIRS.sum()+1)/(cal.MODIS.sum()+1));ratios={}
 for m in range(1,13):
  c=cal[cal.index.str[5:7].astype(int)==m];ratios[str(m)]=float((c.VIIRS.sum()+ratio*20)/(c.MODIS.sum()+20))
 calendar=[]
 for date,r in monthly.iterrows():
  adjusted=float(r.MODIS*ratios[str(int(date[5:7]))]);calendar.append({'month':date,'MODIS':int(r.MODIS),'VIIRS':int(r.VIIRS),'adjusted_modis':round(adjusted,2),'harmonized':round((adjusted+r.VIIRS)/2,2),'coverage':'unknown','record_available':True})
 testcal=[r for r in calendar if int(r['month'][:4]) in test_years];mae=lambda key:float(np.mean([abs(r[key]-r['VIIRS']) for r in testcal]))
 harmonization={'method':'Training-period monthly regional MODIS-to-VIIRS ratio; average adjusted MODIS and VIIRS, never sum. Not unique fire counts.','train_end':int(cutoff),'ratios':ratios,'heldout_modis_raw_mae':mae('MODIS'),'heldout_modis_adjusted_mae':mae('adjusted_modis'),'calibration_scope':'Original study AOI only','coverage':'unknown'}
 final=fit_models(panel);future=pd.MultiIndex.from_product([meta.cell_id,range(1,13)],names=['cell_id','m']).to_frame(index=False).merge(meta[['cell_id','lat','lon']],on='cell_id');xf=features(panel,future);rf=final['Random forest'];pf=xf.season_frequency.values if chosen=='Seasonal baseline' else final[chosen].predict_proba(xf)[:,1]
 if chosen=='Seasonal baseline':
  rng=np.random.default_rng(SEED);draws=[]
  for _ in range(40):
   ys=rng.choice(years,len(years),replace=True);boot=pd.concat([panel[panel.year==y] for y in ys]);draws.append(features(boot,future).season_frequency.values)
  spread=np.array(draws)
 else:spread=np.array([tree.predict_proba(xf.to_numpy())[:,1] for tree in rf.estimators_]) if chosen=='Random forest' else np.array([pf,pf])
 lo,hi=np.quantile(spread,[.1,.9],axis=0);order=np.sort(pf);rank=lambda p:float(np.searchsorted(order,p,side='right')/len(order)*100);season=[]
 for i,r in future.iterrows():season.append({'cell_id':r.cell_id,'month':int(r.m),'index':round(rank(pf[i]),1),'spread_low':round(rank(lo[i]),1),'spread_high':round(rank(hi[i]),1),'raw_proxy':round(float(pf[i]),6)})
 now=pd.Timestamp.now(tz='UTC').isoformat();latest=str(d.datetime.max().date())
 report={'version':'1.0','trained_at':now,'seed':SEED,'target':'At least one qualifying VIIRS S-NPP recorded detection per 5 km cell-month. No-record labels are NOT confirmed no-fire observations.','probability_calibrated':False,'selected_model':chosen,'features':FEATURES,'train_years':[int(years[0]),int(cutoff)],'validation_years':val_years,'test_years':test_years,'results':results,'spatial_holdout':{'method':'Easternmost 20% of cells excluded during training; evaluated in test years','metrics':spatial},'rolling_origin':rolling,'feature_importance':dict(zip(FEATURES,rf.feature_importances_.tolist())),'training_samples':len(tr),'test_samples':len(te),'grid_cells':len(meta),'latest_observation':latest,'forecast_origin':pd.Timestamp.now(tz='Asia/Yangon').strftime('%Y-%m-01'),'observation_gap_start':f'{years[-1]+1}-01-01','refit_years':years,'uncertainty_method':'10th–90th year-bootstrap spread (seasonal baseline), or tree disagreement (RF); not a calibrated prediction interval','limitations':['GEE coverage and environmental predictors were not acquired.','No-record labels mix true negatives, missed detections and unobserved periods.','Annual seasonal pattern repeats; no year-specific climate forecast.','No official Bago Yoma forest polygon; approximate envelope clipped to Bago.','No calibrated actual-fire probabilities or emergency warnings.']}
 report['configuration']={'grid_m':5000,'quality':{'MODIS':'confidence 30–100','VIIRS':'nominal or high'},'random_forest':{'trees':100,'max_depth':10,'min_samples_leaf':20,'class_weight':'balanced_subsample'},'selection':'validation Brier','decision_threshold':'maximum validation F1 on 0.05–0.95 grid','feature_history':'strictly earlier years','coverage_policy':'record presence proxy only','projection_refit':'all available years, after evaluation'}
 report['data_manifest']=manifest;report['feature_schema']={f:'float64' for f in FEATURES}
 report['algorithm_version']='1.1'
 report['source_hash']=hashlib.sha256((Path(__file__).read_text()+(ROOT/'backend/core.py').read_text()).encode()).hexdigest()
 harmonization['candidate_pairs']={'count':len(match_observations(q)), 'distance_m':1000,'time_minutes':90,'method':'Greedy one-to-one cross-sensor nearest matches; includes midnight; not confirmed fire incidents; not used to add or subtract calendar counts'}
 rng=np.random.default_rng(SEED);ratio_draws={str(m):[] for m in range(1,13)}
 for _ in range(100):
  sampled=pd.concat([cal[cal.index.str[:4].astype(int)==y] for y in rng.choice(sorted(cal.index.str[:4].astype(int).unique()),len(cal.index.str[:4].astype(int).unique()),replace=True)])
  for m in range(1,13):
   c=sampled[sampled.index.str[5:7].astype(int)==m];ratio_draws[str(m)].append(float((c.VIIRS.sum()+ratio*20)/(c.MODIS.sum()+20)))
 harmonization['ratio_spread']={m:np.quantile(values,[.1,.9]).tolist() for m,values in ratio_draws.items()}
 harmonization['uncertainty']='10th–90th percentile from 100 training-year resamples; not complete detection-bias uncertainty'
 records=[]
 for r in d.itertuples():
  records.append({'id':r.id,'lat':r.latitude,'lon':r.longitude,'date':str(r.datetime.date()),'time':r.datetime.strftime('%H:%M'),'sensor':r.sensor,'satellite':str(r.satellite),'confidence':r.confidence,'frp':None if pd.isna(r.frp) else r.frp,'scan':None if pd.isna(r.scan) else r.scan,'track':None if pd.isna(r.track) else r.track,'daynight':str(r.daynight),'version':str(r.version),'processing_type':r.processing_type,'source':r.source,'ingested_at':r.ingested_at,'cell_id':r.cell_id,'qualified':bool(r.qualifies)})
 summary={'mode':'real','record_count':len(records),'qualified_count':int(d.qualifies.sum()),'years':years,'latest_observation':latest,'updated_at':now,'grid_cells':len(meta),'manifest':manifest,'source':'NASA FIRMS Myanmar annual archives'}
 for name,obj in [('summary',summary),('model-report',report),('harmonization',harmonization),('calendar',calendar),('seasonal-risk',season)]:write(outdir/f'{name}.json',obj)
 for y in years:write(outdir/f'hotspots-{y}.json',[r for r in records if r['date'].startswith(str(y))])
 (ROOT/'data/runtime').mkdir(parents=True,exist_ok=True);joblib.dump({'models':final,'history':panel,'selected_model':chosen,'report':report},ROOT/'data/runtime/model.joblib')
 fingerprint=hashlib.sha256(json.dumps({'files':[(m['file'],m['sha256']) for m in manifest],'source':report['source_hash']},sort_keys=True).encode()).hexdigest()[:16]
 version_dir=ROOT/'data/processed'/fingerprint
 if not version_dir.exists():
  version_dir.mkdir(parents=True)
  for path in outdir.glob('*.json'):shutil.copy2(path,version_dir/path.name)
  for path in outdir.glob('*.geojson'):shutil.copy2(path,version_dir/path.name)
 write(outdir/'processed-version.json',{'version':fingerprint,'source_hash':report['source_hash'],'data_manifest':manifest})
 print(json.dumps({'selected_model':chosen,'results':results,'records':len(records),'cells':len(meta)},indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw');a=p.parse_args();run(a.raw_dir)
