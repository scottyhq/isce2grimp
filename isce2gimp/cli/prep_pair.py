#!/usr/bin/env python3
"""Prepare directory for running topsApp.py on local machine.

Generate interferogram folder containing:
topsApp.xml
SLCs
Orbit files
Aux file

Example
-------
Relative Orbit 90, ASF frame 227, Absolute orbits in 2018-11:
$ prep_pair -p 90 -f 227 -r 13416 -s 24487

Author: Scott Henderson (scottyh@uw.edu)
Updated: 07/2021
"""
import argparse
import os
from dinosar.archive import asf
import dinosar.isce as dice
import datetime
import geopandas as gpd
from pathlib import Path

ROOTDIR = Path(__file__).parent.parent
INVENTORY = os.path.join(ROOTDIR, 'data', 'asf_inventory.gpkg')
TEMPLATE = os.path.join(ROOTDIR, 'data', 'template.yml')

def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="prepare ISCE 2.5.2 topsApp.py")
    parser.add_argument(
        "-r", type=int, dest="reference", required=True, help="reference absolute orbit"
    )
    parser.add_argument(
        "-s", type=int, dest="secondary", required=True, help="secondary absolute orbit"
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

    return parser



def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()

    gf = gpd.read_file(INVENTORY, layer=str(inps.path))
    gf = gf.query('frameNumber == @inps.frame')
    #print(gf.loc[:,['startTime','orbit']])

    print(f"Reading from template file: {inps.template}...")
    inputDict = dice.read_yaml_template(inps.template)

    # interferogram naming scheme: TRACK-FRAME-REFABS-SECABS
    intdir = f"{inps.path}-{inps.frame}-{inps.reference}-{inps.secondary}"
    
    if os.path.isdir(intdir):
        print(f'{intdir} already exists, remove it and rerun if you really want to')
        return

    os.mkdir(intdir)
    os.chdir(intdir)

    ref = gf.query('orbit == @inps.reference')
    sec = gf.query('orbit == @inps.secondary')
    refDate = ref.startTime.values[0]
    secDate = sec.startTime.values[0]
    print(refDate, secDate)

    reference_url = ref.url.values[0]
    secondary_url = sec.url.values[0]
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
    # Create a download file
    asf.write_download_urls(downloadList)
    print(f"Generated download-links.txt and topsApp.xml in {intdir}")


if __name__ == "__main__":
    main()
