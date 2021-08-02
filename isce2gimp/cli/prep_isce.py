#!/usr/bin/env python3
"""Prepare directory for running topsApp.py on local machine.

Generate interferogram folder containing:
topsApp.xml
SLCs
Orbit files
Aux file

Example
-------
Relative Orbit 90, ASF frame 227, Absolute orbites in 2018-11:
$ isce2gimp.py -p 90 -f 227 -r 13416 -s 24487

Author: Scott Henderson (scottyh@uw.edu)
Updated: 07/2021
"""
import argparse
import os
from dinosar.archive import asf
import dinosar.isce as dice

import isce2gimp
packageDir = os.path.dirname(os.path.dirname(isce2gimp.__file__))

def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="prepare ISCE 2.5.2 topsApp.py")
    parser.add_argument(
        "-y", type=str, dest="year", required=True, help="year"
    )
    parser.add_argument(
        "-m", type=str, dest="month", required=True, help="month"
    )
    parser.add_argument(
        "-r", type=str, dest="reference", required=False, help="reference date"
    )
    parser.add_argument(
        "-s", type=str, dest="secondary", required=False, help="secondary date"
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
        required=False,
        help="Path to YAML input template file",
    )
    parser.add_argument(
        "-f", type=str, dest="frame", required=True, help="ASF Frame"
    )

    return parser


def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()

    inventoryFile = os.path.join(packageDir,'data',f'query_{inps.year}_{inps.month}.json')
    gf = asf.load_asf_json(inventoryFile)
    gf = gf.query('track==@inps.path and frameNumber==@inps.frame').sort_values('timeStamp')
    print(gf.loc[:,['timeStamp','absoluteOrbit']])

    templateFile = os.path.join(packageDir,'template.yml')
    print(f"Reading from template file: {templateFile}...")
    inputDict = dice.read_yaml_template(templateFile)

    if not inps.reference:
        inps.reference = gf.absoluteOrbit.iloc[0]
    if not inps.secondary:
        inps.secondary = gf.absoluteOrbit.iloc[1]

    # interferogram naming scheme: TRACK-FRAME-REFABS-SECABS
    intdir = f"{inps.path}-{inps.frame}-{inps.reference}-{inps.secondary}"
    if not os.path.isdir(intdir):
        os.mkdir(intdir)
    os.chdir(intdir)

    refDate = gf.query('absoluteOrbit == @inps.reference').sceneDateString.iloc[0]
    secDate = gf.query('absoluteOrbit == @inps.secondary').sceneDateString.iloc[0]
    print(refDate, secDate)

    reference_url = gf.query('absoluteOrbit == @inps.reference').downloadUrl.iloc[0]
    secondary_url = gf.query('absoluteOrbit == @inps.secondary').downloadUrl.iloc[0]
    downloadList = [reference_url,secondary_url]
    inps.reference_scenes = os.path.basename(reference_url)
    inps.secondary_scenes = os.path.basename(secondary_url)

    # NOTE: use locally stored orbits, instead of downloading
    #try:
    #    frame = os.path.basename(inps.reference_scenes)
    #    downloadList.append(asf.get_orbit_url(frame))
    #    frame = os.path.basename(inps.secondary_scenes)
    #    downloadList.append(asf.get_orbit_url(frame))
    #except Exception as e:
    #    print("Trouble downloading POEORB... maybe scene is too recent?")
    #    print("Falling back to using header orbits")
    #    print(e)
    #    pass

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
