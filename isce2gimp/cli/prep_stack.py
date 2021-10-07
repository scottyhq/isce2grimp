#!/usr/bin/env python3
"""Prepare 'n' pairs for running topsApp.py on local machine.

Example
-------
Relative Orbit 90, ASF frame 227, 3 sequential pairs starting with absolute orbit 13416:
$ prep_stack -p 90 -f 227 -r 13416 -n 3

Author: Scott Henderson (scottyh@uw.edu)
Updated: 07/2021
"""
import dinosar.isce as dice
import argparse
import geopandas as gpd
import os
from pathlib import Path

ROOTDIR = Path(__file__).parent.parent
INVENTORY = os.path.join(ROOTDIR, 'data', 'asf_inventory.gpkg')
TEMPLATE = os.path.join(ROOTDIR, 'data', 'template.yml')


def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="prepare ISCE 2.5.2 topsApp.py")
    parser.add_argument(
        "-n", type=int, dest="npairs", required=True, help="number of sequential pairs"
    )
    parser.add_argument(
        "-r", type=str, dest="reference", required=True, help="reference absolute orbit"
    )
    parser.add_argument(
        "-p",
        type=str,
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
        "-f", type=str, dest="frame", required=True, help="ASF Frame"
    )

    return parser


def create_proc_dir(gf, inps):
    # create temporary download directory
    tmpData = f'./tmp-data-{inps.path}'
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

    reference_url = gf.query('absoluteOrbit == @inps.reference').downloadUrl.iloc[0]
    secondary_url = gf.query('absoluteOrbit == @inps.secondary').downloadUrl.iloc[0]
    downloadList = [reference_url,secondary_url]
    inps.reference_scenes = os.path.basename(reference_url)
    inps.secondary_scenes = os.path.basename(secondary_url)

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


def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()

    print(f'reading {INVENTORY}...')
    gf = gpd.read_file(INVENTORY)
    gf = gf.query('track==@inps.path and frameNumber==@inps.frame').reset_index()

    startInd = gf.query('absoluteOrbit == @inps.reference').index[0]
    
    print(f"Reading from template file: {inps.template}...")
    for i in range(inps.npairs):
        inps.reference = gf.absoluteOrbit.iloc[startInd+i]
        inps.secondary = gf.absoluteOrbit.iloc[startInd+(i+1)]
        print(inps.reference, inps.secondary)
        create_proc_dir(gf, inps)

if __name__ == "__main__":
    main()
