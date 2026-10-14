"""Build a standalone provisional notebook without changing the running scan."""
from pathlib import Path
import base64
import gzip
import io
import json
import random
import sqlite3
import time
from datetime import datetime, timezone
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect((ROOT / 'data/processed/automotive_us_2019.sqlite').as_uri() + '?mode=ro', uri=True, timeout=10)
cap = connection.execute('SELECT MAX(rowid) FROM listings').fetchone()[0]
ids = sorted(random.Random(6182019).sample(range(1, cap + 1), min(100000, cap)))
records = []
for start in range(0, len(ids), 500):
    batch = ids[start:start+500]
    for retry in range(20):
        try:
            result = connection.execute('SELECT rowid,payload FROM listings WHERE rowid IN (' + ','.join('?'*len(batch)) + ')', batch).fetchall()
            break
        except sqlite3.OperationalError:
            time.sleep(.2)
    records.extend((index, json.loads(payload)) for index,payload in result)
connection.close()
records.sort(key=lambda item:item[0])
vehicles = pd.DataFrame([row for _,row in records])
buffer=io.BytesIO();vehicles.to_parquet(buffer,index=False,compression='zstd')
vehicle_bytes=buffer.getvalue()
(OUT/'vehicles_partial_100k.parquet').write_bytes(vehicle_bytes)
def encode(data):return base64.b64encode(gzip.compress(data)).decode()
provenance={'status':'PROVISIONAL — subset of an incomplete source scan, not a national random sample',
            'seed':6182019,'committed_rowid_cap':cap,'snapshot_rows':len(vehicles),
            'selection':'uniform sample of committed SQLite row IDs <= cap; no deletes observed; concurrent updates may occur during read',
            'extracted_at_utc':datetime.now(timezone.utc).isoformat(),'parquet_sha256':hashlib.sha256(vehicle_bytes).hexdigest(),
            'full_source_rows':'Unknown until the original scan finishes','full_source_bytes':49526352322}
