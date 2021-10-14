"""Tests for querying ASF archive."""
import os
import contextlib
import pytest

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


def test_prep_pair(tmpdir):
    with run_in(tmpdir):
        os.system('prep_pair -p 90 -f 227 -r 13416 -s 24487')
        outdir = "90-227-13416-24487"
        assert os.path.isdir(outdir)
        assert os.path.isfile(f'{outdir}/download-links.txt')
        assert os.path.isfile(f'{outdir}/topsApp.xml')

def test_prep_stack(tmpdir):
    with run_in(tmpdir):
        os.system('prep_stack -p 90 -f 227 -r 13416 -n 3')
        outdirs = ["90-227-13416-24487", "90-227-24487-13591", "90-227-13591-24662"]
        for outdir in outdirs:
            assert os.path.isdir(outdir)

def test_unaligned_frames(tmpdir):
    with run_in(tmpdir):
        os.system('prep_stack -p 83 -f 374 -s 2021-09-04 -n 1')
        procdir = "83-374-39530-28634"
        datadir = "tmp-data-83"
        assert os.path.isdir(procdir)
        assert os.path.isfile(f'{datadir}/download-links.txt')
        with open(f'{datadir}/download-links.txt') as f:
            links = f.read()
        assert 'S1A_IW_SLC__1SDH_20210904T092848_20210904T092916_039530_04ABED_6AC5' in links
        assert 'S1B_IW_SLC__1SDH_20210910T092747_20210910T092817_028634_036ADB_B496' in links
        assert 'S1B_IW_SLC__1SDH_20210910T092814_20210910T092842_028634_036ADB_2401' in links

