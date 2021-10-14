#!/usr/bin/env python3
'''
print range of values (unique dates), absolute orbits for a given path

Usage: ./query_inventory -p 83 -s 2019-01-01 -e 2021-01-01

various tabuler summaries 
print(gf.groupby(['date','platform']).frameNumber.agg(lambda x: list(x)).to_string())
print(gf.groupby(['platform','frameNumber']).sceneName.count())
print(gf.groupby(['date','platform','orbit']).frameNumber.count())
'''
import argparse
import geopandas as gpd
import pandas as pd
import os
from pathlib import Path

pd.options.mode.chained_assignment = None  # default='warn'

ROOTDIR = Path(__file__).parent.parent
INVENTORY = os.path.join(ROOTDIR, 'data', 'asf_inventory.gpkg')

def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="query inventory")
    parser.add_argument(
        "-s", type=str, dest="start", required=False, help="start date"
    )
    parser.add_argument(
        "-e", type=str, dest="end", required=False, help="end date"
    )
    parser.add_argument(
        "-p",
        type=int,
        dest="path",
        required=True,
        help="Path/Track/RelativeOrbit Number",
    )

    return parser

def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()
    
    print(f'Reading {INVENTORY} for relative orbit {inps.path}...')
    gf = gpd.read_file(INVENTORY, layer=str(inps.path))
    print(len(gf),'acquisitions in inventory')
    print(len(gf.orbit.unique()),'orbits')

    if inps.start:
        gf = gf.query('startTime >= @inps.start')
    
    if inps.end:
        gf = gf.query('startTime <= @inps.end')

    gf['date'] = gf.startTime.str[:10]
    print(gf.groupby(['date','orbit','platform']).frameNumber.agg(lambda x: list(x)).to_string())

if __name__ == "__main__":
    main() 
