#!/usr/bin/env python3
'''
Create geodat.in file, copy .unw and .conncomp to output folder, and run
convertuw.py for GIMP offset processing.

# Warnings and notes:
- this is a first pass, could be errors
- requires Python > 3.6
- maybe look at contrib/frameUtils/FrameInfoExtractor.py

# Common errors:
ValueError: time data '' does not match format '%Y-%m-%d %H:%M:%S.%f'
*currently a bit of a hack solution to extract time from isce.log, so make sure it is in the int directory

Example:
convert_isce.py -c -i /Volumes/insar10/scott/isce-frames/2018-11/A90-13416-24487 -o /Volumes/insar10/scott/gimpout/2018-11/A90-13416-24487

Author: Scott Henderson
Date: 05/02/2019
'''
import isce
from imageMath import IML
from iscesys import DateTimeUtil as DTU
from topsApp import TopsInSAR
from isceobj.Planet.Planet import Planet
from subprocess import PIPE, run
import numpy as np
import argparse
import datetime
import os
import glob
import shutil

import isce2gimp.util as u 

# Hard coded values for Sentinel-1 IW Mode
# -----------------
params = {}
params['look_direction'] = 'right'
params['wavelength'] = 0.05546576
params['range_posting'] = 2.329562
params['az_posting'] = 13.894780
params['sv_dt'] = 10.0
params['ReMajor'] = 6378.1370
params['ReMinor'] = 6356.7520
# ----------------


def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(
                        description='convert ISCE outputs to GIMP')
    parser.add_argument('-i', type=str, dest='intdir', required=True,
                        help='path to ISCE int-date1-date2 directory')
    parser.add_argument('-o', type=str, dest='outdir', required=True,
                        help='path to output directory')
    parser.add_argument('-c', dest='convert', action='store_true',
                        required=False, default=False,
                        help='Run convertuw.py in output folder')
    return parser


def get_ascNodeTime():
    ''' get ascending node time '''
    # self.reference.product.ascendingNodeTime not showing up in python :(
    cmd = 'grep reference.sensor.ascendingnodetime isce.log | cut -d "=" -f2'
    r = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    result = r.stdout.split('\n')[0].strip() # get rid of extra occurances from restarts
    fmt = "%Y-%m-%d %H:%M:%S.%f"
    ascNodeTime = datetime.datetime.strptime(result, fmt)
    with open('ascendingNodeTime', 'w') as f:
        f.write(ascNodeTime.strftime("%Y-%m-%dT%H:%M:%S.%f"))

    return ascNodeTime


def get_frame_number(burstTime, ascNodeTime):
    '''get frame number based on burst time from ascending node '''
    btime = 2.759
    correct = 0
    frame = int((burstTime - ascNodeTime).seconds / (btime + correct) + 0.5)

    return frame


def get_frames(self):
    ''' get collection of all bursts used in processing '''
    # self is instance of topsApp.TopsInSAR
    frames = []
    for swath in self.catalog['swaths']:
        referenceProduct = self._insar.loadProduct(os.path.join(
            self._insar.fineCoregDirname, 'IW{0}.xml'.format(swath)))
        frames.append(referenceProduct)

    return frames


def get_merged_orbit(self, frames):
    ''' get merged orbit from all swaths '''
    # self is instance of topsApp.TopsInSAR
    mergedOrbit = self._insar.getMergedOrbit(frames)

    return mergedOrbit


def get_statevecs(mergedOrbit):
    ''' Read topsApp.xml configuration/run topsApp programmatically '''

    nvecs = len(mergedOrbit._stateVectors)
    svt0 = DTU.seconds_since_midnight(
                            mergedOrbit._stateVectors[0].getTime())
    sv_list = []
    for sv in mergedOrbit._stateVectors:
        sv_list.append('{0:.6E} {1:.6E} {2:.6E}'.format(*sv.getPosition()))
        sv_list.append('{0:.6E} {1:.6E} {2:.6E}'.format(*sv.getVelocity()))
    stateVecs = '\n'.join(sv_list)

    return nvecs, svt0, stateVecs


