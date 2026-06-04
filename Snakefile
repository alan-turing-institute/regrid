from workflow.lib import cmip6
from workflow.lib.grid import regridding_label
from workflow.lib.windows import time_windows


configfile: "config/preprocess.yaml"

for key in ("time_start", "time_end", "time_window", "time_label_format"):
    if key in config:
        config["selection"][key] = config[key]


WINDOWS = time_windows(config)
WINDOW_LABELS = [window["label"] for window in WINDOWS]
WINDOW_BY_LABEL = {window["label"]: window for window in WINDOWS}
SURFACE_VARS = config["selection"]["surface_variables"]
ATMOS_VARS = config["selection"]["atmos_variables"]
CONFIG_FILE = "config/preprocess.yaml"
LOG_LEVEL = config.get("runtime", {}).get("log_level", "INFO")


RESOLUTION_LABEL = regridding_label(config)


def cmip6_variable_files(variable, window):
    return cmip6.variable_files(config, variable, window["start"], window["end"])

SURFACE_REGRIDDED = expand(
    config["outputs"]["surface_regridded"] + "/{var}/{var}_{window}.{resolution}.regridded.nc",
    var=SURFACE_VARS,
    window=WINDOW_LABELS,
    resolution=[RESOLUTION_LABEL],
)
ATMOS_REGRIDDED = expand(
    config["outputs"]["atmos_regridded"] + "/{var}/{var}_{window}.{resolution}.regridded.nc",
    var=ATMOS_VARS,
    window=WINDOW_LABELS,
    resolution=[RESOLUTION_LABEL],
)
MANIFEST_OUT = config["outputs"]["manifest"]


rule all:
    input:
        SURFACE_REGRIDDED,
        ATMOS_REGRIDDED,
        MANIFEST_OUT,


rule subset_surface_variable:
    input:
        data=lambda wc: cmip6_variable_files(wc.var, WINDOW_BY_LABEL[wc.window])
    output:
        temp(config["outputs"]["surface_subset"] + "/{var}/{var}_{window}.nc")
    log:
        "logs/subset_surface/{var}_{window}.log"
    params:
        cfg=CONFIG_FILE,
        start=lambda wc: WINDOW_BY_LABEL[wc.window]["start"],
        end=lambda wc: WINDOW_BY_LABEL[wc.window]["end"],
        include_end=lambda wc: WINDOW_BY_LABEL[wc.window]["include_end"],
        log_level=LOG_LEVEL,
    threads: 2
    shell:
        """
        mkdir -p logs/subset_surface
        python workflow/scripts/subset_variable.py \
          --config {params.cfg} \
          --kind surface \
          --variable {wildcards.var} \
          --window-start {params.start} \
          --window-end {params.end} \
          --include-window-end {params.include_end} \
          --output {output} \
          --log-level {params.log_level} \
          > {log} 2>&1
        """


rule subset_atmos_variable:
    input:
        data=lambda wc: cmip6_variable_files(wc.var, WINDOW_BY_LABEL[wc.window])
    output:
        temp(config["outputs"]["atmos_subset"] + "/{var}/{var}_{window}.nc")
    log:
        "logs/subset_atmos/{var}_{window}.log"
    params:
        cfg=CONFIG_FILE,
        start=lambda wc: WINDOW_BY_LABEL[wc.window]["start"],
        end=lambda wc: WINDOW_BY_LABEL[wc.window]["end"],
        include_end=lambda wc: WINDOW_BY_LABEL[wc.window]["include_end"],
        log_level=LOG_LEVEL,
    threads: 2
    shell:
        """
        mkdir -p logs/subset_atmos
        python workflow/scripts/subset_variable.py \
          --config {params.cfg} \
          --kind atmos \
          --variable {wildcards.var} \
          --window-start {params.start} \
          --window-end {params.end} \
          --include-window-end {params.include_end} \
          --output {output} \
          --log-level {params.log_level} \
          > {log} 2>&1
        """


rule interpolate_atmos_levels:
    input:
        data=config["outputs"]["atmos_subset"] + "/{var}/{var}_{window}.nc"
    output:
        temp(config["outputs"]["atmos_levels"] + "/{var}/{var}_{window}.nc")
    log:
        "logs/interpolate_levels/{var}_{window}.log"
    params:
        cfg=CONFIG_FILE,
        log_level=LOG_LEVEL,
    threads: 2
    shell:
        """
        mkdir -p logs/interpolate_levels
        python workflow/scripts/interpolate_levels.py \
          --config {params.cfg} \
          --input {input.data} \
          --output {output} \
          --log-level {params.log_level} \
          > {log} 2>&1
        """


rule regrid_surface:
    input:
        data=config["outputs"]["surface_subset"] + "/{var}/{var}_{window}.nc"
    output:
        config["outputs"]["surface_regridded"] + "/{var}/{var}_{window}.{resolution}.regridded.nc"
    log:
        "logs/regrid_surface/{var}_{window}.{resolution}.log"
    wildcard_constraints:
        resolution=RESOLUTION_LABEL
    params:
        cfg=CONFIG_FILE,
        log_level=LOG_LEVEL,
    threads: 4
    shell:
        """
        mkdir -p logs/regrid_surface
        python workflow/scripts/regrid_variable.py \
          --config {params.cfg} \
          --kind surface \
          --variable {wildcards.var} \
          --input {input.data} \
          --output {output} \
          --log-level {params.log_level} \
          > {log} 2>&1
        """


rule regrid_atmos:
    input:
        data=config["outputs"]["atmos_levels"] + "/{var}/{var}_{window}.nc"
    output:
        config["outputs"]["atmos_regridded"] + "/{var}/{var}_{window}.{resolution}.regridded.nc"
    log:
        "logs/regrid_atmos/{var}_{window}.{resolution}.log"
    wildcard_constraints:
        resolution=RESOLUTION_LABEL
    params:
        cfg=CONFIG_FILE,
        log_level=LOG_LEVEL,
    threads: 4
    shell:
        """
        mkdir -p logs/regrid_atmos
        python workflow/scripts/regrid_variable.py \
          --config {params.cfg} \
          --kind atmos \
          --variable {wildcards.var} \
          --input {input.data} \
          --output {output} \
          --log-level {params.log_level} \
          > {log} 2>&1
        """


rule manifest:
    input:
        surface=SURFACE_REGRIDDED,
        atmos=ATMOS_REGRIDDED
    output:
        MANIFEST_OUT
    log:
        "logs/manifest.log"
    params:
        cfg=CONFIG_FILE,
        time_start=config["selection"]["time_start"],
        time_end=config["selection"]["time_end"],
        time_window=config["selection"].get("time_window", ""),
        log_level=LOG_LEVEL,
    shell:
        """
        mkdir -p logs
        python workflow/scripts/write_manifest.py \
          --config {params.cfg} \
          --surface {input.surface} \
          --atmos {input.atmos} \
          --time-start {params.time_start} \
          --time-end {params.time_end} \
          --time-window {params.time_window} \
          --output {output} \
          --log-level {params.log_level} \
          > {log} 2>&1
        """
