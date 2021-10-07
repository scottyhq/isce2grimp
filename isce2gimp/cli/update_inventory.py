#!/usr/bin/env python3
'''
Download json inventory for ASF Sentinel-1 archive with greenland.geojson 

Usage: ./get_asf_inventory.py
'''

import requests
from datetime import date
import geopandas as gpd
import os
import shapely
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
    """Search ASF API

    Notes
    ----------
    API keywords = [absoluteOrbit,asfframe,maxBaselinePerp,minBaselinePerp,
    beamMode,beamSwath,collectionName,maxDoppler,minDoppler,maxFaradayRotation,
    minFaradayRotation,flightDirection,flightLine,frame,granule_list,
    maxInsarStackSize,minInsarStackSize,intersectsWith,lookDirection,
    offNadirAngle,output,platform,polarization,polygon,processingLevel,
    relativeOrbit,maxResults,processingDate,start or end acquisition time

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
        output='json',
    )
    if orbit:
        data["relativeOrbit"] = orbit
    if start:
        data["start"] = start
    if stop:
        data["end"] = stop
    if flightDirection:
        data["flightDirection"] = flightDirection

    r = requests.get(baseurl, params=data, timeout=100)
    #print(r.status_code)    
    return r.json()


def asfjson2geopandas(json):
    df = gpd.pd.DataFrame(json[0])
    polygons = df.stringFootprint.apply(shapely.wkt.loads)
    gf = gpd.GeoDataFrame(df, crs="EPSG:4326", geometry=polygons)
    gf.sort_values(by='sceneDate', inplace=True) #ascending head to tail

    return gf


def get_last_date():
    # last row will be most recent date
    gf = gpd.read_file(INVENTORY, rows=slice(-1,None))
    date = gf.sceneDate.values[0]
    # Add one second to avoid getting repeats
    datestr = str(gpd.pd.to_datetime(date) + gpd.pd.Timedelta(seconds=1))

    return datestr



def main():
    if os.path.isfile(INVENTORY):
       start = get_last_date()
    else:
       start = None    
    
    end = TODAY.strftime('%Y-%m-%d')
    response = query_asf(start=start, stop=end)
    
    if len(response[0]) == 0:
        print('Did not find new scenes')
    else:
        gf = asfjson2geopandas(response)
        nscenes = len(gf)
        print(f'found {nscenes} scenes')
        
        if os.path.isfile(INVENTORY):
            mode = 'a'
        else:
            mode = 'w'
        
        gf.to_file(INVENTORY, driver='GPKG', mode=mode)

if __name__ == "__main__":
    main() 