(OUT/'snapshot_metadata.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
prep=(ROOT/'scripts/sample_automotive.py').read_text(encoding='utf-8')
rq=(ROOT/'docs/research_questions.md').read_text(encoding='utf-8').split('## Notebook workflow')[0]
data={'vehicles':encode(vehicle_bytes),'hd':encode((ROOT/'data/raw/ipeds_2019/hd2019.csv').read_bytes()),
      'ef':encode((ROOT/'data/raw/ipeds_2019/ef2019a_rv.csv').read_bytes()),'provenance':provenance}
cells=[]
def cell(code):cells.append('@app.cell\ndef _('+code[0]+'):\n'+''.join('    '+line+'\n' if line else '\n' for line in code[1].splitlines())+'\n')
cell(('', '''import marimo as mo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import BallTree
import base64, gzip, io, json
return mo, pd, np, plt, BallTree, base64, gzip, io, json'''))
cell(('mo', '''mo.md("""# Title and group
# Student Composition, College Density, and Nearby Used-Car Markets in the United States
**Group:** Team 8  
**Members:** [Add each member's name and uniqname before submission.]

**PROVISIONAL VERSION.** This notebook uses a reproducible subset of an incomplete automotive extraction. It is suitable for developing and checking the workflow, but does not support claims about the complete national market. Replace the vehicle input with the completed random sample and rerun before finalizing findings. Embedded inputs make this version runnable without the original 49.53 GB JSON.
""")
return'''))
cell(('mo', '''mo.md("""## Overview
This project describes associations between university student composition, local college density, and nearby used-car listing supply. IPEDS provides student counts and institutional locations, while automotive listings provide brands, body styles, model years, and coordinates. Combining them lets us compare nearby markets across institutions with different international and graduate student shares, and examine whether Japanese-brand shares differ with college density. Neither source can provide these comparisons alone. The observations concern advertised supply, not completed sales or students' individual purchases. Campus neighborhoods may overlap, and the provisional vehicle input has incomplete geographic and temporal coverage.
""")
return'''))
cell(('mo', 'mo.md('+repr('## Research questions\n\n'+rq.split('\n',2)[2])+')\nreturn'))
cell(('mo', '''mo.md("""## Data sources
| Dataset | Publisher | Source | Download date | License / terms | Role |
|---|---|---|---|---|---|
| HD2019: institution directory | NCES / IPEDS | [HD2019 ZIP](https://nces.ed.gov/ipeds/datacenter/data/HD2019.zip) | 2026-10-14 | Public-use data; no separate file license recorded | UNITID, state, institutional characteristics, latitude and longitude |
| EF2019A: Fall 2019 enrollment, revised file | NCES / IPEDS | [EF2019A ZIP](https://nces.ed.gov/ipeds/datacenter/data/EF2019A.zip) | 2026-10-14 | Public-use data; no separate file license recorded | Student totals by UNITID and EFALEVEL |
| 1.5 years Automotive Classified from 2019–2010, version 1 | winddude / Kaggle | [Dataset](https://www.kaggle.com/datasets/winddude/15-years-automotive-classified-from-20192010) | 2026-10-14 | Kaggle reports “Other (specified in description)”; exact description terms remain to be verified | Used-car listing attributes and coordinates |

HD and EF are matched on the institution identifier **UNITID**. Listings do not share that identifier: we match them to institutional coordinates using great-circle distance. The main radius is provisionally 10 miles, with a 5-mile alternative. The 2019 enrollment data are combined with listings whose original local posting timestamp falls in 2019. The notebook embeds the complete downloaded HD2019 and revised EF2019A tables, but only the provisional vehicle subset. The brand list and full extraction code appear below; classifications still require review.
""")
return'''))
cell(('base64,gzip,io,json,pd', 'embedded_inputs = '+repr(data)+'\n'+'''def decode_input(encoded):
    return io.BytesIO(gzip.decompress(base64.b64decode(encoded)))
hd_raw = pd.read_csv(decode_input(embedded_inputs['hd']),encoding='cp1252',low_memory=False)
ef_raw = pd.read_csv(decode_input(embedded_inputs['ef']),encoding='cp1252',low_memory=False)
vehicles_raw = pd.read_parquet(decode_input(embedded_inputs['vehicles']))
provenance = embedded_inputs['provenance']
return hd_raw, ef_raw, vehicles_raw, provenance'''))
cell(('mo,hd_raw,ef_raw,vehicles_raw,merged,pd,provenance', '''mo.md(f"""## Data description
The original automotive JSON contains **{provenance['full_source_bytes']:,} bytes**; its full row count and raw-field missingness are not yet known. The provisional vehicle input already passed the extraction filters shown below. Consequently its missingness must not be described as the original full JSON's missingness. The snapshot was read at {provenance['extracted_at_utc']} from committed row IDs up to {provenance['committed_rowid_cap']:,}.
""")
shape_table = pd.DataFrame([
    {'dataset':'HD2019 before merge','rows':len(hd_raw),'columns':hd_raw.shape[1],'one_row':'IPEDS institution'},
    {'dataset':'EF2019A revised before merge','rows':len(ef_raw),'columns':ef_raw.shape[1],'one_row':'Institution × student enrollment level'},
    {'dataset':'Provisional vehicle input before spatial merge','rows':len(vehicles_raw),'columns':vehicles_raw.shape[1],'one_row':'Unique eligible listing in the processed prefix subset'},
    {'dataset':'Merged main table','rows':len(merged),'columns':merged.shape[1],'one_row':'Selected university with student composition and 10-mile market summaries'}])
mo.ui.table(shape_table,selection=None)
return shape_table,'''))
cell(('mo,pd,hd_raw,ef_raw,vehicles_raw,merged', '''def variable_description(table,label,columns,units):
    return pd.DataFrame([{'dataset':label,'variable':c,'dtype':str(table[c].dtype),'unit':units.get(c,'0–1 share' if 'share' in c else 'count' if c.startswith('n_') or c.endswith('_count') else 'category'), 'missing_count':int(table[c].isna().sum()),'missing_share':float(table[c].isna().mean())} for c in columns])
_hd = hd_raw.rename(columns=lambda c:c.strip())
_ef = ef_raw.rename(columns=lambda c:c.strip())
variable_table = pd.concat([
    variable_description(_hd,'HD2019',['UNITID','LATITUDE','LONGITUD','ICLEVEL','DEGGRANT'],{'UNITID':'identifier','LATITUDE':'degrees','LONGITUD':'degrees'}),
    variable_description(_ef,'EF2019A revised',['UNITID','EFALEVEL','EFTOTLT','EFTOTLW','EFNRALT'],{'UNITID':'identifier','EFALEVEL':'enrollment category','EFTOTLT':'students','EFTOTLW':'students','EFNRALT':'students'}),
    variable_description(vehicles_raw,'Provisional listings',['listing_key','latitude','longitude','manufacturer','body_style','model_year','vehicle_age','is_japanese_brand'],{'listing_key':'identifier','latitude':'degrees','longitude':'degrees','model_year':'model year','vehicle_age':'years','is_japanese_brand':'boolean'}),
    variable_description(merged,'Merged table',[c for c in merged if c in ['unitid','international_student_share','graduate_student_share','nearby_college_count','college_density_per_sq_mile','japanese_brand_share','vehicle_age_median','vehicle_age_q25','vehicle_age_q75','n_known_brand','n_known_body_style','n_known_vehicle_age'] or c.startswith(('brand_share_','body_style_share_'))],{'unitid':'identifier','college_density_per_sq_mile':'institutions per nominal square mile','vehicle_age_median':'years','vehicle_age_q25':'years','vehicle_age_q75':'years'})],ignore_index=True)
mo.ui.table(variable_table,selection=None,page_size=20)
return variable_table,'''))
cell(('mo', '''mo.md("""## Data manipulation
The embedded vehicle input was extracted by the complete script below. It filters explicit US listings, valid 2019 posting dates, valid coordinates and listing identity, flattens fields, and deduplicates by canonical URL (falling back to record ID), retaining the latest eligible capture. Images and description fields are omitted. Unknown attributes remain missing. Exact raw-stage losses for the unfinished full scan are unavailable and are not fabricated here.

**Reconstruction:** save the complete script below as `scripts/sample_automotive.py`; with the original JSON available, run `python scripts/sample_automotive.py --sample-size 500000 --seed 6182019`. This expensive extraction is deliberately not triggered by opening the notebook. The current embedded data were sampled from the already-committed partial intermediate, not from the complete source.
""")
return'''))
cell(('mo', 'complete_extraction_script = '+repr(prep)+'\nmo.accordion({"Complete original extraction, cleaning, deduplication, and reservoir-sampling script":mo.md("```python\\n"+complete_extraction_script+"\\n```")})\nreturn complete_extraction_script,'))
cell(('pd,np,hd_raw,ef_raw,vehicles_raw,BallTree', '''hd = hd_raw.rename(columns=lambda c:c.strip()).copy()
ef = ef_raw.rename(columns=lambda c:c.strip()).copy()
hd['ACT'] = hd['ACT'].astype('string').str.strip()
us_states = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
school_audit = [{'step':'HD original','rows':len(hd)}]
college_candidates = hd[hd.STABBR.isin(us_states)].copy()
school_audit.append({'step':'US 50 states and DC','rows':len(college_candidates)})
college_candidates = college_candidates[college_candidates.ICLEVEL.eq(1)&college_candidates.DEGGRANT.eq(1)]
school_audit.append({'step':'Four-year degree-granting','rows':len(college_candidates)})
college_candidates = college_candidates[college_candidates.ACT.isin(['A','N','R'])].copy()
school_audit.append({'step':'Active/new/restored institutions','rows':len(college_candidates)})
assert not hd.UNITID.duplicated().any()
assert not ef.duplicated(['UNITID','EFALEVEL']).any()
_tot = ef[ef.EFALEVEL.eq(1)][['UNITID','EFTOTLT','EFTOTLW','EFNRALT']]
_ug = ef[ef.EFALEVEL.eq(2)][['UNITID','EFTOTLT']].rename(columns={'EFTOTLT':'undergraduate_students'})
_gr = ef[ef.EFALEVEL.eq(12)][['UNITID','EFTOTLT']].rename(columns={'EFTOTLT':'graduate_students'})
college_candidates = college_candidates.merge(_tot,on='UNITID',how='left',validate='one_to_one',indicator=True)
enrollment_match_counts = college_candidates['_merge'].value_counts().rename_axis('status').reset_index(name='institutions')
college_candidates = college_candidates.merge(_ug,on='UNITID',how='left',validate='one_to_one').merge(_gr,on='UNITID',how='left',validate='one_to_one')
_infer_zero = college_candidates.graduate_students.isna() & college_candidates.undergraduate_students.eq(college_candidates.EFTOTLT) & college_candidates.EFTOTLT.notna()
college_candidates.loc[_infer_zero,'graduate_students'] = 0
inferred_zero_graduate_count = int(_infer_zero.sum())
colleges = college_candidates[college_candidates.EFTOTLT.gt(0)&college_candidates.LATITUDE.between(-90,90)&college_candidates.LONGITUD.between(-180,180)].copy()
school_audit.append({'step':'Positive reported enrollment and valid coordinates','rows':len(colleges)})
colleges = colleges.rename(columns={'UNITID':'unitid','INSTNM':'institution_name','STABBR':'state_code','LATITUDE':'latitude','LONGITUD':'longitude','EFTOTLT':'total_students','EFNRALT':'international_students','EFTOTLW':'female_students'})
colleges['international_student_share'] = colleges.international_students/colleges.total_students
colleges['graduate_student_share'] = colleges.graduate_students/colleges.total_students
vehicles = vehicles_raw.drop_duplicates('listing_key').copy()
vehicles = vehicles[vehicles.country.eq('US')&vehicles.posting_year.eq(2019)&vehicles.latitude.between(-90,90)&vehicles.longitude.between(-180,180)].reset_index(drop=True)
vehicle_audit = pd.DataFrame([{'step':'Embedded partial sample','rows':len(vehicles_raw)},{'step':'Listing-key deduplication','rows':len(vehicles_raw.drop_duplicates('listing_key'))},{'step':'Revalidated US/year/coordinates','rows':len(vehicles)}])
earth_miles = 3958.7613
vehicle_tree = BallTree(np.radians(vehicles[['latitude','longitude']].to_numpy(dtype=float)),metric='haversine')
college_points = np.radians(colleges[['latitude','longitude']].to_numpy(dtype=float))
college_tree = BallTree(college_points,metric='haversine')
def link_radius(radius):
    neighbors,distances = vehicle_tree.query_radius(college_points,r=radius/earth_miles,return_distance=True)
    lengths = np.array([len(n) for n in neighbors])
    return pd.DataFrame({'unitid':np.repeat(colleges.unitid.to_numpy(),lengths),'vehicle_index':np.concatenate(neighbors).astype(int),'distance_miles':np.concatenate(distances)*earth_miles})
def summarize_radius(radius,listing_frame=None):
    pairs = link_radius(radius)
    nearby = pairs.merge(vehicles.reset_index().rename(columns={'index':'vehicle_index'}),on='vehicle_index',validate='many_to_one')
    if listing_frame is not None:
        nearby = nearby[nearby.listing_key.isin(listing_frame.listing_key)]
    counts = nearby.groupby('unitid').agg(n_listings=('listing_key','size'),n_known_brand=('manufacturer','count'),n_known_body_style=('body_style','count'),n_known_vehicle_age=('vehicle_age','count'),vehicle_age_median=('vehicle_age','median'),vehicle_age_q25=('vehicle_age',lambda x:x.quantile(.25)),vehicle_age_q75=('vehicle_age',lambda x:x.quantile(.75)))
    jp = nearby.assign(japanese=nearby.is_japanese_brand.fillna(False).astype(int)).groupby('unitid').japanese.sum()
    counts['n_japanese_brand']=jp
    counts['japanese_brand_share']=counts.n_japanese_brand/counts.n_known_brand.replace(0,np.nan)
    for column,prefix,denominator in [('manufacturer','brand_share_','n_known_brand'),('body_style','body_style_share_','n_known_body_style')]:
        distribution=nearby.groupby(['unitid',column]).size().unstack(fill_value=0)
        counts=counts.join(distribution.div(counts[denominator].replace(0,np.nan),axis=0).add_prefix(prefix))
    result = colleges[['unitid','institution_name','state_code','latitude','longitude','total_students','international_students','graduate_students','international_student_share','graduate_student_share']].merge(counts.reset_index(),on='unitid',how='left',validate='one_to_one')
    count_columns=[c for c in result if c.startswith('n_')]
    result[count_columns]=result[count_columns].fillna(0).astype(int)
    result['nearby_college_count']=college_tree.query_radius(college_points,r=radius/earth_miles,count_only=True)
    result['college_density_per_sq_mile']=result.nearby_college_count/(np.pi*radius**2)
    result['radius_miles']=radius
    return result,nearby
merged, listing_links = summarize_radius(10)
alternative_5mi, links_5mi = summarize_radius(5)
complete_listings = vehicles.dropna(subset=['manufacturer','body_style','vehicle_age'])
complete_case_market,_ = summarize_radius(10,complete_listings)
school_audit=pd.DataFrame(school_audit)
return colleges,vehicles,merged,listing_links,alternative_5mi,links_5mi,complete_case_market,complete_listings,school_audit,vehicle_audit,enrollment_match_counts,inferred_zero_graduate_count'''))
cell(('mo,school_audit,vehicle_audit,enrollment_match_counts,merged,listing_links,vehicles,inferred_zero_graduate_count,pd', '''mo.vstack([mo.md("### Cleaning and enrollment merge audit"),mo.ui.table(school_audit,selection=None),mo.ui.table(vehicle_audit,selection=None),mo.ui.table(enrollment_match_counts,selection=None)])
spatial_audit=pd.DataFrame([{'measure':'Universities with at least one nearby listing','count':int(merged.n_listings.gt(0).sum())},{'measure':'Universities with no nearby listing','count':int(merged.n_listings.eq(0).sum())},{'measure':'Distinct vehicle listings matched','count':listing_links.listing_key.nunique()},{'measure':'Vehicle listings unmatched','count':len(vehicles)-listing_links.listing_key.nunique()},{'measure':'University–listing pairs','count':len(listing_links)},{'measure':'Listings shared by multiple universities','count':int(listing_links.groupby('listing_key').unitid.nunique().gt(1).sum())}])
mo.vstack([mo.md(f"### Spatial matching audit\nGraduate count was inferred as zero for {inferred_zero_graduate_count:,} institutions only when undergraduate enrollment equals total enrollment. Other missing graduate counts remain unknown. No nearby listings means a zero listing count but missing market shares/ages."),mo.ui.table(spatial_audit,selection=None),mo.ui.table(merged,selection=None,page_size=10)])
return spatial_audit,'''))
cell(('mo', '''mo.md("""## Data visualisation
All figures below describe this provisional merged table. They are not statistical tests. For brand/body-style composition figures, the plotted value is the mean university-level share, so large listing markets do not automatically dominate. Neighborhoods can overlap. Minimum 10 known observations is a provisional display threshold; schools excluded from a figure remain in the merged table.
""")
return'''))
cell(('mo,pd,np,plt,merged', '''plot_data=merged.copy()
plot_data['international_group']=pd.qcut(plot_data.international_student_share.rank(method='first'),4,labels=['Q1 lowest','Q2','Q3','Q4 highest'])
plot_data['graduate_group']=pd.qcut(plot_data.graduate_student_share.rank(method='first'),4,labels=['Q1 lowest','Q2','Q3','Q4 highest'])
brand_cols=[c for c in merged if c.startswith('brand_share_')]
top_brands=merged[brand_cols].mean().nlargest(6).index.tolist()
rq1_data=plot_data[plot_data.n_known_brand.ge(10)]
brand_plot=rq1_data.groupby('international_group',observed=True)[top_brands].mean().rename(columns=lambda x:x.replace('brand_share_',''))
fig_brand,ax_brand=plt.subplots(figsize=(10,4.5))
brand_plot.plot.bar(ax=ax_brand)
ax_brand.set(title='RQ1: Nearby brand shares by international student share',xlabel='International student share quartile',ylabel='Mean university-level brand share')
ax_brand.tick_params(axis='x',rotation=0);ax_brand.legend(title='Brand',bbox_to_anchor=(1.02,1));fig_brand.tight_layout()
mo.vstack([mo.as_html(fig_brand),mo.md(f"This figure compares six commonly identified brands across international-student-share quartiles using {len(rq1_data):,} universities with at least 10 known-brand listings. The displayed mean shares span {brand_plot.min().min():.1%} to {brand_plot.max().max():.1%}; differences are descriptive and may reflect partial-source coverage, vehicle prices, or geography rather than student preferences.")])
return plot_data,fig_brand'''))
cell(('mo,plt,plot_data', '''_body_columns=[c for c in plot_data if c.startswith('body_style_share_')]
_body_top=plot_data[_body_columns].mean().nlargest(5).index.tolist()
_body_data=plot_data[plot_data.n_known_body_style.ge(10)]
_body_summary=_body_data.groupby('graduate_group',observed=True)[_body_top].mean().rename(columns=lambda x:x.replace('body_style_share_',''))
fig_body,_ax=plt.subplots(figsize=(10,4.5))
_body_summary.plot.bar(ax=_ax)
_ax.set(title='RQ2: Nearby body styles by graduate student share',xlabel='Graduate student share quartile',ylabel='Mean university-level body-style share')
_ax.tick_params(axis='x',rotation=0);_ax.legend(title='Body style',bbox_to_anchor=(1.02,1));fig_body.tight_layout()
mo.vstack([mo.as_html(fig_body),mo.md(f"The figure compares body-style compositions across graduate-share quartiles for {len(_body_data):,} universities. Only five common categories are shown, so their shares need not sum to one. Unknown body styles are excluded from the denominator and their coverage is reported above.")])
return fig_body,'''))
cell(('mo,plt,plot_data,pd', '''_age_data=plot_data[plot_data.n_known_vehicle_age.ge(10)&plot_data.graduate_group.notna()]
_age_groups=[_age_data.loc[_age_data.graduate_group.eq(label),'vehicle_age_median'].dropna().to_numpy() for label in ['Q1 lowest','Q2','Q3','Q4 highest']]
fig_age,_ax=plt.subplots(figsize=(9,4.5))
_ax.boxplot(_age_groups,labels=['Q1 lowest','Q2','Q3','Q4 highest'])
_ax.set(title='RQ2: University market median vehicle ages',xlabel='Graduate student share quartile',ylabel='University-level median vehicle age (years)');fig_age.tight_layout()
age_summary=_age_data.groupby('graduate_group',observed=True)[['vehicle_age_median','vehicle_age_q25','vehicle_age_q75']].median()
mo.vstack([mo.as_html(fig_age),mo.ui.table(age_summary.reset_index(),selection=None),mo.md(f"This plot shows variation in market median age across {len(_age_data):,} universities, rather than the age of every individual vehicle. The accompanying table also shows typical within-market quartiles. Use both when describing age distributions; a full-sample rerun is needed before interpreting group differences.")])
return fig_age,age_summary'''))
cell(('mo,plt,merged', '''_density_data=merged[merged.n_known_brand.ge(10)].dropna(subset=['japanese_brand_share'])
fig_density,_ax=plt.subplots(figsize=(9,4.5))
_points=_ax.scatter(_density_data.nearby_college_count,_density_data.japanese_brand_share,s=14,alpha=.4,c=_density_data.n_known_brand,cmap='viridis')
_ax.set(title='RQ3: College density and nearby Japanese-brand share',xlabel='Number of selected universities within 10 miles (including focal university)',ylabel='Japanese-brand share among known-brand listings')
fig_density.colorbar(_points,ax=_ax,label='Known-brand listings');fig_density.tight_layout()
mo.vstack([mo.as_html(fig_density),mo.md(f"Each point is one of {len(_density_data):,} university neighborhoods. Nearby college counts range from {int(_density_data.nearby_college_count.min())} to {int(_density_data.nearby_college_count.max())}; Japanese-brand shares range from {_density_data.japanese_brand_share.min():.1%} to {_density_data.japanese_brand_share.max():.1%}. A consistent upward pattern would support RQ3. This provisional plot does not establish such a relationship or a causal explanation.")])
return fig_density,'''))
cell(('mo,merged,alternative_5mi,complete_case_market,complete_listings,vehicles,pd', '''radius_comparison=pd.DataFrame([{'radius_miles':5,'universities_with_listings':int(alternative_5mi.n_listings.gt(0).sum()),'university_listing_pairs':int(alternative_5mi.n_listings.sum())},{'radius_miles':10,'universities_with_listings':int(merged.n_listings.gt(0).sum()),'university_listing_pairs':int(merged.n_listings.sum())}])
_paired=merged[['unitid','japanese_brand_share']].merge(alternative_5mi[['unitid','japanese_brand_share']],on='unitid',suffixes=('_10','_5')).dropna()
_radius_change=(_paired.japanese_brand_share_10-_paired.japanese_brand_share_5).abs().median()
_matched=merged.n_listings.gt(0)
mo.md(f"""## Decision log
These are provisional processing decisions for the current workflow; the team should review them after the completed-sample rerun.

### 1. Neighborhood radius
**Decision:** Use a 10-mile neighborhood for the main descriptive table.  
**Alternative:** Use a 5-mile neighborhood.  
**Evidence:** The code actually runs both radii. The 10-mile rule matches {_matched.sum():,} universities, versus {alternative_5mi.n_listings.gt(0).sum():,} at 5 miles.  
**Consequence:** Among {len(_paired):,} universities with identifiable brand data at both radii, the median absolute change in Japanese-brand share is {_radius_change:.2%}. This demonstrates sensitivity in the provisional input; it does not prove 10 miles is the uniquely correct definition.

### 2. Attribute missingness
**Decision:** Retain listings with missing brand, body style, or age and use a separate known-field denominator for each measure.  
**Alternative:** Require all three fields to be available.  
**Evidence:** {len(complete_listings):,} of {len(vehicles):,} input listings satisfy the complete-case rule. The spatial summary is actually recomputed with those records.  
**Consequence:** Complete-case filtering changes matched university coverage from {_matched.sum():,} to {complete_case_market.n_listings.gt(0).sum():,}. It excludes {len(vehicles)-len(complete_listings):,} listings that may still inform one or two of the research questions.

### 3. Unmatched universities
**Decision:** Keep the selected university universe in a left join; show zero listing counts and missing market characteristics for unmatched universities.  
**Alternative:** Retain only universities with a matched listing (an inner-join analysis table).  
**Evidence:** {int((~_matched).sum()):,} of {len(merged):,} universities have no matched provisional listing.  
**Consequence:** The alternative removes those universities. Mean international student share is {merged.international_student_share.mean():.2%} in the retained universe and {merged.loc[_matched,'international_student_share'].mean():.2%} among matched universities. A missing market in this partial sample must not be interpreted as absence of a real local market.
""")
mo.ui.table(radius_comparison,selection=None)
return radius_comparison,'''))
content='# /// script\n# requires-python = ">=3.12"\n# dependencies = ["marimo", "pandas", "numpy", "matplotlib", "scikit-learn", "pyarrow"]\n# ///\n\nimport marimo\n\n__generated_with = "0.23.0"\napp = marimo.App(width="medium")\n\n'+''.join(cells)+'\nif __name__ == "__main__":\n    app.run()\n'
destination=ROOT/'SI618_M1_team8_provisional.py'
destination.write_text(content,encoding='utf-8')
print('Notebook saved:',destination,'bytes',destination.stat().st_size,flush=True)
print('Snapshot:',json.dumps(provenance),flush=True)
