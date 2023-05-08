# isce2grimp
[ISCE2](https://github.com/isce-framework/isce2) Processing for [GrIMP](https://nsidc.org/grimp)

## Install

```
(or git@github.com:scottyhq/isce2grimp.git)
git clone https://github.com/scottyhq/isce2grimp.git
cd isce2grimp
conda create --name isce2grimp --file conda-linux.lock
conda activate isce2grimp
poetry install
```

## Run

Process an ISCE frame & output range-doppler product w/ metadata required for GrIMP workflows.

Default ISCE processing parameters are in [template.yml](isce2grimp/data/template.yml)

#### Periodically update the sentinel1 inventory from ASF
```
update_inventory
```

#### Query the local inventory (fast compared to remote ASF API query):
```
query_inventory -p 83 -s 2019-01-01 -e 2021-01-01 -f 368
```

#### Single self-contained pair w/ download links in folder
```
# prep_isce -p RELORB -f FRAME_ID -r [REFERENCE_ABSORB] -s [SECONDARY_ABSORB]
prep_pair -p 90 -f 227 -r 13416 -s 24487
```

#### Sequence of 'n' pairs starting with reference orbit
```
prep_stack -p 90 -f 227 -r 13416 -n 3
# NOTE: after running prep_stack, download shared zip files:
cd tmp-data-90
wget -nc -c -i download-links.txt
```

#### RUN ISCE (in ifg folder created by prep_isce 90-227-13416-24487
```
run_isce -i 90-227-13416-24487
```

#### convert existing isce output for downstream GRIMP processing
```
convert_isce -i 90-227-13416-24487 -o 90-227-13416-24487-out
```

#### clean up after ourselves
```
clean_isce -i 90-227-13416-24487
```

## Develop

Follow these instructions if you want to make changes to the code

Work on a new 'feature' branch from current main branch
```
cd isce2grimp
git checkout main
git pull
git checkout -b newfeature
```

Install development version of current branch
```
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

You can pass a [yml template](./isce2grimp/data/template-noion.yml) to customize any topsApp.py options, for example do not perform an ionospheric correction.
```
prep_stack -p 83 -f 374 -s 2021-09-04 -n 1 -t /path/to/template-noion.yml
```

#### To run ISCE scripts such as mdx.py for visualizing results, first update the system $PATH

```
export ISCE_HOME=$CONDA_PREFIX/lib/python3.9/site-packages/isce
export PATH=$PATH:${ISCE_HOME}/bin:${ISCE_HOME}/applications

mdx.py filt_topophase.unw
```
