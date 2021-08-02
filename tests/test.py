"""Tests for querying ASF archive."""
from dinosar.archive import asf
import pytest
import requests
import os
import geopandas as gpd
import contextlib


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


@pytest.mark.network
def test_query_asf(tmpdir):
    with run_in(tmpdir):
        asf.query_asf([0.611, 1.048, -78.196, -77.522], "S1A")
        asf.query_asf([0.611, 1.048, -78.196, -77.522], "S1B")
        assert os.path.isfile("query_S1A.json")
        assert os.path.isfile("query_S1B.json")


@pytest.mark.network
def test_get_list():
    """Check retrieving specific frame information in inventory."""
    baseurl = "https://api.daac.asf.alaska.edu/services/search/param"
    granules = [
        "S1B_IW_SLC__1SDV_20171117T015310_20171117T015337_008315_00EB6C_40CA",
        "S1A_IW_SLC__1SSV_20150526T015345_20150526T015412_006086_007E23_34D6",
    ]
    paramDict = dict(granule_list=granules, output="json")
    r = requests.get(baseurl, params=paramDict, verify=True, timeout=(5, 10))
    print(r.url)
    print(r.status_code)
    assert r.status_code == 200

