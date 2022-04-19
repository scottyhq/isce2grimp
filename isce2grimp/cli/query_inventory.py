#!/usr/bin/env python3
'''
print range of values (unique dates), absolute orbits for a given path

Usage:

query_inventory -p 83 -s 2019-01-01 -e 2021-01-01
query_inventory -p 17 -f 211
query_inventory -p 17 -f 211 -a 19864


various tabuler summaries
print(gf.groupby(['date','platform']).frameNumber.agg(lambda x: list(x)).to_string())
print(gf.groupby(['platform','frameNumber']).sceneName.count())
print(gf.groupby(['date','platform','orbit']).frameNumber.count())
'''
import argparse
import geopandas as gpd
import pandas as pd
import os
import sys
from isce2grimp.cli.update_inventory import read_all_layers
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
        required=False,
        help="Path/Track/RelativeOrbit Number",
    )
    parser.add_argument(
        "-f", type=int, dest="frame", required=False, help="frame number"
    )
    parser.add_argument(
        "-a", type=int, dest="absolute_orbit", required=False, help="absolute orbit number"
    )

    return parser

def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()

    if inps.path:
        print(f'Reading {INVENTORY} for relative orbit {inps.path}...')
        gf = gpd.read_file(INVENTORY, layer=str(inps.path))
        print(len(gf),'acquisitions in inventory')
        print(len(gf.orbit.unique()),'orbits')
    else:
        parser.print_help(sys.stderr)
        print(f'Generating full summary for {INVENTORY}...')
        gf = read_all_layers(INVENTORY)
        print('Total frames=',len(gf))
        summary = gf.groupby(['pathNumber']).agg(dict(sceneName='count', frameNumber='nunique', orbit='nunique',startTime='min', stopTime='max'))
        summary = summary.rename(columns={'sceneName':'totalScenes','frameNumber':'uniqueFrames','orbit':'relativeOrbits'})
        print(summary)
        sys.exit()

    if inps.frame:
        gf = gf.query('frameNumber == @inps.frame')

    # convert dtypes
    gf['date'] = gf.startTime.str[:10]
    gf['startTime'] = pd.to_datetime(gf.startTime)

    if inps.start:
        gf = gf.query('startTime >= @inps.start')

    if inps.end:
        gf = gf.query('startTime <= @inps.end')

    # Add timespans with '0' for first entry instead of 'NaT'
    gf['dt_days'] = pd.to_datetime(gf.date).diff().dt.days.fillna(0).astype(int)

    if inps.absolute_orbit:
        print(gf.query('orbit == @inps.absolute_orbit').T.drop('geometry').to_string())
    else:
        print(gf.groupby(['date','dt_days','orbit','platform']).frameNumber.agg(lambda x: list(x)).to_string())

if __name__ == "__main__":
    main()
