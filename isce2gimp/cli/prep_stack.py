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
import dinosar.isce as dice
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

    inputDict = dice.read_yaml_template(inps.template)

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

    xml = dice.dict2xml(inputDict)
    dice.write_xml(xml)

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
    print(f'getting nearest acquistion to {date}')
    intindex = pd.DatetimeIndex(gf.startTime).get_loc(pd.to_datetime(date), method='nearest')
    ind = gf.index[intindex]
    print(gf.loc[ind,['startTime','orbit']].to_string())
    
    return ind


def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()

    print(f'reading relative orbit {inps.path} from {INVENTORY}...')
    gf = gpd.read_file(INVENTORY, layer=str(inps.path))
    print("temporal span:") 
    print(gf.startTime.min(), gf.stopTime.max())

    print(f'requested number of pairs (-n):  ', inps.npairs)

    if inps.end:
        gf = gf.query('stopTime <= @inps.end')
        print("cropped span:")
        print(gf.startTime.min(), gf.stopTime.max())
    
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
        gf = gf[startInd:startInd+200]
        gf['overlap'] = get_overlap_area(gf, gfREF)
        gf = gf.query('overlap >= 0.1').reset_index()
   
    # Use requested 'npairs' up to end date
    select_orbits = gf.orbit.unique()
    NPAIRS = len(select_orbits)-1
    if inps.npairs < NPAIRS:
        NPAIRS = inps.npairs
    
    for i in range(NPAIRS):
        inps.reference = select_orbits[i]
        inps.secondary = select_orbits[i+1]
        print(inps.reference, inps.secondary)
        create_proc_dir(gf, inps)

if __name__ == "__main__":
    main()
