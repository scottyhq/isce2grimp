#!/usr/bin/env python3
"""run ISCE on APL server

Example
-------
Use 12 CPUs, single socket
$ run_isce -i 90-231-13416-24487 -n 12

Author: Scott Henderson (scottyh@uw.edu)
Updated: 07/2021
"""
import argparse
import os
import isce

# Set up environment variables
os.environ['ISCE_HOME'] = os.path.dirname(isce.__file__)
os.environ['ISCE_ROOT'] = os.path.dirname(os.environ['ISCE_HOME'])
os.environ['PATH']+='{ISCE_HOME}/bin:{ISCE_HOME}/applications'.format(**os.environ)
print(os.environ['PATH'])

def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="run ISCE 2.5.2 topsApp.py")
    parser.add_argument(
        "-i", type=str, dest="intdir", required=True, help="interferogram directory"
    )
    parser.add_argument(
        "-n", type=int, dest="cpus", required=False, default=8, help="number of CPUs to use"
    )

    return parser


def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()
    print(f'Processing interferogram in {inps.intdir}...')
    os.chdir(inps.intdir)
    print('Downloading SLCs...')
    # NOTE: this requires ~/.netrc
    #cmd = 'wget -nc --input-file=download-links.txt'
    cmd = 'aria2c -c -i download-links.txt'  # -x 8 -s 8, not sure if faster w/ multiple connections
    print(cmd)
    os.system(cmd)
    print('Running ISCE...')
    cmd = f"OMP_NUM_THREADS={inps.cpus} OMP_PLACES='sockets(1)' nohup topsApp.py --end=unwrap"
    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
