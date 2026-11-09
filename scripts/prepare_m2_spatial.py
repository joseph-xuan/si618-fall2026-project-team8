"""Reproduce the nonstatistical geographic lookup used by SI618_M2_Team8.py.

Run from the team repository with Python 3.12+ and:
  uv run --with pandas --with numpy --with pyarrow --with shapely --with pyshp \
    --with xlrd --with scikit-learn python scripts/prepare_m2_spatial.py

The output is plain compressed JSON, never executable serialized Python.
"""
from pathlib import Path
from urllib.request import urlopen
import argparse
import base64
import hashlib
import io
import json
import logging
import zlib

import numpy as np
import pandas as pd
import shapefile
import shapely
from shapely.strtree import STRtree
from sklearn.neighbors import BallTree

URLS = {
    'tl_2019_us_county.zip':'https://www2.census.gov/geo/tiger/TIGER2019/COUNTY/tl_2019_us_county.zip',
    'list1_Sep_2018.xls':'https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2018/delineation-files/list1_Sep_2018.xls',
    'co-est2019-alldata.csv':'https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv',
}
STATE_FIPS = set('01 04 05 06 08 09 10 11 12 13 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56'.split())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assign(frame,longitude,latitude,tree):
    coordinates=frame[[longitude,latitude]].to_numpy(dtype=float)
    points,inverse=np.unique(coordinates,axis=0,return_inverse=True)
    pairs=tree.query(shapely.points(points),predicate='intersects')
    pairs=pairs[:,np.lexsort((pairs[1],pairs[0]))]
    first=np.r_[True,np.diff(pairs[0])!=0]
    unique_pairs=pairs[:,first]
    codes=np.full(len(points),-1,dtype='<i2')
    codes[unique_pairs[0]]=unique_pairs[1]
    return codes[inverse],int(len(pairs[0])-len(unique_pairs[0]))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--cache',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    project=args.project.resolve()
    cache=args.cache or project/'data/raw/m2_geography'
    output=args.output or project/'data/processed/m2_spatial_lookup.json'
    cache.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,url in URLS.items():
        path=cache/name
        if not path.exists():
            with urlopen(url,timeout=180) as response,path.open('wb') as stream:
                while chunk:=response.read(1024*1024):
                    stream.write(chunk)
        manifest.append({'name':name,'url':url,'bytes':path.stat().st_size,'sha256':digest(path)})
    logging.getLogger('shapefile').setLevel(logging.ERROR)
    records,polygons=[],[]
    for item in shapefile.Reader(str(cache/'tl_2019_us_county.zip')).iterShapeRecords():
        row=item.record.as_dict()
        if row['STATEFP'] in STATE_FIPS:
            records.append({'county_id':row['GEOID'],'county_name':row['NAMELSAD'],
                'state_fips':row['STATEFP'],'land_sqmi':float(row['ALAND'])/2589988.110336})
            polygons.append(shapely.geometry.shape(item.shape.__geo_interface__))
    order=np.argsort([r['county_id'] for r in records])
    geo=pd.DataFrame([records[i] for i in order])
    tree=STRtree(np.array([polygons[i] for i in order],dtype=object))
    pop=pd.read_csv(cache/'co-est2019-alldata.csv',encoding='cp1252')
    pop=pop[pop.SUMLEV.eq(50)].copy()
    pop['county_id']=pop.STATE.astype(str).str.zfill(2)+pop.COUNTY.astype(str).str.zfill(3)
    geo=geo.merge(pop[['county_id','POPESTIMATE2019']],on='county_id',validate='one_to_one')
    cross=pd.read_excel(cache/'list1_Sep_2018.xls',header=2,dtype='string')
    cross=cross[pd.to_numeric(cross['CBSA Code'],errors='coerce').notna()].copy()
    cross['county_id']=cross['FIPS State Code'].str.zfill(2)+cross['FIPS County Code'].str.zfill(3)
    cross=cross.rename(columns={'CBSA Code':'cbsa_code','CBSA Title':'cbsa_title','Metropolitan/Micropolitan Statistical Area':'cbsa_type'})
    geo=geo.merge(cross[['county_id','cbsa_code','cbsa_title','cbsa_type']],on='county_id',how='left',validate='one_to_one')
    geo['region_id']=np.where(geo.cbsa_code.notna(),'CBSA_'+geo.cbsa_code.fillna(''),'OUT_'+geo.county_id)
    raw=pd.read_parquet(project/'data/processed/vehicles_us_2019_sample.parquet')
    assert raw.listing_key.is_unique and raw.country.eq('US').all() and raw.posting_year.eq(2019).all()
    vehicle_codes,boundaries=assign(raw,'longitude','latitude',tree)
    hd=pd.read_csv(project/'data/raw/ipeds_2019/hd2019.csv',encoding='cp1252',low_memory=False)
    selected=hd[hd.ACT.astype('string').str.strip().isin(['A','N','R']) & hd.ICLEVEL.eq(1) & hd.DEGGRANT.eq(1)
        & hd.LATITUDE.between(-90,90)&hd.LONGITUD.between(-180,180)
        & ~(hd.LATITUDE.eq(0)&hd.LONGITUD.eq(0))].copy()
    school_codes,_=assign(selected,'LONGITUD','LATITUDE',tree)
    schools=selected[school_codes>=0].copy()
    reported=pd.to_numeric(schools.COUNTYCD).astype(int).astype(str).str.zfill(5).to_numpy()
    assert np.array_equal(reported,geo.county_id.to_numpy()[school_codes[school_codes>=0]])
    retained=raw[vehicle_codes>=0]
    neighborhoods=BallTree(np.radians(retained[['latitude','longitude']].to_numpy()),metric='haversine').query_radius(
        np.radians(schools[['LATITUDE','LONGITUD']].to_numpy()),r=10/3958.7613)
    frequency=np.bincount(np.concatenate(neighborhoods),minlength=len(retained))
    audit={'vehicles_boundary_ties_unique_points':boundaries,'contiguous_colleges':len(schools),
        'contiguous_unique_listings':len(retained),'college_county_disagreements':0,
        'unmatched_vehicle_reported_states':raw.loc[vehicle_codes<0,'state_code'].fillna('MISSING').value_counts().to_dict(),
        'campus_10mile_overlap':{'unique_matched_listings':int((frequency>0).sum()),
            'multiply_matched_listings':int((frequency>1).sum()),
            'multiple_match_percent':float(100*(frequency>1).sum()/(frequency>0).sum()),
            'total_campus_listing_pairs':int(frequency.sum()),'max_campuses_per_listing':int(frequency.max())}}
    paths=['data/raw/ipeds_2019/hd2019.csv','data/raw/ipeds_2019/ef2019a_rv.csv',
        'data/processed/vehicles_us_2019_sample.parquet','outputs/automotive_sample_metadata.json']
    payload={'county_csv':base64.b85encode(zlib.compress(geo.to_csv(index=False).encode(),9)).decode(),
        'county_codes':base64.b85encode(zlib.compress(vehicle_codes.tobytes(),9)).decode(),
        'sources':{p:digest(project/p) for p in paths},'spatial_audit':audit,'geography_sources':manifest}
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        raise FileExistsError(f'Preserve the existing lookup or choose --output: {output}')
    output.write_text(json.dumps(payload,separators=(',',':')))
    print(json.dumps({'output':str(output),'counties':len(geo),'listings':len(raw),'audit':audit},indent=2))

if __name__=='__main__':
    main()
