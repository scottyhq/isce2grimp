#!/usr/bin/env python3
'''
Download json inventory for ASF Sentinel-1 archive with greenland.geojson 

Usage: ./get_asf_inventory.py
'''

import requests
from datetime import date
import geopandas as gpd
import fiona
import os
from pathlib import Path

ROOTDIR = Path(__file__).parent.parent
INVENTORY = os.path.join(ROOTDIR, 'data', 'asf_inventory.gpkg')
TODAY = date.today()

print(f"Updating {INVENTORY} through {TODAY}")

def query_asf(
    sat="Sentinel-1",
    orbit=None,
    start=None,
    stop=None,
    beam="IW",
    flightDirection=None,
    outfile='query.json'
):
    """Search ASF API and return GeoJSON

    https://docs.asf.alaska.edu/api/basics/
    NOTE: 15 minute time limit on running Search API queries
    """
    print(f"Querying ASF Vertex between {start} and {stop}...")
    gf = gpd.read_file(os.path.join(ROOTDIR,'data','greenland.json'))
    polygonWKT = gf.geometry[0].wkt

    baseurl = "https://api.daac.asf.alaska.edu/services/search/param"
    # relativeOrbit=$ORBIT
    data = dict(
        intersectsWith=polygonWKT,
        platform=sat,
        processingLevel="SLC",
        beamMode=beam,
        output='geojson',
    )
    if orbit:
        data["relativeOrbit"] = orbit
    if start:
        data["start"] = start
    if stop:
        data["end"] = stop
    if flightDirection:
        data["flightDirection"] = flightDirection

    r = requests.get(baseurl, params=data)
    print(r.url)
    #print(r.status_code)    
    return r.json()


def convert_dtypes(df):
    # https://stackoverflow.com/questions/61704608/pandas-infer-objects-doesnt-convert-string-columns-to-numeric
    
    ints = ['bytes','frameNumber','orbit','pathNumber']
    dates = ['processingDate','startTime','stopTime']
    strings = ['beamModeType', 'fileID','fileName','flightDirection',
               'granuleType','groupID', 'md5sum','platform','polarization',
               'processingLevel','sceneName','sensor','url']

    for col in ints:
        df[col] = df[col].astype('int')
    
    for col in dates:
        df[col] = gpd.pd.to_datetime(df[col])

    for col in strings:
        df[col] = df[col].astype('string')

    return df


def asfjson2geopandas(json):
    """ convert ASF JSON response to GeoDataFrame 

    """
    gf = gpd.GeoDataFrame.from_features(json)
    gf = gf.drop(columns=['browse','faradayRotation','insarStackId','offNadirAngle','pointingAngle'])
    gf = convert_dtypes(gf)
    gf.sort_values(by='startTime', inplace=True) #ascending head to tail

    return gf


def get_last_date_layered(path):
    dates = []
    layers = fiona.listlayers(path)
    for layer in layers:    
        gf = gpd.read_file(path, rows=slice(-1,None), layer=layer)
        dates.append(gf.startTime.values[0])
    
    date = gpd.pd.to_datetime(dates).max()
        
    # Add one second to avoid getting repeats
    datestr = str(date + gpd.pd.Timedelta(seconds=1))

    return datestr


def get_last_date(path):
    # last row will be most recent date
    gf = gpd.read_file(path, rows=slice(-1,None))
    date = gpd.pd.to_datetime(gf.startTime.values[0])
    # Add one second to avoid getting repeats
    datestr = str(date + gpd.pd.Timedelta(seconds=1))

    return datestr


def write_layers(gf):
    ''' write each relative orbit as a separate layer'''
    # 40218 frames
    # reading entire GPKG: CPU times: user 4.66 s, sys: 83.1 ms, total: 4.75 s
    # reading entire PARQUET: CPU times: user 1.49 s, sys: 137 ms, total: 1.62 s
    # %time gpd.read_file(path, layer='90') 1.05s (~5000 rows seems to scale w/ number of rows)
    mode = 'a' if os.path.isfile(INVENTORY) else 'w'

    for relOrb in gf.pathNumber.sort_values().unique():
        print(f'saving layer for relative orbit = {relOrb}')
        subset = gf.query('pathNumber == @relOrb')
        subset.to_file(INVENTORY, driver='GPKG', layer=str(relOrb))
    

def read_all_layers(path):
    # https://stackoverflow.com/questions/56165069/can-geopandas-get-a-geopackages-or-other-vector-file-all-layers
    layers = fiona.listlayers(path) 
    gf = gpd.read_file(path, driver='GPKG', layer=layers.pop(0)) # get first layer
    for layer in layers:
        tmp = gpd.read_file(path, layer=layer)
        gf = gf.append(tmp, ignore_index=True)

    return gf


def main():
    if os.path.isfile(INVENTORY):
       start = get_last_date_layered(INVENTORY)
    else:
       start = None    
    
    end = TODAY.strftime('%Y-%m-%d')
    response = query_asf(start=start, stop=end)
    
    if len(response) == 0:
        print('Did not find new scenes')
    else:
        gf = asfjson2geopandas(response)
        nscenes = len(gf)
        print(f'found {nscenes} scenes')
        
        #if os.path.isfile(INVENTORY):
        #    mode = 'a'
        #else:
        #    mode = 'w'
        #gf.to_file(INVENTORY, driver='GPKG', mode=mode)
        write_layers(gf)

if __name__ == "__main__":
    main() 
