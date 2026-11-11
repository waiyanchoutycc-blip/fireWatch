#!/usr/bin/env python3
"""Download authentic NASA FIRMS, NASA POWER and licensed Bago admin boundary.

Usage: python scripts/acquire_sources.py [--start-year 2015] [--end-year 2025]
No external Python packages or NASA API keys are required. NASA country archives
contain positive detections only: they are not observation-coverage masks.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
PUBLIC = ROOT / 'public' / 'data'


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def retrieve(url: str, retries=3):
    error = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={'User-Agent': 'BagoYomaFireWatch-Research/1.0'})
            with urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise ValueError(f'Unexpected HTTP status: {response.status}')
                return response.read()
        except Exception as exc:
            error = exc
            if attempt < retries - 1:
                time.sleep(2 + attempt)
    raise RuntimeError(f'Download failed: {url}: {error}')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def get_firms(sensor, year):
    name = f'{sensor}_{year}_Myanmar.csv'
    path = RAW / name
    url = f'https://firms.modaps.eosdis.nasa.gov/data/country/{sensor}/{year}/{name}'
    item = {'source': 'NASA FIRMS yearly country archive', 'sensor': sensor,
            'year': year, 'url': url, 'file': name, 'country': 'Myanmar',
            'acquired_at': utcnow()}
    try:
        blob = path.read_bytes() if path.exists() else retrieve(url)
        if not blob.startswith(b'latitude,longitude,'):
            raise ValueError('Response is not a FIRMS CSV; no data saved')
        reader = csv.DictReader(io.StringIO(blob.decode('utf-8-sig')))
        count, minimum, maximum = 0, None, None
        for row in reader:
            count += 1
            date = row.get('acq_date')
            minimum = min(minimum, date) if minimum else date
            maximum = max(maximum, date) if maximum else date
        if not count:
            raise ValueError('Empty country archive')
        if not path.exists():
            path.write_bytes(blob)
        item.update(status='downloaded', bytes=len(blob),
                    sha256=hashlib.sha256(blob).hexdigest(), rows=count,
                    min_date=minimum, max_date=maximum, fields=reader.fieldnames)
    except Exception as exc:
        item.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    print(json.dumps({k: v for k, v in item.items() if k in
                      ['sensor', 'year', 'status', 'rows', 'bytes', 'error']}), flush=True)
    return item


def get_power(start_year, end_year):
    name = f'power_monthly_{start_year}_{end_year}_95.9_18.5.json'
    path = RAW / name
    url = ('https://power.larc.nasa.gov/api/temporal/monthly/point?'
           'parameters=T2M,PRECTOTCORR&community=AG&longitude=95.9&latitude=18.5'
           f'&start={start_year}&end={end_year}&format=JSON')
    blob = path.read_bytes() if path.exists() else retrieve(url)
    data = json.loads(blob)
    if not data.get('properties', {}).get('parameter', {}).get('T2M'):
        raise ValueError('NASA POWER response contains no temperature series')
    if not path.exists():
        path.write_bytes(blob)
    months = [k for k in data['properties']['parameter']['T2M'] if int(k[-2:]) <= 12]
    write_json(RAW / 'power_manifest.json', {
        'source': 'NASA POWER / MERRA-2', 'url': url, 'file': name,
        'sha256': hashlib.sha256(blob).hexdigest(), 'acquired_at': utcnow(),
        'status': 'downloaded', 'coordinate': [95.9, 18.5],
        'spatial_resolution_degrees': [0.625, 0.5], 'parameters': data['parameters'],
        'months': len(months), 'api_header': data['header'],
        'note': 'One coarse-grid regional context series. YYYY13 values are annual '
                'and must be excluded from monthly features. Not local 5 km climate.'})
    write_json(PUBLIC / 'power-manifest.json', json.loads((RAW / 'power_manifest.json').read_text()))
    params=data['properties']['parameter']
    write_json(PUBLIC / 'climate.json', [{'month':k[:4]+'-'+k[4:], 'temperature':params['T2M'][k] if params['T2M'][k]!=-999 else None, 'precipitation':params['PRECTOTCORR'][k] if params['PRECTOTCORR'][k]!=-999 else None} for k in sorted(months)])
    print(f'NASA POWER: {len(months)} months per variable saved', flush=True)


def get_boundary():
    api = 'https://www.geoboundaries.org/api/current/gbOpen/MMR/ADM1/'
    metadata_path = PUBLIC / 'bago-admin-source.json'
    # Keep the original version on reruns; delete metadata explicitly to update.
    meta = json.loads(metadata_path.read_text()) if metadata_path.exists() else json.loads(retrieve(api))
    data = json.loads(retrieve(meta['gjDownloadURL']))
    features = [f for f in data['features'] if f.get('properties', {}).get('shapeName', '').lower() == 'bago']
    if not features:
        raise ValueError('No Bago administrative feature in the boundary source')
    for feature in features:
        feature['properties'].update({
            'source': 'geoBoundaries gbOpen / Myanmar Analytics Project',
            'source_url': meta['gjDownloadURL'], 'version': meta['boundaryID'],
            'year_represented': meta['boundaryYearRepresented'],
            'license': meta['boundaryLicense'],
            'boundary_kind': 'Administrative boundary; not Bago Yoma forest boundary'})
    write_json(PUBLIC / 'bago-admin.geojson', {'type': 'FeatureCollection', 'features': features})
    write_json(metadata_path, meta)
    print('Bago administrative boundary saved; licence: ' + meta['boundaryLicense'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2025)
    args = parser.parse_args()
    if args.end_year < args.start_year:
        parser.error('end-year must be >= start-year')
    RAW.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    entries = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(get_firms, sensor, year)
                for sensor in ['modis', 'viirs-snpp']
                for year in range(args.start_year, args.end_year + 1)]
        for job in as_completed(jobs):
            entries.append(job.result())
            write_json(RAW / 'acquisition_manifest.json', {
                'source': 'NASA FIRMS', 'created_at': utcnow(),
                'entries': sorted(entries, key=lambda x: (x['sensor'], x['year']))})
    write_json(PUBLIC / 'acquisition-manifest.json', json.loads((RAW / 'acquisition_manifest.json').read_text()))
    failures = [x for x in entries if x['status'] != 'downloaded']
    print('FIRMS TOTAL', sum(x.get('rows', 0) for x in entries),
          'downloaded', len(entries) - len(failures), 'failed', len(failures), flush=True)
    for label, action in [('POWER', lambda: get_power(args.start_year, args.end_year)),
                          ('boundary', get_boundary)]:
        try:
            action()
        except Exception as exc:
            failures.append({'source': label, 'error': str(exc)})
            print(f'{label} failed: {exc}', flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
