# isce2gimp
ISCE Processing for GIMP

## Install

This code is designed to run on APL servers. To install, you need access to the private isce2gimp respository and a [GitHub personal access token (PAT)](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token).

```
git clone https://github.com/scottyhq/isce2gimp.git
conda env create
conda activate isce2gimp
```

## Run

Process an ISCE frame & output range-doppler product w/ metadata required for GIMP workflows.

At a minimum the following inputs are necessary. default is to re-download SLCs, precise orbits, and use
dem and other settings specified in template.yml

```
# prep_isce -p RELORB -f FRAME_ID -y YEAR -m MONTH -r [REFERENCE_ABSORB] -s [SECONDARY_ABSORB] 
* NOTE: relies on ASF metadata being pre-dowloaded. Go to ./isce2gimp/data and run `get_inventory_asf.py`
# NOTE: if -r and -s not specified, the earliest sequential acquisitions in inventory will be used
prep_isce -p 90 -f 227 -y 2018 -m 11

# RUN ISCE (in ifg folder created by prep_isce 90-227-13416-24487
run_isce -i 90-227-13416-24487

# convert existing isce output
convert_isce -c -i 90-227-13416-24487 -o 90-227-13416-24487-out

# clean up after ourselves
clean_isce -i 90-227-13416-24487
```

## Develop

```
poetry install
poetry run pytest -o markers=network
```
