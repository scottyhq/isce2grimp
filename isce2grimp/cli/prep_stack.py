#!/usr/bin/env python3
"""Prepare 'n' pairs for running topsApp.py on local machine.

Example
-------
Relative Orbit 90, ASF frame 227, 3 sequential pairs starting with absolute orbit 13416:
$ prep_stack -p 90 -f 227 -r 13416 -n 3

Relative orbit 83, ASF frame 374, relative orbit 39530
$ prep_stack -p 83 -f 374 -r 39530 -n 1

Author: Scott Henderson (scottyh@uw.edu)
Updated: 07/2021
"""
import isce2grimp.util.dinosar as dinosar
import argparse
import geopandas as gpd
import pandas as pd
import os
from pathlib import Path

pd.options.mode.chained_assignment = None  # default='warn'

ROOTDIR = Path(__file__).parent.parent
INVENTORY = os.path.join(ROOTDIR, 'data', 'asf_inventory.gpkg')
TEMPLATE = os.path.join(ROOTDIR, 'data', 'template.yml')


def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="prepare ISCE 2.5.2 topsApp.py")
    parser.add_argument(
        "-n", type=int, dest="npairs", required=False, default=10, help="number of sequential pairs"
    )
    parser.add_argument(
        "-r", type=int, dest="reference", required=False, help="reference absolute orbit"
    )
    parser.add_argument(
        "-s", type=str, dest="start", required=False, help="reference start date"
    )
    parser.add_argument(
        "-e", type=str, dest="end", required=False, help="reference end date"
    )
    parser.add_argument(
        "-p",
        type=int,
        dest="path",
        required=True,
        help="Path/Track/RelativeOrbit Number",
    )
    parser.add_argument(
        "-t",
        type=str,
        dest="template",
        default=TEMPLATE,
        required=False,
        help="Path to YAML input template file",
    )
    parser.add_argument(
        "-f", type=int, dest="frame", required=True, help="ASF Frame"
    )
    parser.add_argument(
        "-m", dest="match_frame", required=False, default=False,  action='store_true',
        help="use exact frame number match"
    )
    parser.add_argument(
        "-j", dest="jump", required=False, default=0, type=int,
        help="jump acquitions (-j 2 will skip 2 6-day acquisitions, forming 18-day pairs)"
    )

    return parser


def create_proc_dir(gf, inps):
    # create temporary download directory
    tmpData = f'tmp-data-{inps.path}'
    if not os.path.isdir(tmpData):
        os.mkdir(tmpData)
        urls=[]
    else:
        with open(f'{tmpData}/download-links.txt') as f:
            urls = [line.rstrip() for line in f.readlines()]

    # interferogram naming scheme: TRACK-FRAME-REFABS-SECABS
    intdir = f"{inps.path}-{inps.frame}-{inps.reference}-{inps.secondary}"

    inputDict = dinosar.read_yaml_template(inps.template)

    if os.path.isdir(intdir):
        print(f'{intdir} already exists, remove it and rerun if you really want to')
        return

    os.mkdir(intdir)
    os.chdir(intdir)

    reference_url = gf.query('orbit == @inps.reference').url.to_list()
    secondary_url = gf.query('orbit == @inps.secondary').url.to_list()
    downloadList = reference_url + secondary_url
    inps.reference_scenes = [f'../{tmpData}/{os.path.basename(x)}' for x in reference_url]
    inps.secondary_scenes = [f'../{tmpData}/{os.path.basename(x)}' for x in secondary_url]

    # Update input dictionary with argparse inputs
    inputDict["topsinsar"]["reference"]["safe"] = inps.reference_scenes
    inputDict["topsinsar"]["reference"]["output directory"] = "referencedir"
    inputDict["topsinsar"]["secondary"]["safe"] = inps.secondary_scenes
    inputDict["topsinsar"]["secondary"]["output directory"] = "secondarydir"

    xml = dinosar.dict2xml(inputDict)
    dinosar.write_xml(xml)

    os.chdir('../')

    # overwrite download-links with union of new urls
    newurls = list(set(urls).union(downloadList))
    newurls.sort()
    with open(f'{tmpData}/download-links.txt', 'w') as f:
        f.write('\n'.join(newurls))


def get_overlap_area(gf, gfREF):
    # want frames with > 10% overlap
    frame_area = gfREF.iloc[0].geometry.area
    overlaps = gf.geometry.map(lambda x: x.intersection(gfREF.geometry.iloc[0]).area/frame_area)

    return overlaps


def get_nearest_orbit(gf, date):
    """" return nearest orbit for a given date """
    print(f'getting nearest acquistion to {date}:')
    date_index = pd.DatetimeIndex(gf.startTime)
    int_index = date_index.get_indexer([pd.to_datetime(date)], method='nearest')[0]
    index = gf.index[int_index]
    print(gf.loc[index,['startTime','orbit']].to_string())

    return index


def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()

    print(f'reading relative orbit {inps.path} from {INVENTORY}...')
    gf = gpd.read_file(INVENTORY, layer=str(inps.path))
    print("temporal span: ", gf.startTime.min(), gf.stopTime.max())
    print('frames:', len(gf))

    print(f'requested number of pairs (-n):  ', inps.npairs)

    # Crop temporal span of inventory
    if inps.start:
        gf = gf.query('startTime >= @inps.start')
    elif inps.reference:
        START = gf.query('orbit == @inps.reference')['startTime'].min()
        gf = gf.query('startTime >= @START')
    if inps.end:
        gf = gf.query('stopTime <= @inps.end')
    gf.reset_index(inplace=True)
    print("cropped temporal span: ", gf.startTime.min(), gf.stopTime.max())
    print('frames:', len(gf))

    # Basic input error catching
    frames = gf.frameNumber.sort_values().unique()
    if inps.frame not in frames:
        raise ValueError(f'reference frame {inps.frame} not in inventory: {frames}')

    gfREF = gf.query('frameNumber == @inps.frame')
    orbits = gfREF.orbit.sort_values().unique()
    if inps.reference:
        if inps.reference not in orbits:
            raise ValueError(f'reference orbit {inps.reference} not in inventory: {orbits}')
        else:
            startInd = gfREF.query('orbit == @inps.reference').index[0]
    elif inps.start:
        startInd = get_nearest_orbit(gfREF, inps.start)
    else:
        raise ValueError('must supply either -r or -s')

    if inps.match_frame:
        gf = gfREF.loc[startInd:]
    else:
        # Since framing of consecutive frames don't always line up, find overlaps
        gf = gf.loc[startInd:startInd+200]
        gf['overlap'] = get_overlap_area(gf, gfREF)
        #print(gf.loc[:,['frameNumber','overlap']])
        gf = gf.query('overlap >= 0.1').reset_index()

    # Use requested 'npairs' up to end date accounting for jump setting
    select_orbits = gf.orbit.unique()
    print(f'unique orbits in requested range: {len(select_orbits)}')
    print(f'requested jump between acquisition pairs (-j): {inps.jump}')
    NPAIRS = len(select_orbits) - 1 - inps.jump
    if inps.npairs < NPAIRS:
        NPAIRS = inps.npairs

    print(f'creating processing directories for {NPAIRS} pairs:')
    for i in range(NPAIRS):
        inps.reference = select_orbits[i]
        inps.secondary = select_orbits[i + inps.jump + 1]
        print(inps.reference, inps.secondary)
        create_proc_dir(gf, inps)

if __name__ == "__main__":
    main()
