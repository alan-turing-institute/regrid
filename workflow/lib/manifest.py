import logging
from pathlib import Path

import xarray as xr
from tqdm import tqdm

from workflow.lib.io import ensure_parent, resolve_netcdf_inputs

LOGGER = logging.getLogger(__name__)


def write_manifest(
    config: dict,
    surface_paths: list[str],
    atmos_paths: list[str],
    output: str,
) -> None:
    LOGGER.info("Writing manifest to %s", output)
    ensure_parent(output)
    surface_files = resolve_netcdf_inputs(surface_paths)
    atmos_files = resolve_netcdf_inputs(atmos_paths)
    LOGGER.info(
        "Manifest inputs: surface=%s atmos=%s", len(surface_files), len(atmos_files)
    )
    surface = xr.open_dataset(surface_files[0])
    atmos = xr.open_dataset(atmos_files[0])
    surface_vars = config["selection"]["surface_variables"]
    atmos_vars = config["selection"]["atmos_variables"]
    all_files = surface_files + atmos_files
    files_by_var = {
        variable: sum(path.parent.name == variable for path in all_files)
        for variable in tqdm(
            surface_vars + atmos_vars,
            desc="summarize manifest files",
            unit="var",
            leave=False,
        )
    }
    lines = [
        "CMIP6 preprocessing manifest",
        f"cmip6 root: {config['cmip6']['root']}",
        f"activity_id: {config['cmip6']['activity_id']}",
        f"institution_id: {config['cmip6']['institution_id']}",
        f"source_id: {config['cmip6']['source_id']}",
        f"experiment_id: {config['cmip6']['experiment_id']}",
        f"member_id: {config['cmip6']['member_id']}",
        f"grid_label: {config['cmip6']['grid_label']}",
        f"version: {config['cmip6'].get('version', 'latest')}",
        f"surface files first: {surface_files[0]}",
        f"surface files: {len(surface_files)}",
        f"atmos files first: {atmos_files[0]}",
        f"atmos files: {len(atmos_files)}",
        f"time range: {config['selection']['time_start']} -> {config['selection']['time_end']}",
        f"time window: {config['selection'].get('time_window', 'single output')}",
        f"surface vars: {', '.join(surface_vars)}",
        f"atmos vars: {', '.join(atmos_vars)}",
        "files by variable: "
        + ", ".join(f"{variable}={count}" for variable, count in files_by_var.items()),
        f"levels Pa: {', '.join(str(int(v)) for v in atmos.plev.values)}",
        f"grid: lat={surface.sizes['lat']} lon={surface.sizes['lon']}",
        f"engine: {config['regridding']['engine']}",
        f"method: {config['regridding']['method']}",
    ]
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOGGER.info("Finished writing manifest to %s", output)
