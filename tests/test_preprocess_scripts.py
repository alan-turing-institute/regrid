import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import xarray as xr
import yaml

from workflow.lib import cmip6
from workflow.lib.grid import decreasing_lat, regridding_label, target_grid
from workflow.lib.processing import assert_no_nans
from workflow.lib.windows import time_windows


def write_config(path: Path, root: Path) -> None:
    config = {
        "cmip6": {
            "root": str(root),
            "activity_id": "CMIP",
            "institution_id": "MPI-M",
            "source_id": "MPI-ESM1-2-HR",
            "experiment_id": "1pctCO2",
            "member_id": "r1i1p1f1",
            "grid_label": "gn",
            "version": "latest",
            "table_id_by_variable": {
                "tas": "6hrPlev",
                "ta": "6hrPlev",
            },
        },
        "selection": {
            "time_start": "1850-01-01T06:00:00",
            "time_end": "1850-01-02T00:00:00",
            "time_window": "12H",
            "time_label_format": "%Y%m%d%H%M",
            "surface_variables": ["tas"],
            "atmos_variables": ["ta"],
            "pressure_levels_pa": [30000.0, 50000.0, 85000.0, 100000.0],
        },
        "regridding": {
            "engine": "xarray_interp",
            "method": "bilinear",
            "periodic": True,
            "target_lat_start": -45.0,
            "target_lat_stop": 45.0,
            "target_lat_count": 3,
            "target_lon_start": 0.0,
            "target_lon_stop": 180.0,
            "target_lon_count": 4,
        },
        "runtime": {
            "chunks": {},
            "keep_weights": True,
            "weights_dir": str(path.parent / "weights"),
        },
        "outputs": {
            "surface_subset": "build/surface.subset",
            "atmos_subset": "build/atmos.subset",
            "atmos_levels": "build/atmos.levels",
            "surface_regridded": "build/surface.regridded",
            "atmos_regridded": "build/atmos.regridded",
            "manifest": "build/preprocess_manifest.txt",
        },
    }
    path.write_text(yaml.safe_dump(config))


def write_cmip6_file(
    root: Path,
    variable: str,
    data: xr.DataArray,
    time_range: str = "185001010600-185001020000",
) -> Path:
    var_dir = (
        root
        / "CMIP"
        / "MPI-M"
        / "MPI-ESM1-2-HR"
        / "1pctCO2"
        / "r1i1p1f1"
        / "6hrPlev"
        / variable
        / "gn"
        / "latest"
    )
    var_dir.mkdir(parents=True, exist_ok=True)
    path = (
        var_dir / f"{variable}_6hrPlev_MPI-ESM1-2-HR_1pctCO2_r1i1p1f1_gn_"
        f"{time_range}.nc"
    )
    xr.Dataset({variable: data}).to_netcdf(path)
    return path


def run_script(script: str, *args: str) -> None:
    subprocess.run(
        ["python", Path("workflow/scripts") / script, *args],
        check=True,
    )


class PreprocessScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.config = self.work / "preprocess.yaml"
        self.cmip6_root = self.work / "cmip6"
        write_config(self.config, self.cmip6_root)

        time = np.array(
            ["1850-01-01T06:00:00", "1850-01-01T12:00:00", "1850-01-01T18:00:00"],
            dtype="datetime64[ns]",
        )
        lat = np.array([45.0, -45.0])
        lon = np.array([0.0, 180.0])
        plev = np.array([40000.0, 90000.0])

        tas = xr.DataArray(
            np.arange(time.size * lat.size * lon.size).reshape(
                time.size, lat.size, lon.size
            ),
            dims=("time", "lat", "lon"),
            coords={"time": time, "lat": lat, "lon": lon},
        )
        ta = xr.DataArray(
            np.arange(time.size * plev.size * lat.size * lon.size).reshape(
                time.size, plev.size, lat.size, lon.size
            ),
            dims=("time", "plev", "lat", "lon"),
            coords={"time": time, "plev": plev, "lat": lat, "lon": lon},
        )
        write_cmip6_file(self.cmip6_root, "tas", tas)
        write_cmip6_file(self.cmip6_root, "ta", ta)
        write_cmip6_file(self.cmip6_root, "ta", ta, "201001010600-201501010000")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_target_grid_can_be_defined_by_resolution(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["regridding"]["resolution_degrees"] = 0.25
        config["regridding"]["target_lat_start"] = 90.0
        config["regridding"]["target_lat_stop"] = -90.0
        config["regridding"]["target_lon_start"] = 0.0
        config["regridding"]["target_lon_stop"] = 359.75

        grid = target_grid(config)

        self.assertEqual(grid.sizes["lat"], 721)
        self.assertEqual(grid.sizes["lon"], 1440)
        np.testing.assert_allclose(grid.lat[[0, -1]].values, [90.0, -90.0])
        np.testing.assert_allclose(grid.lon[[0, -1]].values, [0.0, 359.75])
        self.assertEqual(regridding_label(config), "0p25deg")

    def test_decreasing_lat_orders_latitudes_north_to_south(self) -> None:
        ds = xr.Dataset(
            {"tas": xr.DataArray([1.0, 2.0, 3.0], dims=("lat",))},
            coords={"lat": [-45.0, 0.0, 45.0]},
        )

        ordered = decreasing_lat(ds)

        self.assertEqual(ordered.lat.values.tolist(), [45.0, 0.0, -45.0])
        self.assertEqual(ordered.tas.values.tolist(), [3.0, 2.0, 1.0])

    def test_assert_no_nans_reports_variable_counts(self) -> None:
        ds = xr.Dataset(
            {
                "tas": xr.DataArray([1.0, np.nan, 3.0], dims=("time",)),
                "psl": xr.DataArray([np.nan, np.nan, 2.0], dims=("time",)),
            }
        )

        with self.assertRaisesRegex(
            ValueError, r"NaNs found in test step: tas: 1, psl: 2"
        ):
            assert_no_nans(ds, "test step")

    def test_cmip6_variable_files_only_returns_files_overlapping_window(self) -> None:
        config = yaml.safe_load(self.config.read_text())

        files = cmip6.variable_files(
            config,
            "ta",
            "1850-01-01T06:00:00",
            "1850-01-01T18:00:00",
        )

        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("185001010600-185001020000.nc"))

    def test_time_windows_are_stable_when_time_range_shrinks(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["selection"]["time_end"] = "1850-01-03T06:00:00"
        config["selection"]["time_window"] = "1D"

        original = time_windows(config)
        config["selection"]["time_end"] = "1850-01-02T06:00:00"
        shortened = time_windows(config)

        self.assertEqual(shortened, original[:1])
        self.assertEqual(shortened[0]["include_end"], "false")

    def test_time_windows_only_add_missing_windows_when_time_range_expands(
        self,
    ) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["selection"]["time_end"] = "1850-01-03T06:00:00"
        config["selection"]["time_window"] = "1D"

        original = time_windows(config)
        config["selection"]["time_end"] = "1850-01-04T06:00:00"
        expanded = time_windows(config)

        self.assertEqual(expanded[: len(original)], original)
        self.assertEqual(
            expanded[-1],
            {
                "label": "185001030600_185001040600",
                "start": "1850-01-03T06:00:00",
                "end": "1850-01-04T06:00:00",
                "include_end": "false",
            },
        )

    def test_subset_variable_reads_standard_cmip6_layout_and_writes_one_variable(
        self,
    ) -> None:
        output = self.work / "subset/tas/tas_185001010600_185001011800.nc"
        run_script(
            "subset_variable.py",
            "--config",
            str(self.config),
            "--kind",
            "surface",
            "--variable",
            "tas",
            "--window-start",
            "1850-01-01T06:00:00",
            "--window-end",
            "1850-01-01T18:00:00",
            "--include-window-end",
            "false",
            "--output",
            str(output),
        )

        ds = xr.open_dataset(output)
        self.assertEqual(list(ds.data_vars), ["tas"])
        self.assertEqual(ds.sizes["time"], 2)
        self.assertEqual(ds.lat.values.tolist(), [-45.0, 45.0])

    def test_interpolate_regrid_and_manifest_single_purpose_scripts(self) -> None:
        subset = self.work / "subset/ta/ta_185001010600_185001011800.nc"
        levels = self.work / "levels/ta/ta_185001010600_185001011800.nc"
        regridded = self.work / "regridded/ta/ta_185001010600_185001011800.regridded.nc"
        manifest = self.work / "manifest.txt"

        run_script(
            "subset_variable.py",
            "--config",
            str(self.config),
            "--kind",
            "atmos",
            "--variable",
            "ta",
            "--window-start",
            "1850-01-01T06:00:00",
            "--window-end",
            "1850-01-01T18:00:00",
            "--include-window-end",
            "false",
            "--output",
            str(subset),
        )
        run_script(
            "interpolate_levels.py",
            "--config",
            str(self.config),
            "--input",
            str(subset),
            "--output",
            str(levels),
        )
        level_ds = xr.open_dataset(levels)
        self.assertEqual(
            level_ds.plev.values.tolist(), [30000.0, 50000.0, 85000.0, 100000.0]
        )
        np.testing.assert_allclose(
            level_ds.ta.isel(time=0, lat=0, lon=0).values,
            [1.2, 2.8, 5.6, 6.8],
        )
        run_script(
            "regrid_variable.py",
            "--config",
            str(self.config),
            "--kind",
            "atmos",
            "--variable",
            "ta",
            "--input",
            str(levels),
            "--output",
            str(regridded),
        )
        run_script(
            "write_manifest.py",
            "--config",
            str(self.config),
            "--surface",
            str(regridded),
            "--atmos",
            str(regridded),
            "--output",
            str(manifest),
        )

        ds = xr.open_dataset(regridded)
        self.assertEqual(ds.sizes["plev"], 4)
        self.assertEqual(ds.sizes["lat"], 3)
        self.assertEqual(ds.sizes["lon"], 4)
        self.assertGreater(float(ds.lat[0]), float(ds.lat[-1]))
        text = manifest.read_text()
        self.assertIn("CMIP6 preprocessing manifest", text)
        self.assertIn("files by variable:", text)


if __name__ == "__main__":
    unittest.main()
