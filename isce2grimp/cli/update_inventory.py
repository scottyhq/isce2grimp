#!/usr/bin/env python3
'''
Download json inventory for ASF Sentinel-1 archive with greenland.geojson 

Usage: ./get_asf_inventory.py
'''
import requests
import geopandas as gpd
import pandas as pd
import fiona
from pathlib import Path

ROOTDIR = Path(__file__).parent.parent
INVENTORY = Path(ROOTDIR, 'data', 'asf_inventory.gpkg')
TODAY = str(str(pd.Timestamp.today()))

print(f"Updating {INVENTORY} through {TODAY}")

def query_asf(
    sat="Sentinel-1",
    orbit=None,
    start=None,
    stop=None,
    beam="IW",
    flightDirection=None,
):
    """Search ASF API and return GeoJSON

    https://docs.asf.alaska.edu/api/basics/
    NOTE: 15 minute time limit on running Search API queries
    """
    print(f"Querying ASF Vertex between {start} and {stop}...")
    gf = gpd.read_file(Path(ROOTDIR,'data','greenland.json'))
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
    #print(r.url)
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
        # deal with inhomogeneous formatting drop tzinfo (but all are UTC), keep only second precision
        df[col] = pd.to_datetime(df[col], format='ISO8601', utc=True).dt.tz_localize(None).astype('datetime64[s]')

    for col in strings:
        df[col] = df[col].astype('string')

    return df


def asfjson2geopandas(json):
    ''' convert ASF GEOJSON response to GeoDataFrame '''
    gf = gpd.GeoDataFrame.from_features(json)
    # We don't need these columns for local inventory:
    drop_cols = ['browse','faradayRotation','insarStackId','offNadirAngle','pointingAngle','centerLat','centerLon']
    gf = gf.drop(columns=drop_cols)
    gf = convert_dtypes(gf)
    gf.sort_values(by='startTime', inplace=True) #ascending head to tail

    return gf


def get_last_date_layered(path):
    ''' assumes data stored such that rows top to bottom are ascending chronological'''
    dates = []
    layers = fiona.listlayers(path)
    for layer in layers:    
        gf = gpd.read_file(path, rows=slice(-1,None), layer=layer)
        dates.append(gf.stopTime.values[0])
    
    date = pd.to_datetime(dates).max()
        
    # Add one second to avoid getting repeats
    datestr = str(date + pd.Timedelta(seconds=1))

    return datestr


def get_last_date(path):
    ''' for single dataframe, assume last row is most recent date '''
    gf = gpd.read_file(path, rows=slice(-1,None))
    date = pd.to_datetime(gf.stopTime.values[0])
    # Add one second to avoid getting repeats
    datestr = str(date + pd.Timedelta(seconds=1))

    return datestr


def write_layers(gf):
    ''' write each relative orbit as a separate layer'''
    if Path(INVENTORY).is_file():
        layers = fiona.listlayers(INVENTORY)
    else:
        layers = []

    for relOrb in gf.pathNumber.sort_values().unique():
        subset = gf.query('pathNumber == @relOrb')
        print(f'adding {len(subset)} scenes to relative orbit = {relOrb}')
        
        # DriverError: NULL pointer error if writing new layer with mode='a'
        if str(relOrb) in layers:
            mode = 'a'
        else:
            mode = 'w'

        subset = gf.query('pathNumber == @relOrb')
        subset.to_file(INVENTORY, driver='GPKG', layer=str(relOrb), mode=mode)
    

def read_all_layers(path):
    ''' read geopackage file with multiple layers into single dataframe'''
    layers = fiona.listlayers(path) 
    gf = gpd.read_file(path, driver='GPKG', layer=layers.pop(0)) # get first layer
    for layer in layers:
        tmp = gpd.read_file(path, layer=layer)
        gf = gf.append(tmp, ignore_index=True)

    return gf


def update_inventory(start, end):
    ''' update inventory through date=end '''
    response = query_asf(start=start, stop=end)
    if len(response['features']) > 0:
        gf = asfjson2geopandas(response)
        print(f'found {len(gf)} scenes')
        write_layers(gf)
    else:
        print('No new scenes found.')


def main():
    ''' create greenland inventory file '''
    # For initial inventory creation loop over years
    if not Path(INVENTORY).exists():
        update_inventory('2014-01-01', '2015-01-01') 
        end_range = pd.Timestamp.today() + pd.Timedelta(365, 'days')
        years = pd.date_range('2016-01-01', end_range, freq='YS')
        for end in years:
            start = get_last_date_layered(INVENTORY)
            update_inventory(start, end)

    else:
        start = get_last_date_layered(INVENTORY)    
        end = TODAY
        update_inventory(start, end)

if __name__ == "__main__":
    main() 