def get_azimuth_info(self, frames):
    ''' Sensing start, prf '''
    # see /opt/isce2-2.3.1/isce/components/isceobj/TopsProc/runGeocode.py
    topSwath = min(frames, key=lambda x: x.sensingStart)
    t0 = topSwath.sensingStart
    # is dtaz is constant for IW globally? 0.002055556299999998
    dtaz = topSwath.bursts[0].azimuthTimeInterval
    alooks_offset = ((self.numberAzimuthLooks-1)/2.0) * dtaz
    sensingStart = t0 + datetime.timedelta(seconds=alooks_offset)

    bottomSwath = max(frames, key=lambda x: x.sensingStop)
    tf = bottomSwath.sensingStop
    sensingStop = tf - datetime.timedelta(seconds=alooks_offset)

    sensingMid = sensingStart + (sensingStop - sensingStart)/2

    return sensingStart, sensingMid, sensingStop


def get_ranges(self, frames):
    ''' Get near, mid, far range '''
    # see /opt/isce2-2.3.1/isce/components/isceobj/TopsProc/runGeocode.py
    leftSwath = min(frames, key=lambda x: x.startingRange)
    r0 = leftSwath.startingRange
    dr = leftSwath.bursts[0].rangePixelSize  # constant: range_posting?
    # Get range and timing for multilooked array
    rlooks_offset = ((self.numberRangeLooks-1)/2.0) * dr
    rangeFirstSample = r0 + rlooks_offset

    rightSwath = max(frames, key=lambda x: x.farRange)
    rf = rightSwath.farRange
    rangeFar = rf - rlooks_offset
    # NOTE: better to use far-range determined from topophase.unw image?
    # for int-20190414-20190426 off by 23meters
    # rangeFar = rangeFirstSample + ((img.width-1) * self.numberRangeLooks * dr)

    rangeMid = (rangeFar + rangeFirstSample)/2

    return rangeFirstSample, rangeMid, rangeFar


def get_altitude(orbit, tmid):
    ''' get spacecraft altitude along orbit at given time '''
    peg = orbit.interpolateOrbit(tmid, method='hermite')
    refElp = Planet(pname='Earth').ellipsoid
    llh = refElp.xyz_to_llh(peg.getPosition())
    altitude = llh[2]

    return altitude


def get_mid_incidence(rangeMid, timeMid, orbit):
    ''' use trig to calculate incidence angle from ECEF coords'''
    # currently within 0.5 deg of los.rdr
    # satellite position
    peg = orbit.interpolateOrbit(timeMid, method='hermite')
    sat_ecef = peg.getPosition()  # ecef xyz
    refElp = Planet(pname='Earth').ellipsoid
    sat_llh = refElp.xyz_to_llh(sat_ecef)
    # H = llh[2]
    Re = refElp.localRadius(sat_llh)

    # image midpoint
    mid_llh = orbit.rdr2geo(timeMid, rangeMid)
    mid_ecef = refElp.llh_to_xyz(mid_llh)

    # trig to get phic
    lam = (np.arccos(
            np.dot(sat_ecef, mid_ecef) /
            (np.linalg.norm(sat_ecef) * np.linalg.norm(mid_ecef)))
           )
    eta = np.arcsin((Re * np.sin(lam)) / rangeMid)
    phic = np.degrees(eta + lam)

    return phic


