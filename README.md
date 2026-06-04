# regrid

A Snakemake pipeline for pre-processing CMIP6 climate model data. Given a set of CMIP6 variables and a time range, the pipeline subsets, interpolates, and regrids the data to a target grid.

## What it does

The pipeline runs in four main stages for each variable and time window:

1. **Subset** — extracts the relevant time slice from CMIP6 NetCDF files
2. **Interpolate** (atmospheric variables only) — re-interpolates from native pressure levels to target levels
3. **Regrid** — re-projects data to a target lat/lon grid using either xarray linear interpolation or xESMF
4. **Manifest** — writes a summary file describing the processed outputs

Surface and atmospheric variables are handled as separate branches and can be processed in parallel. Intermediate subset files are marked temporary and cleaned up automatically.

## Installation

The pipeline uses a conda environment defined in `environment.yml`. [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html) is recommended for fast installs:

```bash
micromamba env create -f environment.yml
micromamba activate regrid
```

Or with conda:

```bash
conda env create -f environment.yml
conda activate regrid
```

Key dependencies include Python 3.12, xarray, dask, scipy, netCDF4, and optionally xESMF for conservative/bilinear regridding.

## Configuration

Copy and edit the example config before running:

```bash
cp config/preprocess.example.yaml config/preprocess.yaml
```

The config file controls:

- **`cmip6`** — path to the CMIP6 data root and DRS identifiers (activity, institution, source, experiment, member, etc.)
- **`selection`** — time range, variables to process, target pressure levels, and optional time window frequency
- **`regridding`** — regridding engine (`xarray_interp` or `xesmf`), method, and target grid (either `resolution_degrees` or explicit lat/lon counts)
- **`runtime`** — dask chunking, weight caching, log level
- **`outputs`** — paths for intermediate and final outputs

## Running the pipeline

Run with Snakemake from the repo root:

```bash
snakemake --cores 4
```

To do a dry run first:

```bash
snakemake --cores 4 --dry-run
```

To use more parallelism, increase `--cores`. Each regrid rule uses 4 threads internally.

### Output structure

```
build/
  surface.regridded/{var}/{var}_{window}.{resolution}.regridded.nc
  atmos.regridded/{var}/{var}_{window}.{resolution}.regridded.nc
  preprocess_manifest.txt
logs/
  subset_surface/, subset_atmos/, interpolate_levels/
  regrid_surface/, regrid_atmos/
  manifest.log
```

## Running tests

```bash
python -m unittest discover tests
```

Tests create a synthetic CMIP6 directory structure and exercise the full pipeline end-to-end, including subsetting, interpolation, regridding, and manifest generation.
