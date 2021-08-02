#!/usr/bin/env python3
'''
Download json files for Sentinel-1 Archive metadata over greenland

Usage: ./get_asf_inventory.py

Will loop over years and months from 2014-10, search and download if local file does not exist
uses greenland.geojson for search polygon
'''

import requests
from datetime import date
import geopandas as gpd
import os

today = date.today()
print("Updating inventory through ", today)

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
    gf = gpd.read_file('greenland.json')
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
    #print(r.url)
    # Save Directly to dataframe
    # df = pd.DataFrame(r.json()[0])
    with open(outfile, "w") as j:
        j.write(r.text)



def main():
    # start of every month datetimeIndex
    DI = gpd.pd.date_range(start='2014-10-01', end=today, freq='MS')
    
    for i in range(len(DI)):
        start = DI[i].strftime('%Y-%m-%d')
        
        if i == len(DI)-1:
            end = today.strftime('%Y-%m-%d')
        else:
            end = DI[i+1].strftime('%Y-%m-%d')
        
        outfile = f'query_{DI[i].year}_{DI[i].month}.json'
        if not os.path.exists(outfile):
            query_asf(start=start, stop=end, outfile=outfile)
        else:
            print(f'{outfile} already exists... skipping search')

if __name__ == "__main__":
    main() 
