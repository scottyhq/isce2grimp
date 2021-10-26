# isce2gimp
ISCE Processing for GIMP

## Install

This code is designed to run on APL servers. To install, you need access to the private isce2gimp respository and a [GitHub personal access token (PAT)](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token).

```
git clone git@github.com:scottyhq/isce2gimp.git
cd isce2gimp
conda env create
conda activate isce2gimp
```

## Run

Process an ISCE frame & output range-doppler product w/ metadata required for GIMP workflows.

At a minimum the following inputs are necessary. default is to re-download SLCs, precise orbits, and use
dem and other settings specified in template.yml

```
# Periodically update the sentinel1 inventory from ASF
update_inventory

# Single self-contained pair w/ download links in folder
# prep_isce -p RELORB -f FRAME_ID -r [REFERENCE_ABSORB] -s [SECONDARY_ABSORB]
prep_pair -p 90 -f 227 -r 13416 -s 24487

# Sequence of 'n' pairs starting with reference orbit
prep_stack -p 90 -f 227 -r 13416 -n 3
# NOTE: after running prep_stack, download shared zip files:
cd tmp-data-90
wget -nc -c -i download-links.txt

# RUN ISCE (in ifg folder created by prep_isce 90-227-13416-24487
run_isce -i 90-227-13416-24487

# convert existing isce output
convert_isce -i 90-227-13416-24487 -o 90-227-13416-24487-out

# clean up after ourselves
clean_isce -i 90-227-13416-24487
```

## Develop

Follow these instructions if you want to make changes to the code

Work on a new 'feature' branch from current main branch
```
cd isce2gimp
git checkout main
git pull
git checkout -b newfeature
```

```
# Use a lock file to recreate the exact conda environment
conda create --name isce2gimp --file conda-linux.lock
# Install development version of current branch
poetry install
```

run tests
```
poetry run pytest -o markers=network
```

push changes on new branch to github, create a pull request to merge into 'main' branch
```
git add [newfiles]
git commit -m "some new things"
git push
```


## Notes

#### Use a template.yml to customize processing options

You can pass a [yml template](isce2gimp/data/template-noion.yml) to customize any topsApp.py options, for example do not perform an ionospheric correction.
```
prep_stack -p 83 -f 374 -s 2021-09-04 -n 1 -t /path/to/template-noion.yml
```

#### To run ISCE scripts such as mdx.py for visualizing results, first update the system $PATH

NOTE: this is for ian's environment
```
export ISCE_HOME=/home/ian/anaconda3/envs/isce2gimp/lib/python3.9/site-packages/isce
export PATH=$PATH:${ISCE_HOME}/bin:${ISCE_HOME}/applications

mdx.py filt_topophase.unw
```