def get_corner_coordinates(self, frames, orbit):
    ''' corner coords based on '''
    r0, rm, r1 = get_ranges(self, frames)
    t0, tm, t1 = get_azimuth_info(self, frames)
    # warning copied from isce rdr2geo documentation:
    ## Returns point on ground at given height and doppler frequency.
    ## Never to be used for heavy duty computing.
    earlyNear = orbit.rdr2geo(t0, r0)[:2]
    earlyFar = orbit.rdr2geo(t0, r1)[:2]
    lateFar = orbit.rdr2geo(t1, r1)[:2]
    lateNear = orbit.rdr2geo(t1, r0)[:2]
    centroid = orbit.rdr2geo(tm, rm)[:2]

    # string format coords - double check w/ kmls
    if frames[0].bursts[0].passDirection == 'ASCENDING':
        ll = '{0:.6f} {1:.6f}'.format(*earlyNear)
        lr = '{0:.6f} {1:.6f}'.format(*earlyFar)
        ur = '{0:.6f} {1:.6f}'.format(*lateFar)
        ul = '{0:.6f} {1:.6f}'.format(*lateNear)
    else:
        ur = '{0:.6f} {1:.6f}'.format(*earlyNear)
        ul = '{0:.6f} {1:.6f}'.format(*earlyFar)
        ll = '{0:.6f} {1:.6f}'.format(*lateFar)
        lr = '{0:.6f} {1:.6f}'.format(*lateNear)

    center = '{0:.6f} {1:.6f}'.format(*centroid)

    return ll, lr, ul, ur, center


def write_geodat_config(params, outdir):
    ''' write output geodat.in file for GIMP processing '''
    output = '''; Image name: {name}
; Image date: {date}
; Image time: {time}
; Nominal center lat,lon: 0.000000 0.000000
; track direction: 0.000000
; S/C altitude: {altitude}
; Average height above terrain: 0.000000
; Vel along track: 0.000000
; PRF :   {prf}
; near/cen/far range : {ranges}
; Range pixel spacing :   {rangePixelSpacing}
; Number of looks (rg,az) :   {rlooks} {alooks}
; Azimuth pixel spacing :   {azimuthPixelSpacing}
; Number of pixels (rg,az) :  {shape}
; Number of state vectors :   {nvecs}
; Start time of state vectors :   {svt0}
; Interval between 2 state vectors :   {sv_dt}
; Look direction  :   1.000000
; Offset of first recordin complex image (s) : 0.000000
; Skew offset (s), squint (deg) : 0.000000  0.000000
;
; {passDir} Pass
;
; rangesize,azimuthsize,nrangelooks,nazimuthlooks
;
{width}  {length}  {rlooks}  {alooks}
;
; ReMajor, ReMinor, Rc, phic, h
;
{ReMajor}    {ReMinor}   {rangeMid_km}  {incidenceMid}   {altitude_km}
;
; ll,lr,ul,ur,center
;
{ll}
{lr}
{ul}
{ur}
{center}
;
; Range/azimuth single look pixel sizes
;
{range_posting}  {az_posting}
;
{passDir}
;
; Look direction
;
right
;
; Flag to indicate state vectors and associated data
;
state
; time after squint and skew corrections
{time}
; prf
{prf}
; wavelength
{wavelength}
; number of state vectors
{nvecs}
; time of first vector
{svt0}
; state vector interval
{sv_dt}
; state vectors
{stateVecs}
'''.format(**params)
    outpath = f"{outdir}/geodat{params['rlooks']}x{params['alooks']}.in"
    with open(outpath, 'w') as f:
        f.write(output)


def copy_outputs(outdir):
    ''' copy select files from isce merged/ directory '''
    print(f'copying files to {outdir}')
    files = glob.glob('merged/filt_topophase.unw*')
    files += glob.glob('frames.*')
    files += ['topsApp.xml', 'isce.log', 'topsProc.xml']
    files += ['nohup.out', 'stderr.txt', 'stdout.txt']
    files += ['ascendingNodeTime']
    for file in files:
        #print(file)
        try:
          shutil.copy(file, outdir)
        except:
          print('not found:',file)
    # Also make copy of entire merged folder
    #shutil.copytree('merged', outdir + '/merged')


