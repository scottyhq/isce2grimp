#!/usr/bin/env python3
'''
Download a Copernicus DEM (30m) and mosaic for ISCE processing
https://copernicus-dem-30m.s3.amazonaws.com/readme.html
# example for ISCE dem over grand mesa (native 30m/ posting)
./get_glo30dem.py -d -r 36 40 -110 -106 
# example for ISCE dem over greenland (~90m posting at mid latitude)
./get_glo30dem.py -d -r 36 40 -110 -106 -tr 0.0025
#AWS CLI Example (note in eu-central-1)
#aws --no-sign-request s3 ls s3://copernicus-dem-30m/Copernicus_DSM_COG_10_N17_00_E031_00_DEM/
#2020-11-24 12:26:32   39858660 Copernicus_DSM_COG_10_N17_00_E031_00_DEM.tif
#aws --no-sign-request s3 ls s3://copernicus-dem-90m/Copernicus_DSM_COG_30_S90_00_W178_00_DEM/
#2020-11-24 06:21:12     468750 Copernicus_DSM_COG_30_S90_00_W178_00_DEM.tif
'''

import argparse
import subprocess
import numpy as np
import sys
import os
import logging
from multiprocessing.pool import ThreadPool as Pool

def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description='get_glo30.py')
    parser.add_argument('-r', type=float, nargs=4, dest='roi', required=False,
                        metavar=('S', 'N', 'W', 'E'),
                        help='Region of interest bbox [S,N,W,E]')
    parser.add_argument('-d', type=bool, dest='download', required=False,
                        default=False,
                        help='download tiles')
    parser.add_argument('-b', type=str, dest='bucket', required=False,
                        default='s3://copernicus-dem-30m/',
                        help='s3 bucket name')
    parser.add_argument('-tr', type=float, dest='resolution', required=False,
                        default=0.000277777777778,
                        help='target posting (degrees)')
    return parser


def run_bash_command(cmd):
    """Call a system command through the subprocess python module."""
    logging.info(cmd)
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print("Child was terminated by signal", -retcode, file=sys.stderr)
        else:
            print("Child returned", retcode, file=sys.stderr)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)

def hillshade(vrt):
    """create a hillshade for QGIS"""
    if not os.path.exists('hillshade.tif'):
        cmd = f'gdaldem hillshade -s 111120 glo30_isce.dem.wgs84.vrt glo30_isce_hillshade.tif'
        run_bash_command(cmd)


def download(s3uri):
    """Download all sequentially"""
    if not os.path.exists(os.path.basename(s3uri)):
        cmd = f'aws --no-sign-request s3 cp {s3uri} .'
        run_bash_command(cmd)


def parallel_download(fileList):
    with open(fileList, 'r') as f:
        urls = [x.rstrip() for x in f.readlines()]
    logging.debug(urls)
    pool = Pool()
    pool.map(download, urls)


def construct_urls(lats, lons, bucket, res=10):
    """construct urls for downloading resolution in arcsec 10=30m"""
    URLs = []
    logging.info(f'{lats}, {lons}')
    for lat in lats:
        for lon in lons:
            lathemi = 'S' if lat < 0 else 'N'
            lonhemi = 'W' if lon < 0 else 'E'
            folder = f'Copernicus_DSM_COG_{res}_{lathemi}{abs(lat):02d}_00_{lonhemi}{abs(lon):03d}_00_DEM'
            scene = f'{folder}.tif'
            URLs.append(os.path.join(bucket, folder, scene))

    return URLs


def get_file_list(roi, bucket):
    """Construct file list e.g. Greenland: (SNWE) [73, 81, -49, -16]
    note that tiles are simply every 1deg, so number of pixels in tile changes with lat
    """
    S, N, W, E = np.round(roi).astype('int')
    logging.info(f'S={S}, N={N}, W={W}, E={E}')
    # Buffer? # for now go to North-1 East-1 b/c tiles ref LL corner
    lats = np.arange(S, N)
    lons = np.arange(W, E)
    URLs = construct_urls(lats, lons, bucket)

    with open('download-list.txt', 'w') as f:
        f.write('\n'.join(URLs))

    with open('gdal-list.txt', 'w') as f:
        #gdalURLs = [x.replace('s3://', '/vsis3/') for x in URLs]
        # download tiles in parallel, then work with local files
        gdalURLs = [os.path.basename(x) for x in URLs]
        f.write('\n'.join(gdalURLs))

    return URLs


def mosaic(roi, resolution, outname='mosaic.vrt', inputlist='gdal-list.txt', tiff=False, isce=False):
    """Build VRT from list of tif files """
    # NOTE: for some reason can't open ISCE directly with QGIS, but works fine with rasterio, xarray...
    S, N, W, E = np.round(roi).astype('int')
    # NOTE: consider -resolution highest here for higher latitudes
    cmd = f'gdalbuildvrt -overwrite mosaic.vrt *tif'
    run_bash_command(cmd)
    # Vertical datum correction (Earth Gravitational Model 2008) to WGS84 ellipsoid heights
    cmd = f'gdalwarp -r bilinear -tr {resolution} {resolution} -of VRT -multi -overwrite -s_srs "+proj=longlat +datum=WGS84 +no_defs +geoidgrids=egm08_25.gtx" -t_srs EPSG:4326 mosaic.vrt mosaic_wgs84.vrt'
    run_bash_command(cmd)
    # Write to disk for ISCE processing
    cmd = f'gdal_translate -of ISCE -a_ullr {W} {N} {E} {S} mosaic_wgs84.vrt glo30_isce.dem.wgs84'
    run_bash_command(cmd)
    cmd = f'gdal_translate -of VRT glo30_isce.dem.wgs84 glo30_isce.dem.wgs84.vrt'
    run_bash_command(cmd)

    with open('glo30_isce.dem.wgs84.xml') as f:
        text = f.read()
    append_text = '''<imageFile>
<property name="family">
    <value>demimage</value>
    <doc>Instance family name</doc>
</property>
<property name="name">
    <value>demimage_name</value>
    <doc>Instance name</doc>
</property>
<property name="image_type">
    <value>dem</value>
    <doc>Image type used for displaying.</doc>
</property>
<property name="reference">
    <value>WGS84</value>
    <doc>Geodetic datum</doc>
</property>
<property name="extra_file_name">
    <value>glo30_isce.dem.wgs84.vrt</value>
    <doc>For example name of vrt metadata.</doc>
</property>'''
    modtext = text.replace('<imageFile>', append_text)
    with open('glo30_isce.dem.wgs84.xml', 'w') as f:
        text = f.write(modtext)

def main(parser):
    """Run as a script with args coming from argparse."""
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    # NOTE: need to fix list of tiles for high latitutudes
    # Copernicus_DSM_COG_10_N77_00_W010_00_DEM.tif: No such file or directory
    if args.download:
        get_file_list(args.roi, args.bucket) #writes download-list.txt
        parallel_download('download-list.txt')
    mosaic(args.roi, args.resolution)


if __name__ == '__main__':
    parser = cmdLineParse()
    main(parser)
