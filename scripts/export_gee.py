"""GEE export (not run in delivery). earthengine authenticate, then --project YOUR_PROJECT --year 2024."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 import ee
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--year',type=int,required=True);a=p.parse_args();ee.Initialize(project=a.project);cells=ee.FeatureCollection(json.loads((ROOT/'public/data/grid.geojson').read_text()))
 def export(fc,name):
  task=ee.batch.Export.table.toDrive(collection=fc,description=name,folder='FireWatch',fileFormat='CSV');task.start();print(name,task.id)
 dem=ee.Image('USGS/SRTMGL1_003').select('elevation');terrain=ee.Terrain.products(dem).select(['elevation','slope','aspect']);export(terrain.reduceRegions(collection=cells,reducer=ee.Reducer.mean(),scale=30,crs='EPSG:32647',tileScale=4),f'firewatch_terrain_{a.year}')
 lc=ee.Image(ee.ImageCollection('MODIS/061/MCD12Q1').filterDate(f'{a.year}-01-01',f'{a.year+1}-01-01').first()).select('LC_Type1');forest=lc.gte(1).And(lc.lte(5)).rename('forest_fraction');export(forest.reduceRegions(collection=cells,reducer=ee.Reducer.mean(),scale=500,crs='EPSG:32647',tileScale=4),f'firewatch_forest_{a.year}')
 for month in range(1,13):
  start=ee.Date.fromYMD(a.year,month,1);end=start.advance(1,'month')
  def masks(im):
   mask=im.select('FireMask').bitwiseAnd(15);valid=mask.eq(5).Or(mask.eq(7)).Or(mask.eq(8)).Or(mask.eq(9));fire=mask.gte(8).And(mask.lte(9));return valid.rename('valid_land_observations').addBands(fire.rename('nominal_high_fire_observations')).unmask(0)
  fire=ee.ImageCollection('MODIS/061/MOD14A1').filterDate(start,end).map(masks).sum();table=fire.reduceRegions(collection=cells,reducer=ee.Reducer.sum(),scale=1000,crs='EPSG:32647',tileScale=4).map(lambda f:f.set({'month':start.format('YYYY-MM'),'sensor':'MODIS_Terra','coverage_units':'valid pixel-days; not complete month coverage'}));export(table,f'firewatch_coverage_{a.year}_{month:02d}')
  def ndvi(im):return im.select('NDVI').multiply(.0001).updateMask(im.select('SummaryQA').lte(1))
  vegetation=ee.ImageCollection('MODIS/061/MOD13Q1').filterDate(start,end).map(ndvi).mean().rename('ndvi');table=vegetation.reduceRegions(collection=cells,reducer=ee.Reducer.mean(),scale=250,crs='EPSG:32647',tileScale=4).map(lambda f:f.set('month',start.format('YYYY-MM')));export(table,f'firewatch_ndvi_{a.year}_{month:02d}')
 print('Inspect Earth Engine Tasks and Google Drive. Validate coverage before changing labels. Never use target-month observed vegetation for a multiyear forecast.')
if __name__=='__main__':main()