def convertuw(isceUNW, geodat):
    ''' Convert geomosaicked sigma to tiff for GIMP'''
    uwFile=isceUNW.replace('unw','uw')
    # input image
    print(isceUNW,geodat,uwFile)

    georxa=u.geodatrxa(file=geodat)
    print(georxa.nr,georxa.na)
    #exit()
    cc =u.readImage(isceUNW+'.conncomp',georxa.nr,georxa.na,'u1')
    print(np.min(cc),np.max(cc))
    unw=u.readImage(isceUNW,georxa.nr*2,georxa.na,'f4')
    uw=unw[0:,georxa.nr:]
    uw[cc == 0] = -2.0e9
    print(np.min(uw),np.max(uw))
    u.writeImage(uwFile,uw,'>f4')

    print(unw.shape,uw.shape)


def main():
    print('\n======\n Converting ISCE outputs to GIMP... \n======\n')
    parser = cmdLineParse()
    inps = parser.parse_args()
    
    # make sure output directory path is absolute
    inps.outdir = os.path.abspath(inps.outdir)
    os.chdir(inps.intdir)

    self = TopsInSAR(cmdline='topsApp.xml')  # topsApp.TopsInSAR
    self.configure()  # overwrites defaults by reading topsApp.xml
    # NOTE! self._insar is instance of <isceobj.TopsProc.TopsProc.TopsProc>
    # insar = self._insar #create mapping in functions if needed
    rlooks = self.numberRangeLooks
    alooks = self.numberAzimuthLooks

    frames = get_frames(self)  # can be slow
    orientation = frames[0].bursts[0].passDirection.lower()
    # is aziTimeInt constant for IW globally? 0.002055556299999998
    prf = 1.0 / frames[0].bursts[0].azimuthTimeInterval

    orbit = get_merged_orbit(self, frames)
    nvecs, svt0, stateVecs = get_statevecs(orbit)

    rangeFirstSample, rangeMid, rangeFar = get_ranges(self, frames)
    sensingStart, sensingMid, sensingStop = get_azimuth_info(self, frames)
    # Write frame numbers
    ascNodeTime = get_ascNodeTime()
    f0 = get_frame_number(sensingStart, ascNodeTime)
    ff = get_frame_number(sensingStop, ascNodeTime)
    with open(f'frames.{f0}.{ff}', 'w') as f:
        f.write('')

    altitude = get_altitude(orbit, sensingMid)
    phic = get_mid_incidence(rangeMid, sensingMid, orbit)
    ll, lr, ul, ur, center = get_corner_coordinates(self, frames, orbit)

    # Load unwrapped image to get dimensions
    img, dataname, metaname = IML.loadImage('merged/filt_topophase.unw')

    params['prf'] = prf
    params['name'] = self.catalog['reference']['safe'][0]
    params['date'] = sensingStart.strftime('%-d %b %Y').upper()
    params['time'] = sensingStart.strftime('%-H %-M %-S.%f')
    params['ranges'] = f'{rangeFirstSample:.6f} {rangeMid:.6f} {rangeFar:.6f}'
    params['rangeMid_km'] = f'{rangeMid/1e3:.6f}'
    params['rlooks'] = rlooks
    params['alooks'] = alooks
    params['width'] = img.width
    params['length'] = img.length
    params['shape'] = f'{img.width} {img.length}'
    params['rangePixelSpacing'] = params['range_posting'] * rlooks
    params['azimuthPixelSpacing'] = params['az_posting'] * alooks
    params['altitude'] = altitude
    params['altitude_km'] = f'{altitude/1e3:.6f}'
    params['incidenceMid'] = f'{phic:.6f}'
    params['passDir'] = orientation
    params['svt0'] = svt0
    params['nvecs'] = nvecs
    params['stateVecs'] = stateVecs

    params['ll'] = ll
    params['lr'] = lr
    params['ul'] = ul
    params['ur'] = ur
    params['center'] = center
    #print(params)

    if not os.path.isdir(inps.outdir):
        os.makedirs(inps.outdir)
    write_geodat_config(params, inps.outdir)
    copy_outputs(inps.outdir)

    if inps.convert is True:
        geodat = f'{inps.outdir}/geodat{rlooks}x{alooks}.in'
        convertuw(f'{inps.outdir}/filt_topophase.unw', geodat)

    print('Done!')

if __name__ == "__main__":
    main()

