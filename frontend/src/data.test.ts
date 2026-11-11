import{describe,it,expect}from'vitest';
import{parseCsv,validateAoi,inside,scenarioIndex,csv}from'./data';
import{keys,translate,Key}from'./i18n';
const header='latitude,longitude,acq_date,acq_time,instrument,confidence,satellite,version\n';
describe('data contracts',()=>{
 it('validates times and exact duplicates while keeping sensor provenance',()=>{const s='18.5,95.9,2024-03-01,530,MODIS,75,T,6.1';const d=parseCsv(header+s+'\n'+s+'\n18.5,95.9,2024-03-01,530,VIIRS,n,N,1','firms.csv');expect(d.rows).toHaveLength(2);expect(d.rejected).toBe(1);expect(d.rows[1].confidence).toBe('n');expect(d.rows[0].time).toBe('05:30')});
 it('rejects invalid dates, coordinates and incomplete schemas',()=>{expect(()=>parseCsv(header+'18.5,95.9,2024-02-30,530,MODIS,75,T,6.1','x')).toThrow();expect(()=>parseCsv(header+'95,95.9,2024-02-29,530,MODIS,75,T,6.1','x')).toThrow();expect(()=>parseCsv('x,y\n1,2','x')).toThrow()});
 it('rejects missing time and supersedes provisional duplicates',()=>{expect(()=>parseCsv(header+'18.5,95.9,2024-03-01,,MODIS,70,T,6.1','x')).toThrow();const d=parseCsv(header+'18.5,95.9,2024-03-01,530,MODIS,60,T,6.1NRT\n18.5,95.9,2024-03-01,530,MODIS,70,T,6.1','x');expect(d.rows).toHaveLength(1);expect(d.rows[0].version).toBe('6.1')});
 it('keeps a valid AOI and clips observations to it',()=>{const f=validateAoi({type:'Polygon',coordinates:[[[95,18],[96,18],[96,19],[95,19],[95,18]]]});expect(f.properties.status).toContain('User supplied');expect(inside({lon:95.5,lat:18.5}as any,f)).toBe(true);expect(inside({lon:97,lat:18.5}as any,f)).toBe(false);expect(()=>validateAoi({type:'Point',coordinates:[95,18]})).toThrow()});
 it('provides complete bilingual keys',()=>{for(const k of keys){expect(translate('en',k as Key).length).toBeGreaterThan(0);expect(translate('mm',k as Key).length).toBeGreaterThan(0)}});
 it('keeps scenario ranks bounded and monotone',()=>{const r={cell_id:'a',month:3,index:50,raw_proxy:.5,spread_low:20,spread_high:80};const ref=[.1,.2,.3,.4,.5,.6,.7,.8,.9];expect(scenarioIndex(r,'dry',ref)).toBeGreaterThanOrEqual(scenarioIndex(r,'wet',ref));expect(scenarioIndex(r,'baseline',ref)).toBe(50)});
 it('escapes formula injection in CSV exports and preserves Unicode',()=>{const text=csv([{source:'=HYPERLINK("bad")',heading:'မြန်မာ',sensor:'VIIRS'}]);expect(text).toContain("'=HYPERLINK");expect(text).toContain('မြန်မာ')});
});
