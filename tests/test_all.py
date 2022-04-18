"""Tests for querying ASF archive."""
import os
import shlex
import subprocess
import contextlib
import pytest

from pathlib import Path
ROOTDIR = Path(__file__).parent.parent

@contextlib.contextmanager
def run_in(path):
    CWD = os.getcwd()
    os.chdir(path)
    try:
        yield
    except Exception as e:
        print(e)
        raise
    finally:
        os.chdir(CWD)


def test_query_inventory(tmpdir):
    with run_in(tmpdir):
        cmd = shlex.split('query_inventory -p 25 -s 2014-01-01 -e 2015-01-01')
        stdout = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout
        assert '2014-10-19' in stdout


def test_prep_pair(tmpdir):
    with run_in(tmpdir):
        cmd = shlex.split('prep_pair -p 90 -f 227 -r 13416 -s 24487')
        p = subprocess.run(cmd)
        outdir = "90-227-13416-24487"
        assert os.path.isdir(outdir)
        assert os.path.isfile(f'{outdir}/download-links.txt')
        assert os.path.isfile(f'{outdir}/topsApp.xml')

def test_custom_template(tmpdir):
    TEMPLATE = os.path.join(ROOTDIR, 'isce2grimp','data','template-noion.yml')
    with run_in(tmpdir):
        cmd = shlex.split(f'prep_stack -p 83 -f 374 -s 2021-09-04 -n 1 -m -t {TEMPLATE}')
        p = subprocess.run(cmd)
        with open('83-374-39530-39705/topsApp.xml') as f:
            links = f.read()
        assert "<property name='doionospherecorrection'>False</property>" in links

def test_prep_stack_enddate(tmpdir):
    # If more pairs requested than exist through enddate, enddate takes precedence
    with run_in(tmpdir):
        cmd = shlex.split('prep_stack -p 83 -f 374 -s 2020-06-01 -e 2020-07-01 -m -n 50')
        p = subprocess.run(cmd)
        outdirs = ["tmp-data-83", "83-374-32880-33055", "83-374-33055-33230"]
        for outdir in outdirs:
            assert os.path.isdir(outdir)

def test_prep_stack_npairs(tmpdir):
    # if fewer pairs requested than exist in temporal range, make sure just n pairs are used
    with run_in(tmpdir):
        cmd = shlex.split('prep_stack -p 83 -s 2019-01-01 -e 2021-01-01 -f 368 -n 2')
        p = subprocess.run(cmd)
        outdirs = ["tmp-data-83", "83-368-14459-25530", "83-368-25355-14459"]
        for outdir in outdirs:
            assert os.path.isdir(outdir)

def test_prep_stack(tmpdir):
    with run_in(tmpdir):
        cmd = shlex.split('prep_stack -p 90 -f 227 -r 13416 -n 3')
        p = subprocess.run(cmd)
        outdirs = ["90-227-13416-24487", "90-227-24487-13591", "90-227-13591-24662"]
        for outdir in outdirs:
            assert os.path.isdir(outdir)

def test_single_frame(tmpdir):
    ''' ASF frames do not always have consistent footprints (e.g. 90, 197)
    S1A_IW_SLC__1SSH_20150127T204430_20150127T204459_004362_005525_9592
    S1A_IW_SLC__1SSH_20160521T204438_20160521T204505_011362_011412_BC5A
    S1B_IW_SLC__1SSH_20170323T204358_20170323T204425_004841_00874A_4893
    '''
    with run_in(tmpdir):
        cmd = shlex.split('prep_stack -p 90 -f 197 -r 19716 -n 1')
        p = subprocess.run(cmd)
        PAIR = "90-197-19716-30787"
        assert os.path.isdir(PAIR)
        
        with open(f'{PAIR}/topsApp.xml') as f:
            config = f.read()

        # Should be single SLC
        SLC = "['../tmp-data-90/S1B_IW_SLC__1SDH_20200107T204419_20200107T204446_019716_02546B_DF12.zip']"
        assert SLC in config

def test_aligned_frames(tmpdir):
    with run_in(tmpdir):
        cmd = shlex.split('prep_stack -p 83 -f 374 -s 2021-09-04 -n 1 -m')
        p = subprocess.run(cmd)
        assert os.path.isdir("83-374-39530-39705")

def test_unaligned_frames(tmpdir):
    with run_in(tmpdir):
        cmd = shlex.split('prep_stack -p 83 -f 374 -s 2021-09-04 -n 1')
        p = subprocess.run(cmd)
        procdir = "83-374-39530-28634"
        datadir = "tmp-data-83"
        assert os.path.isdir(procdir)
        assert os.path.isfile(f'{datadir}/download-links.txt')
        with open(f'{datadir}/download-links.txt') as f:
            links = f.read()
        assert 'S1A_IW_SLC__1SDH_20210904T092848_20210904T092916_039530_04ABED_6AC5' in links
        assert 'S1B_IW_SLC__1SDH_20210910T092747_20210910T092817_028634_036ADB_B496' in links
        assert 'S1B_IW_SLC__1SDH_20210910T092814_20210910T092842_028634_036ADB_2401' in links
