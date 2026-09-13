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


def runTopsApp(cpus=8, endStep='unwrap', startStep=None):
    """Run topsApp.py in the current directory (no downloading).

    Parameters
    ----------
    cpus : int
        OMP thread count.
    endStep : str
        topsApp step to stop after (passed as --end). For the single-unwrap
        S1 workflow this is 'burstifg' (the fine_interferogram step, which is
        the last step before mergebursts and runs after the ionosphere step),
        so azPhaseCorrect does the only merge/filter/unwrap pass.
    startStep : str or None
        Optional topsApp step to start from (passed as --start).
    """
    steps = ''
    if startStep is not None:
        steps += f' --start={startStep}'
    if endStep is not None:
        steps += f' --end={endStep}'
    cmd = (f"OMP_NUM_THREADS={cpus} OMP_PLACES='sockets(1)' "
           f"nohup topsApp.py{steps}")
    print(cmd)
    os.system(cmd)


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
    runTopsApp(cpus=inps.cpus, endStep='unwrap')


if __name__ == "__main__":
    main()
