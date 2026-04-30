#!/usr/bin/env python3

import sys
from copy import deepcopy
from optparse import OptionParser
from pathlib import Path
import logging

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import libkomwm

FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)
log = logging.getLogger('test_drules_gen')
log.setLevel(logging.INFO)

styles = {
    'default_light':  ['styles/default/light/style.mapcss',  'styles/default/include'],
    'default_dark':   ['styles/default/dark/style.mapcss',   'styles/default/include'],
    'outdoors_light': ['styles/outdoors/light/style.mapcss', 'styles/outdoors/include'],
    'outdoors_dark':  ['styles/outdoors/dark/style.mapcss',  'styles/outdoors/include'],
    'vehicle_light':  ['styles/vehicle/light/style.mapcss',  'styles/vehicle/include'],
    'vehicle_dark':   ['styles/vehicle/dark/style.mapcss',   'styles/vehicle/include'],
}


def output_name(options, style_name):
    return options.name_prefix + style_name


def full_styles_regenerate(options):
    log.info("Start generating styles")
    Path(options.outdir).mkdir(parents=True, exist_ok=True)
    libkomwm.MULTIPROCESSING = False
    prio_ranges_orig = deepcopy(libkomwm.prio_ranges)

    for name, (style_path, include_path) in styles.items():
        generated_name = output_name(options, name)
        log.info(f"Generating {generated_name} style ...")

        # Restore initial state
        libkomwm.prio_ranges = deepcopy(prio_ranges_orig)
        libkomwm.visibilities = {}

        options.filename = options.data + '/' + style_path
        options.priorities_path = options.data + '/' + include_path
        options.outfile = options.outdir + '/' + generated_name

        # Run generation
        libkomwm.komap_mapswithme(options)


def compare_content(file_a_path: str, file_b_path: str, binary=True) -> bool:
    mode = "rb" if binary else "rt"
    with open(file_a_path, mode) as file_a_obj, open(file_b_path, mode) as file_b_obj:
        return file_a_obj.read() == file_b_obj.read()


def compare_with_baseline(generated_dir, baseline_dir, options):
    has_any_diff = False
    suffixes = [(".bin", True)]
    if options.txt:
        suffixes.append((".txt", False))

    for style_name in styles:
        generated_name = output_name(options, style_name)
        for suffix, binary in suffixes:
            generated = f"{generated_dir}/{generated_name}{suffix}"
            baseline = f"{baseline_dir}/{generated_name}{suffix}"
            match = compare_content(generated, baseline, binary=binary)
            if not match:
                log.warning(f"File {generated_name}{suffix} doesn't match {baseline}")
                has_any_diff = True

    if not has_any_diff:
        log.info("All generated files match")

    return not has_any_diff


def main():
    parser = OptionParser()
    parser.add_option("-d", "--data-path", dest="data",
                      help="path to mapcss-mapping.csv and other files", metavar="PATH")
    parser.add_option("-o", "--output-dir", dest="outdir", default="drules",
                      help="output directory", metavar="DIR")
    parser.add_option("-f", "--minzoom", dest="minzoom", default=0, type="int",
                      help="minimal available zoom level", metavar="ZOOM")
    parser.add_option("-t", "--maxzoom", dest="maxzoom", default=None, type="int",
                      help="maximal available zoom level", metavar="ZOOM")
    parser.add_option("-x", "--txt", dest="txt", action="store_true",
                      help="create a text file for output", default=False)
    parser.add_option("", "--name-prefix", dest="name_prefix", default="",
                      help="prefix generated drules filenames, e.g. drules_proto_ for Organic Maps baselines",
                      metavar="PREFIX")
    parser.add_option("", "--compare-baseline", dest="baseline_dir",
                      help="compare generated .bin/.txt files with baseline files from DIR",
                      metavar="DIR")
    parser.add_option("", "--compatibility-profile", dest="compatibility_profile",
                      help="compatibility preset: " + ", ".join(libkomwm.compatibility_profile_names()),
                      default=libkomwm.COMPATIBILITY_PROFILE, metavar="PROFILE")
    parser.add_option("", "--runtime-condition-mode", dest="runtime_condition_mode",
                      help="override runtime condition mode: organicmaps, comaps, mapsme, or mapsme-fallback",
                      default=None, metavar="MODE")

    (options, args) = parser.parse_args()

    if options.data is None:
        parser.error("Please specify base 'data' path.")

    if options.outdir is None:
        parser.error("Please specify base output path.")

    try:
        compatibility = libkomwm.build_compatibility_config(
            options.compatibility_profile,
            runtime_condition_mode=options.runtime_condition_mode
        )
    except ValueError as e:
        parser.error(str(e))
    options.priority_mode = compatibility.priority_mode
    options.runtime_condition_mode = compatibility.runtime_condition_mode
    options.maxzoom = libkomwm.resolve_default_maxzoom(options.maxzoom, compatibility=compatibility)

    full_styles_regenerate(options)
    if options.baseline_dir:
        if not compare_with_baseline(options.outdir, options.baseline_dir, options):
            raise SystemExit("Generated drules differ from baseline.")
    log.info("Done!")

if __name__ == '__main__':
    main()
