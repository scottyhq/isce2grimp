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

@pytest.mark.skip
def test_prep_stack(tmpdir):
    with run_in(tmpdir):
        os.system('prep_stack -p 90 -f 227 -r 13416')
        outdir = "90-227-13416-24487"
        assert os.path.isdir(outdir)
        assert os.path.isfile(f'{outdir}/download-links.txt')
        assert os.path.isfile(f'{outdir}/topsApp.xml')


