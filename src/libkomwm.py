# ruff: noqa: F405
from mapcss import MapCSS
from optparse import OptionParser
import os
import csv
import functools
from dataclasses import dataclass, replace
from sys import exit
from multiprocessing import Pool, set_start_method
from collections import OrderedDict
import mapcss.webcolors
from drules_struct_pb2 import *  # noqa: F403

whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex
whatever_to_cairo = mapcss.webcolors.webcolors.whatever_to_cairo

PROFILE = False
MULTIPROCESSING = True
RUNTIME_CONDITION_MODE = 'organicmaps'
PRIORITY_MODE = 'priority_files'
DEFAULT_MAXZOOM = 20
MAPSME_DEFAULT_MAXZOOM = 19


@dataclass(frozen=True)
class CompatibilityConfig:
    name: str
    priority_mode: str
    runtime_condition_mode: str
    default_maxzoom: int
    use_priority_files: bool
    legacy_zindex: bool
    match_all_class_tags: bool
    allow_duplicate_types: bool
    sort_priority_file_rules: bool
    strict_runtime_filtering: bool
    subset_runtime_filtering: bool
    raw_runtime_conditions: bool
    runtime_fallback: bool
    mapsme_legacy_output: bool
    mapsme_2016_text_order: bool = False


COMPATIBILITY_PROFILES = {
    'organicmaps': CompatibilityConfig(
        name='organicmaps',
        priority_mode='priority_files',
        runtime_condition_mode='organicmaps',
        default_maxzoom=DEFAULT_MAXZOOM,
        use_priority_files=True,
        legacy_zindex=False,
        match_all_class_tags=False,
        allow_duplicate_types=False,
        sort_priority_file_rules=True,
        strict_runtime_filtering=True,
        subset_runtime_filtering=False,
        raw_runtime_conditions=False,
        runtime_fallback=False,
        mapsme_legacy_output=False,
    ),
    'comaps': CompatibilityConfig(
        name='comaps',
        priority_mode='priority_files',
        runtime_condition_mode='comaps',
        default_maxzoom=DEFAULT_MAXZOOM,
        use_priority_files=True,
        legacy_zindex=False,
        match_all_class_tags=False,
        allow_duplicate_types=False,
        sort_priority_file_rules=True,
        strict_runtime_filtering=True,
        subset_runtime_filtering=False,
        raw_runtime_conditions=False,
        runtime_fallback=True,
        mapsme_legacy_output=False,
    ),
    'mapsme': CompatibilityConfig(
        name='mapsme',
        priority_mode='mapsme',
        runtime_condition_mode='mapsme',
        default_maxzoom=MAPSME_DEFAULT_MAXZOOM,
        use_priority_files=False,
        legacy_zindex=True,
        match_all_class_tags=True,
        allow_duplicate_types=True,
        sort_priority_file_rules=False,
        strict_runtime_filtering=False,
        subset_runtime_filtering=True,
        raw_runtime_conditions=True,
        runtime_fallback=False,
        mapsme_legacy_output=True,
    ),
    'mapsme-fallback': CompatibilityConfig(
        name='mapsme-fallback',
        priority_mode='mapsme',
        runtime_condition_mode='mapsme-fallback',
        default_maxzoom=MAPSME_DEFAULT_MAXZOOM,
        use_priority_files=False,
        legacy_zindex=True,
        match_all_class_tags=True,
        allow_duplicate_types=True,
        sort_priority_file_rules=False,
        strict_runtime_filtering=False,
        subset_runtime_filtering=True,
        raw_runtime_conditions=True,
        runtime_fallback=True,
        mapsme_legacy_output=True,
    ),
    'omim-2016': CompatibilityConfig(
        name='omim-2016',
        priority_mode='mapsme',
        runtime_condition_mode='mapsme',
        default_maxzoom=MAPSME_DEFAULT_MAXZOOM,
        use_priority_files=False,
        legacy_zindex=True,
        match_all_class_tags=True,
        allow_duplicate_types=True,
        sort_priority_file_rules=False,
        strict_runtime_filtering=False,
        subset_runtime_filtering=True,
        raw_runtime_conditions=True,
        runtime_fallback=False,
        mapsme_legacy_output=True,
        mapsme_2016_text_order=True,
    ),
}

DEFAULT_COMPATIBILITY_PROFILE = 'organicmaps'
COMPATIBILITY_PROFILE = DEFAULT_COMPATIBILITY_PROFILE
COMPATIBILITY = COMPATIBILITY_PROFILES[COMPATIBILITY_PROFILE]


def compatibility_profile_names():
    return tuple(COMPATIBILITY_PROFILES.keys())


def build_compatibility_config(profile_name=None, priority_mode=None, runtime_condition_mode=None):
    if profile_name is None:
        profile_name = DEFAULT_COMPATIBILITY_PROFILE

    if profile_name not in COMPATIBILITY_PROFILES:
        raise ValueError(f'Unknown compatibility profile: {profile_name}')

    config = COMPATIBILITY_PROFILES[profile_name]
    if priority_mode is not None and priority_mode != config.priority_mode:
        if priority_mode not in ('priority_files', 'mapsme'):
            raise ValueError(f'Unknown priority mode: {priority_mode}')
        use_priority_files = priority_mode == 'priority_files'
        config = replace(
            config,
            priority_mode=priority_mode,
            use_priority_files=use_priority_files,
            mapsme_legacy_output=not use_priority_files,
            legacy_zindex=not use_priority_files,
            match_all_class_tags=not use_priority_files,
            allow_duplicate_types=not use_priority_files,
            sort_priority_file_rules=use_priority_files,
            strict_runtime_filtering=use_priority_files,
            subset_runtime_filtering=not use_priority_files,
            mapsme_2016_text_order=False if use_priority_files else config.mapsme_2016_text_order,
            default_maxzoom=DEFAULT_MAXZOOM if use_priority_files else MAPSME_DEFAULT_MAXZOOM,
        )

    if runtime_condition_mode is not None and runtime_condition_mode != config.runtime_condition_mode:
        if runtime_condition_mode not in ('organicmaps', 'comaps', 'mapsme', 'mapsme-fallback'):
            raise ValueError(f'Unknown runtime condition mode: {runtime_condition_mode}')
        config = replace(
            config,
            runtime_condition_mode=runtime_condition_mode,
            raw_runtime_conditions=runtime_condition_mode.startswith('mapsme'),
            runtime_fallback=runtime_condition_mode in ('comaps', 'mapsme-fallback'),
        )

    return config

# Priority values defined in *.prio.txt files are adjusted
# to fit into the following "priorities ranges":
# [-10000; 10000): overlays (icons, captions...)
# [0; 1000)      : FG - foreground areas and lines
# [-1000; 0)     : BG-top - water, linear and areal, rendered just on top of landcover
# (-2000; -1000) : BG-by-size - landcover areas, later in core sorted by their bbox size
# The core renderer then re-adjusts those ranges as necessary to accomodate
# for special behavior and features' layer=* values.
# See drape_frontend/stylist.cpp for the details of layering logic.

# Priority range for area and line drules. Should be same as drule::kLayerPriorityRange.
LAYER_PRIORITY_RANGE = 1000
# Should be same as drule::kOverlaysMaxPriority. The overlays range is [-kOverlaysMaxPriority; kOverlaysMaxPriority),
# negative values are used for optional captions which are below most other overlays.
OVERLAYS_MAX_PRIORITY = 10000

# Drules are arranged into following ranges.
PRIO_OVERLAYS = 'overlays'
PRIO_FG = 'FG'
PRIO_BG_TOP = 'BG-top'
PRIO_BG_BY_SIZE = 'BG-by-size'

prio_ranges = {
    PRIO_OVERLAYS: {'pos': 4, 'base': 0, 'priorities': {}, 'imports': [], 'originalPriorities': {}},
    PRIO_FG: {'pos': 3, 'base': 0, 'priorities': {}, 'imports': [], 'originalPriorities': {}},
    PRIO_BG_TOP: {'pos': 2, 'base': -1000, 'priorities': {}, 'imports': [], 'originalPriorities': {}},
    PRIO_BG_BY_SIZE: {'pos': 1, 'base': -2000, 'priorities': {}, 'imports': [], 'originalPriorities': {}},
}

visibilities = {}

prio_ranges[PRIO_OVERLAYS]['comment'] = f'''
Overlays (icons, captions, path texts and shields) are rendered on top of all the geometry (lines, areas).
Overlays don't overlap each other, instead the ones with higher priority displace the less important ones.
Optional captions (which have an icon) are usually displayed only if there are no other overlays in their way
(technically, max overlays priority value ({OVERLAYS_MAX_PRIORITY}) is subtracted from their priorities automatically).
'''

prio_ranges[PRIO_FG]['comment'] = '''
FG geometry: foreground lines and areas (e.g. buildings) are rendered always below overlays
and always on top of background geometry (BG-top & BG-by-size) even if a foreground feature
is layer=-10 (as tunnels should be visibile over landcover and water).
'''
prio_ranges[PRIO_BG_TOP]['comment'] = '''
BG-top geometry: background lines and areas that should be always below foreground ones
(including e.g. layer=-10 underwater tunnels), but above background areas sorted by size (BG-by-size),
because ordering by size doesn't always work with e.g. water mapped over a forest,
so water should be on top of other landcover always, but linear waterways should be hidden beneath it.
Still, e.g. a layer=-1 BG-top feature will be rendered under a layer=0 BG-by-size feature
(so areal water tunnels are hidden beneath other landcover area) and a layer=1 landcover areas
are displayed above layer=0 BG-top.
'''
prio_ranges[PRIO_BG_BY_SIZE]['comment'] = '''
BG-by-size geometry: background areas rendered below BG-top and everything else.
Smaller areas are rendered above larger ones (area's size is estimated as the size of its' bounding box).
So effectively priority values of BG-by-size areas are not used at the moment.
But we might use them later for some special cases, e.g. to determine a main area type of a multi-type feature.
Keep them in a logical importance order please.
'''

COMMENT_AUTOFORMAT = '''This file is automatically re-formatted and re-sorted in priorities descending order
when generate_drules.sh is run. All comments (automatic priorities of e.g. optional captions, drule types visibilities, etc.)
are generated automatically for information only. Custom formatting and comments are not preserved.
'''

COMMENT_RANGES_OVERVIEW = '''
Priorities ranges' rendering order overview:
- overlays (icons, captions...)
- FG: foreground areas and lines
- BG-top: water (linear and areal)
- BG-by-size: landcover areas sorted by their size
'''

# TODO: Implement better error handling
validation_errors_count = 0

def to_boolean(s):
    s = s.lower()
    if s == "true" or s == "yes":
        return True, True # Valid, True
    elif s == "false" or s == "no":
        return True, False # Valid, False
    else:
        return False, False # Invalid

def mwm_encode_color(colors, st, prefix='', default='black'):
    if prefix:
        prefix += "-"
    opacity = hex(255 - int(255 * float(st.get(prefix + "opacity", 1))))
    # TODO: Refactoring idea: here color is converted from float to hex. While MapCSS class
    #       reads colors from *.mapcss files and converts to float. How about changing MapCSS
    #       to keep hex values and avoid Hex->Float->Hex operations?
    color = whatever_to_hex(st.get(prefix + 'color', default))[1:]
    result = int(opacity + color, 16)
    colors.add(result)
    return result

def mwm_encode_image(st, prefix='icon', bgprefix='symbol'):
    if prefix:
        prefix += "-"
    if bgprefix:
        bgprefix += "-"
    if prefix + "image" not in st:
        return False
    # strip last ".svg"
    handle = st.get(prefix + "image")[:-4]
    # TODO: return `handle` only once
    return handle, handle


def query_style(args):
    global style
    cl, cltags, minzoom, maxzoom = args
    clname = cl if cl.find('-') == -1 else cl[:cl.find('-')]

    cltags["name"] = "name"
    cltags["addr:housenumber"] = "addr:housenumber"
    cltags["addr:housename"] = "addr:housename"
    cltags["ref"] = "ref"
    cltags["int_name"] = "int_name"
    cltags["addr:flats"] = "addr:flats"

    results = []
    for zoom in range(minzoom, maxzoom + 1):
        all_runtime_conditions_arr = []
        # Get runtime conditions which are used for class 'cl' on zoom 'zoom'
        if "area" not in cltags:
            all_runtime_conditions_arr.extend(style.get_runtime_rules(clname, "line", cltags, zoom))
        all_runtime_conditions_arr.extend(style.get_runtime_rules(clname, "area", cltags, zoom))
        if "area" not in cltags:
            all_runtime_conditions_arr.extend(style.get_runtime_rules(clname, "node", cltags, zoom))

        runtime_conditions_arr = runtime_condition_variants(all_runtime_conditions_arr)

        for runtime_conditions in runtime_conditions_arr:
            zstyle = {}
            strict_runtime_filtering = COMPATIBILITY.strict_runtime_filtering
            subset_runtime_filtering = COMPATIBILITY.subset_runtime_filtering

            # Get style for class 'cl' on zoom 'zoom' with corresponding runtime conditions
            if "area" not in cltags:
                linestyle = style.get_style_dict(clname, "line", cltags, zoom, olddict=zstyle,
                                                 filter_by_runtime_conditions=runtime_conditions,
                                                 strict_runtime_filtering=strict_runtime_filtering,
                                                 subset_runtime_filtering=subset_runtime_filtering)
                zstyle = linestyle
            areastyle = style.get_style_dict(clname, "area", cltags, zoom, olddict=zstyle,
                                             filter_by_runtime_conditions=runtime_conditions,
                                             strict_runtime_filtering=strict_runtime_filtering,
                                             subset_runtime_filtering=subset_runtime_filtering)
            has_icons_for_areas = False
            for st in areastyle.values():
                if "icon-image" in st or 'symbol-shape' in st or 'symbol-image' in st:
                    has_icons_for_areas = True
                    break
            zstyle = areastyle
            if "area" not in cltags:
                nodestyle = style.get_style_dict(clname, "node", cltags, zoom, olddict=zstyle,
                                                 filter_by_runtime_conditions=runtime_conditions,
                                                 strict_runtime_filtering=strict_runtime_filtering,
                                                 subset_runtime_filtering=subset_runtime_filtering)
                zstyle = nodestyle

            results.append((cl, zoom, runtime_conditions, list(zstyle.values()), has_icons_for_areas))
    return results


def runtime_condition_variants(runtime_conditions):
    config = COMPATIBILITY
    if config.runtime_condition_mode != RUNTIME_CONDITION_MODE:
        # Preserve direct test/module compatibility when callers still mutate
        # the historical global mode instead of installing a full profile.
        config = build_compatibility_config(config.name, runtime_condition_mode=RUNTIME_CONDITION_MODE)

    if not runtime_conditions:
        # If there is no runtime conditions, do not filter style by runtime conditions.
        return [None]

    if config.raw_runtime_conditions:
        variants = list(runtime_conditions)
        if config.runtime_fallback:
            variants.append(None)
        return variants

    unique_conditions = []
    for new_rt_conditions in runtime_conditions:
        conditions_unique = True
        for rt_conditions in unique_conditions:
            if new_rt_conditions == rt_conditions:
                conditions_unique = False
                break
        if conditions_unique:
            unique_conditions.append(new_rt_conditions)

    if config.runtime_fallback:
        # CoMaps emits a base rule as a fallback in addition to runtime variants.
        unique_conditions.append(None)

    return unique_conditions


def get_priorities_filename(prio_range, path):
    return os.path.join(path, f'priorities_{prio_ranges[prio_range]["pos"]}_{prio_range}.prio.txt')

def load_priorities(prio_range, path, classif, compress = False, level = 0, has_imports = False, skip_imports = False, format_only = False):
    def print_warning(msg):
        print(f'WARNING: {msg} in {fname}:\n\t{line}')

    priority_max = OVERLAYS_MAX_PRIORITY if prio_range == PRIO_OVERLAYS else LAYER_PRIORITY_RANGE
    priority_min = -OVERLAYS_MAX_PRIORITY if prio_range == PRIO_OVERLAYS else 0

    collection_name = 'priorities'
    if level == 0:
        fname = get_priorities_filename(prio_range, path)
        if skip_imports:
            collection_name = 'originalPriorities'
        else:
            load_priorities(prio_range, path, classif, compress, level, has_imports, True, format_only)
    else:
        fname = path

    with open(fname, 'r') as f:
        group = []
        for line in f:
            line = line.strip()
            # Strip comments.
            line = line.split('#', 1)[0].strip()
            if not line:
                continue

            import_parts = line.split("@import(\"")
            if len(import_parts) > 2:
                print_warning('invalid import statement')
                break
            else:
                if len(import_parts) == 2:
                    import_parts = import_parts[1].split("\"")
                    if (len(import_parts) != 2):
                        print_warning('invalid import statement')
                        break
                    else:
                        if skip_imports:
                            continue
                        if (level > 0):
                            file_path = os.path.abspath(os.path.join(path, "..", import_parts[0]))
                        else:
                            file_path = os.path.abspath(os.path.join(path, import_parts[0]))
                        if not os.path.exists(file_path):
                            print_warning('file to import can\'t be found')
                            break
                        else:
                            has_imports = True
                            if level == 0:
                                prio_ranges[prio_range]['imports'].append(import_parts[0])
                            load_priorities(prio_range, file_path, classif, compress, level+1, has_imports, False, format_only)
                            continue

            tokens = line.split()
            if len(tokens) > 2:
                print_warning('skipping malformed line')
                continue
            if tokens[0] == "===":
                try:
                    priority = int(tokens[1])
                except ValueError:
                    print_warning('skipping invalid priority value')
                else:
                    if priority >= priority_min and priority < priority_max:
                        if len(group):
                            for key in group:
                                prio_ranges[prio_range][collection_name][key] = priority
                        else:
                            print_warning('skipping empty priority group')
                    else:
                        print_warning(f'skipping out of [{priority_min};{priority_max}) range priority value')
                group = []
            else:
                cl = tokens[0]
                object_id = ''
                oid_pos = cl.find('::')
                if oid_pos != -1:
                    object_id = cl[oid_pos:]
                    cl = cl[0:oid_pos]
                if not format_only and cl not in classif:
                    print_warning('unknown classificator type')
                key = (cl, object_id)
                if key in prio_ranges[prio_range][collection_name] and not has_imports:
                    print_warning(f'overriding previously set priority value {prio_ranges[prio_range][collection_name][key]}')
                group.append(key)

        if len(group):
            line = group
            print_warning('skipping last types groups with no priority set')

    if prio_range == PRIO_OVERLAYS:
        for key in prio_ranges[PRIO_OVERLAYS][collection_name].keys():
            main_prio_id = None
            if key[1].startswith('caption'):
                main_prio_id = (key[0], key[1].replace('caption', 'icon'))
            if key[1].startswith('pathtext'):
                main_prio_id = (key[0], key[1].replace('pathtext', 'shield'))
            if main_prio_id is not None and main_prio_id in prio_ranges[PRIO_OVERLAYS][collection_name]:
                main_prio = prio_ranges[PRIO_OVERLAYS][collection_name][main_prio_id]
                if prio_ranges[PRIO_OVERLAYS][collection_name][key] > main_prio:
                    print(f'WARNING: {key} priority is higher than {main_prio_id}, making it equal')
                    prio_ranges[PRIO_OVERLAYS][collection_name][key] = main_prio

    # TODO: update compression logic to handle icons put inbetween automatic optional captions priorities.
    if compress:
        print(f'Compressing {prio_range} priorities into a (0;{priority_max}) range:')
        unique_prios = set(prio_ranges[prio_range][collection_name].values())
        print(f'\tunique priorities values: {len(unique_prios)}')
        # Keep gaps at the range borders.
        base_idx = 1
        if 0 not in unique_prios:
            base_idx = 0
            unique_prios.add(0)
        unique_prios.add(priority_max)
        step = min(priority_max / len(unique_prios), 10)
        print(f'\tnew step between priorities: {step}')
        unique_prios = sorted(unique_prios)
        for prio_id in prio_ranges[prio_range][collection_name].keys():
            idx = unique_prios.index(prio_ranges[prio_range][collection_name][prio_id])
            prio_ranges[prio_range][collection_name][prio_id] = int(step * (base_idx + idx))


def store_visibility(cl, dr_type, object_id, zoom, auto_comment = None):
    if object_id == '::default':
        object_id = ''
    dr_type_comment = (dr_type, auto_comment)
    if cl not in visibilities:
        visibilities[cl] = {}
    if dr_type_comment not in visibilities[cl]:
        visibilities[cl][dr_type_comment] = {}
    if object_id not in visibilities[cl][dr_type_comment]:
        visibilities[cl][dr_type_comment][object_id] = set()
    visibilities[cl][dr_type_comment][object_id].add(zoom)


def prettify_zooms(zooms, maxzoom):

    def add_zrange(first, last, result, maxzoom):
        first = str(first)
        last = str(last)
        if last == str(maxzoom):
            zrange = first + '-'
        elif first == last:
            zrange = first
        else:
            zrange = first + '-' + last
        if result != '':
            result += ','
        result += zrange
        return result

    zooms = sorted(zooms)
    first = zooms.pop(0)
    prev = first
    result = ''
    for zoom in zooms:
        if zoom == prev + 1:
            prev = zoom
        else:
            result = add_zrange(first, prev, result, maxzoom)
            first = zoom
            prev = zoom
    return 'z' + add_zrange(first, prev, result, maxzoom)


def validate_visibilities(maxzoom):
    for cl, dr_types_comments in visibilities.items():
        for dr_type_comment, object_ids in dr_types_comments.items():
            for object_id, zooms in object_ids.items():
                zoom_range = prettify_zooms(zooms, maxzoom)
                if zoom_range.find(',') != -1:
                    print(f'WARNING: non-contiguous visibility range {zoom_range} for {cl} {dr_type_comment}{object_id}')

                dr_type = dr_type_comment[0]
                icon_dr_type_comment = ('icon', None)
                if (dr_type == 'caption' and icon_dr_type_comment in dr_types_comments and
                    object_id in dr_types_comments[icon_dr_type_comment]):
                        icon_zooms = sorted(dr_types_comments[icon_dr_type_comment][object_id])
                        if min(zooms) < icon_zooms[0]:
                            print(f'WARNING: caption {zoom_range} appears before icon {prettify_zooms(icon_zooms, maxzoom)}'
                                  f' for {cl}{object_id}')

                line_dr_type_comment = ('line', None)
                if dr_type in ('pathtext', 'shield'):
                    lines_min_zoom = maxzoom + 1
                    if line_dr_type_comment in dr_types_comments:
                        lines_min_zoom = maxzoom + 1
                        for line_object_id, line_zooms in dr_types_comments[line_dr_type_comment].items():
                            min_zoom = min(line_zooms)
                            if min_zoom < lines_min_zoom:
                                lines_min_zoom = min_zoom
                    min_zoom = min(zooms)
                    if min_zoom < lines_min_zoom:
                        missing_zooms = prettify_zooms(range(min_zoom, lines_min_zoom), maxzoom)
                        print(f'ERROR: {dr_type} without line at {missing_zooms} for {cl}{object_id}')
                        global validation_errors_count
                        validation_errors_count += 1

def has_group_with_priority(priorities, groupPriority):
    for priority in priorities:
        if priority[1] == groupPriority:
            return True
    return False

def has_priority(priorities, groupPriority, type):
    for priority in priorities:
        if priority[1] == groupPriority and priority[0][0] == type:
            return True
    return False

def dump_priorities(prio_range, path, maxzoom, include_comments = True, format_only = False):
    fname = get_priorities_filename(prio_range, path)
    with open(fname, 'w') as outfile:
        if len(prio_ranges[prio_range]['imports']):
            outfile.write('# Only have changes of the base priority file here!\n\n')

        if include_comments:
            comment = COMMENT_AUTOFORMAT + prio_ranges[prio_range]['comment'] + COMMENT_RANGES_OVERVIEW
            for s in comment.splitlines():
                outfile.write(f'# {s}'.rstrip() + '\n')
            outfile.write('\n')

        if len(prio_ranges[prio_range]['imports']):
            for s in prio_ranges[prio_range]['imports']:
                outfile.write(f'@import("{s}")\n')
            outfile.write('\n')

        if include_comments:
            collection_name = 'priorities'
        else:
            collection_name = 'originalPriorities'
        if len(prio_ranges[prio_range][collection_name]):
            dr_types_order = (('icon', 'caption', 'pathtext', 'shield', 'line', 'area') if prio_range == PRIO_OVERLAYS
                              else ('line', 'area', 'icon', 'caption', 'pathtext', 'shield'))
            comment_auto_captions = '''
                All automatic optional captions priorities are below 0.
                They follow the order of their correspoding icons.
                '''

            prios = sorted(prio_ranges[prio_range][collection_name].items(),
                           key = lambda item: (OVERLAYS_MAX_PRIORITY - item[1], item[0][0], item[0][1]))
            if collection_name == 'originalPriorities':
                originalPrios = prios
            else:
                originalPrios = sorted(prio_ranges[prio_range]['originalPriorities'].items(), key = lambda item: (OVERLAYS_MAX_PRIORITY - item[1], item[0][0], item[0][1]))

            group_prio = prios[0][1]
            group = ''
            group_comment = '# '
            for p in prios:
                if p[1] != group_prio:
                    if prio_range == PRIO_OVERLAYS and comment_auto_captions and group_prio < 0:
                        if include_comments:
                            for s in comment_auto_captions.splitlines():
                                outfile.write(f'# {s.strip()}'.rstrip() + '\n')
                            outfile.write('\n')
                        comment_auto_captions = None
                    if include_comments:
                        outfile.write(f'{group}{group_comment}=== {group_prio}\n\n')
                    elif group_comment != '# ':
                        outfile.write(f'{group}{group_comment}=== {group_prio}\n\n')
                    group_prio = p[1]
                    group = ''
                    group_comment = '# '

                cl = p[0][0]
                object_id = p[0][1]
                is_original_group_with_priority = has_group_with_priority(originalPrios, p[1])
                is_original_priority = has_priority(originalPrios, p[1], p[0][0])
                auto_dr_type = None
                auto_comment = None
                if len(p[0]) == 4:
                    auto_dr_type = p[0][2]
                    auto_comment = p[0][3]

                line_drules = ''
                other_drules = ''
                if cl in visibilities:
                    for dr_type_comment in sorted(visibilities[cl].keys(), key = lambda drt: dr_types_order.index(drt[0])):
                        for oid in sorted(visibilities[cl][dr_type_comment].keys()):
                            dr_type, dr_auto_comment = dr_type_comment
                            dr_zoom = dr_type + oid
                            if dr_auto_comment is not None:
                                dr_zoom = f'{dr_zoom}({dr_auto_comment})'
                            dr_zoom += ' ' + prettify_zooms(visibilities[cl][dr_type_comment][oid], maxzoom)
                            # Drules matching this prio_range and object_id and
                            # - an auto priority dr_type match or
                            # - any other non-auto dr_type suitable
                            is_auto_dr_match = dr_type == auto_dr_type and dr_auto_comment == auto_comment
                            is_not_auto_dr = auto_dr_type is None and dr_auto_comment is None
                            is_suitable_for_range = (
                                (prio_range == PRIO_OVERLAYS and dr_type in ('icon', 'caption', 'pathtext', 'shield')) or
                                (prio_range in (PRIO_FG, PRIO_BG_TOP) and dr_type in ('line', 'area')) or
                                (prio_range == PRIO_BG_BY_SIZE and dr_type == 'area'))
                            if oid == object_id and (is_auto_dr_match or is_not_auto_dr and is_suitable_for_range):
                                if line_drules:
                                    line_drules += ' and '
                                line_drules += dr_zoom
                            else:
                                # Drules from other prio_ranges or with other object_ids.
                                if other_drules:
                                    other_drules += ', '
                                other_drules += dr_zoom
                if object_id:
                    cl += object_id
                if not line_drules:
                    if not format_only:
                        if other_drules:
                            line_drules = "WARNING: no drule defined for the priority"
                        else:
                            line_drules = "WARNING: no style defined (the type will be not included into map data)"
                        print(f'{line_drules} for {cl} in {prio_range}')

                info = '# ' + line_drules
                if other_drules:
                    info += f' (also has {other_drules})'

                if include_comments:
                    if auto_dr_type is None and is_original_group_with_priority:
                        group_comment = ''
                    if not is_original_priority:
                        group += f'# {cl:48}  {info}\n'
                    else:
                        group += f'{cl:50}  {info}\n'
                else:
                    group_comment = ''
                    group += f'{cl}\n'

            outfile.write(f'{group}{group_comment}=== {group_prio}\n')

def get_drape_priority(cl, dr_type, object_id, auto_dr_type = None, auto_comment = None, auto_prio_mod = 0):
    if object_id == '::default':
        object_id = ''
    prio_id = (cl, object_id)

    ranges_to_check = (PRIO_OVERLAYS, )
    if dr_type == 'line':
        ranges_to_check = (PRIO_FG, PRIO_BG_TOP)
    elif dr_type == 'area':
        ranges_to_check = (PRIO_BG_BY_SIZE, PRIO_BG_TOP, PRIO_FG)
    for r in ranges_to_check:
        if prio_id in prio_ranges[r]['priorities']:
            priority = prio_ranges[r]['priorities'][prio_id]
            if auto_dr_type is not None:
                min_priority = -OVERLAYS_MAX_PRIORITY if r == PRIO_OVERLAYS else 0
                priority = max(priority + auto_prio_mod, min_priority)
                auto_prio_id = (cl, object_id, auto_dr_type, auto_comment)
                prio_ranges[r]['priorities'][auto_prio_id] = priority
            return priority + prio_ranges[r]['base']

    print(f'ERROR: priority is not set for {dr_type} {cl}{object_id}')
    global validation_errors_count
    validation_errors_count += 1
    return 0


def legacy_z_index_priority(st, explicit_key, base, max_priority):
    if explicit_key in st:
        return int(st.get(explicit_key))
    return min(max_priority, base + int(st.get('z-index', 0)))


def legacy_casing_line_priority(st):
    if '-x-me-casing-line-priority' in st:
        return int(st.get('-x-me-casing-line-priority'))
    return min(int(st.get('z-index', 0) + 999), 20000)


def legacy_line_priority(st):
    return legacy_z_index_priority(st, '-x-me-line-priority', 1000, 20000)


def legacy_shield_priority(st):
    return legacy_z_index_priority(st, '-x-me-shield-priority', 16000, 19100)


def legacy_icon_priority(st):
    return legacy_z_index_priority(st, '-x-me-icon-priority', 16000, 19100)


def legacy_circle_priority(st):
    return legacy_z_index_priority(st, '-x-me-symbol-priority', 14000, 19000)


def legacy_text_priority(st, base_z):
    return legacy_z_index_priority(st, '-x-me-text-priority', base_z, 19000)


def resolve_default_maxzoom(maxzoom, priority_mode=None, compatibility=None):
    if maxzoom is not None:
        return maxzoom
    if compatibility is None:
        compatibility = build_compatibility_config(priority_mode=priority_mode)
    return compatibility.default_maxzoom


def legacy_area_priority(st, bgpos):
    if '-x-me-area-priority' in st:
        return int(st.get('-x-me-area-priority')), bgpos

    if st.get('fill-position', 'foreground') == 'background':
        if 'z-index' not in st:
            bgpos -= 1
            return bgpos - 16000, bgpos

        zzz = int(st.get('z-index', 0))
        if zzz > 0:
            return zzz - 16000, bgpos
        return zzz - 16700, bgpos

    return int(st.get('z-index', 0)) + 1 + 1000, bgpos


def format_priorities(options):
    output = ''
    for prio_range in prio_ranges.keys():
        load_priorities(prio_range, options.priorities_path, set(), compress = False, level = 0, has_imports = False, skip_imports = False, format_only = True)
        dump_priorities(prio_range, options.priorities_path, options.maxzoom, include_comments = False, format_only = True)
        output += f'{"" if not output else ", "}{len(prio_ranges[prio_range]["priorities"])} {prio_range}'
    print(f'Re-formated priorities files: {output}.')

# TODO: Split large function to smaller ones
def komap_mapswithme(options):
    global PRIORITY_MODE
    global RUNTIME_CONDITION_MODE
    global COMPATIBILITY_PROFILE
    global COMPATIBILITY
    profile_name = getattr(options, 'compatibility_profile', None)
    priority_override = getattr(options, 'priority_mode', None)
    runtime_override = getattr(options, 'runtime_condition_mode', None)
    COMPATIBILITY = build_compatibility_config(profile_name, priority_override, runtime_override)
    COMPATIBILITY_PROFILE = COMPATIBILITY.name
    PRIORITY_MODE = COMPATIBILITY.priority_mode
    RUNTIME_CONDITION_MODE = COMPATIBILITY.runtime_condition_mode
    options.maxzoom = resolve_default_maxzoom(getattr(options, 'maxzoom', None), compatibility=COMPATIBILITY)

    if options.data and os.path.isdir(options.data):
        ddir = options.data
    else:
        ddir = os.path.dirname(options.outfile)

    classificator = {}
    class_order = []
    class_tree = {}

    # TODO: Introduce new function to parse `colors.txt` for better testability
    colors_file_name = os.path.join(ddir, 'colors.txt')
    colors = set()
    if os.path.exists(colors_file_name):
        colors_in_file = open(colors_file_name, "r")
        for colorLine in colors_in_file:
            colors.add(int(colorLine))
        colors_in_file.close()

    # TODO: Introduce new function to parse `patterns.txt` for better testability
    patterns = []
    def addPattern(dashes):
        if dashes and dashes not in patterns:
            patterns.append(dashes)

    patterns_file_name = os.path.join(ddir, 'patterns.txt')
    if os.path.exists(patterns_file_name):
        patterns_in_file = open(patterns_file_name, "r")
        for patternsLine in patterns_in_file:
            addPattern([float(x) for x in patternsLine.split()])
        patterns_in_file.close()

    # Build classificator tree from mapcss-mapping.csv file
    types_file = open(os.path.join(ddir, 'types.txt'), "w")

    # The mapcss-mapping.csv format is described inside the file itself.
    # TODO: introduce new function to parse 'mapcss-mapping.csv' for better testability
    cnt = 1
    unique_types_check = set()
    mapping_file = open(os.path.join(ddir, 'mapcss-mapping.csv'))
    for row in csv.reader(mapping_file, delimiter=';'):
        if len(row) <= 1 or row[0].startswith('#'):
            # Allow for empty lines and comment lines starting with '#'.
            continue
        if len(row) == 3:
            # Short format: type name, type id, x / replacement type name
            tag = row[0].replace('|', '=')
            obsolete = len(row[2].strip()) > 0
            row = (row[0], '[{0}]'.format(tag), 'x' if obsolete else '', 'name', 'int_name', row[1], row[2] if row[2] != 'x' else '')
        if len(row) != 7:
            raise Exception('Expecting 3 or 7 columns in mapcss-mapping: {0}'.format(';'.join(row)))

        if int(row[5]) < cnt:
            raise Exception('Wrong type id: {0}'.format(';'.join(row)))
        while int(row[5]) > cnt:
            print("mapswithme", file=types_file)
            cnt += 1
        cnt += 1

        cl = row[0].replace("|", "-")
        if not COMPATIBILITY.allow_duplicate_types and cl in unique_types_check and row[2] != 'x':
            raise Exception('Duplicate type: {0}'.format(row[0]))
        pairs = [i.strip(']').split("=") for i in row[1].split(',')[0].split('[')]
        kv = OrderedDict()
        for i in pairs:
            if len(i) == 1:
                if i[0]:
                    if i[0][0] == "!":
                        kv[i[0][1:].strip('?')] = "no"
                    else:
                        kv[i[0].strip('?')] = "yes"
            else:
                kv[i[0]] = i[1]
        if row[2] != "x":
            classificator[cl] = kv
            class_order.append(cl)
            unique_types_check.add(cl)
            # Mark original type to distinguish it among replacing types.
            print("*" + row[0], file=types_file)
        else:
            # compatibility mode
            if row[6]:
                print(row[6], file=types_file)
            else:
                print("mapswithme", file=types_file)
        class_tree[cl] = row[0]
    class_order.sort()
    mapping_file.close()
    types_file.close()

    if COMPATIBILITY.use_priority_files:
        output = ''
        for prio_range in prio_ranges.keys():
            load_priorities(prio_range, options.priorities_path, unique_types_check, compress = False)
            output += f'{"" if not output else ", "}{len(prio_ranges[prio_range]["priorities"])} {prio_range}'
        print(f'Loaded priorities: {output}.')

    del unique_types_check

    # Get all mapcss static tags which are used in mapcss-mapping.csv
    # This is a dict with main_tag flags (True = appears first in types)
    mapcss_static_tags = {}
    for v in list(classificator.values()):
        for i, t in enumerate(v.keys()):
            mapcss_static_tags[t] = mapcss_static_tags.get(t, True) and i == 0

    # TODO: Introduce new function to parse `mapcss-dynamic.txt` for better testability
    # Get all mapcss dynamic tags from mapcss-dynamic.txt
    with open(os.path.join(ddir, 'mapcss-dynamic.txt')) as dynamic_file:
        mapcss_dynamic_tags = set([line.rstrip() for line in dynamic_file])

    # Parse style mapcss
    global style
    if COMPATIBILITY.legacy_zindex:
        style = MapCSS(options.minzoom, options.maxzoom + 1)
        style.parse(filename=options.filename, static_tags=mapcss_static_tags,
                    dynamic_tags=mapcss_dynamic_tags, legacy_zindex=True)
    else:
        style = MapCSS(options.minzoom, options.maxzoom)
        style.parse(clamp=False, stretch=LAYER_PRIORITY_RANGE,
                    filename=options.filename, static_tags=mapcss_static_tags,
                    dynamic_tags=mapcss_dynamic_tags)

    # Build optimization tree - class/zoom/type -> StyleChoosers
    clname_cltag_unique = set()
    for cl in class_order:
        clname = cl if cl.find('-') == -1 else cl[:cl.find('-')]
        if COMPATIBILITY.match_all_class_tags:
            cltags = classificator[cl]
            style.build_choosers_tree(clname, "line", cltags)
            style.build_choosers_tree(clname, "area", cltags)
            style.build_choosers_tree(clname, "node", cltags)
            continue

        # Get first tag of the class/type.
        cltag = next(iter(classificator[cl].keys()))
        clname_cltag = clname + '$' + cltag
        if clname_cltag not in clname_cltag_unique:
            clname_cltag_unique.add(clname_cltag)
            style.build_choosers_tree(clname, "line", cltag)
            style.build_choosers_tree(clname, "area", cltag)
            style.build_choosers_tree(clname, "node", cltag)

    style.finalize_choosers_tree()

    # TODO: Introduce new function to work with colors for better testability
    # Get colors section from style
    style_colors = {}
    raw_style_colors = style.get_colors()
    if raw_style_colors is not None:
        unique_style_colors = set()
        for k in list(raw_style_colors.keys()):
            unique_style_colors.add(k[:k.rindex('-')])
        for k in unique_style_colors:
            style_colors[k] = mwm_encode_color(colors, raw_style_colors, k)

    visibility = {}
    bgpos = 0

    dr_linecaps = {'none': BUTTCAP, 'butt': BUTTCAP, 'round': ROUNDCAP}
    dr_linejoins = {'none': NOJOIN, 'bevel': BEVELJOIN, 'round': ROUNDJOIN}

    # Build drules tree

    drules = ContainerProto()
    dr_cont = None
    if MULTIPROCESSING:
        set_start_method('fork')  # Use fork with multiprocessing to share global variables among Python instances
        pool = Pool()
        imapfunc = pool.imap
    else:
        imapfunc = map

    if style_colors:
        for k, v in sorted(list(style_colors.items())):
            color_proto = ColorElementProto()
            color_proto.name = k
            color_proto.color = v
            color_proto.x = 0
            color_proto.y = 0
            drules.colors.value.extend([color_proto])

    all_draw_elements = set()

    # TODO: refactor next for-loop for readability and testability
    global validation_errors_count
    for results in imapfunc(query_style, ((cl, classificator[cl], options.minzoom, options.maxzoom) for cl in class_order)):
        for result in results:
                cl, zoom, runtime_conditions, zstyle, has_icons_for_areas = result

                if COMPATIBILITY.sort_priority_file_rules:
                    # First, sort rules by ::object-id in captions (primary, secondary, none ..)
                    # then by other ::object-id in ascending order.
                    def rule_sort_key(dict_):
                        first = 0
                        if dict_.get('text'):
                            if str(dict_.get('object-id')) != '::default':
                                first = 1
                            if str(dict_.get('text')) == 'none':
                                first = 2
                        return (first, dict_.get('object-id'))

                    zstyle.sort(key = rule_sort_key)

                # For debug purpose.
                # if str(cl) == 'highway-path' and int(zoom) == 19:
                #     print(cl)
                #     print(zstyle)

                if dr_cont is not None and dr_cont.name != cl:
                    if dr_cont.element:
                        drules.cont.extend([dr_cont])
                    visibility["world|" + class_tree[dr_cont.name] + "|"] = "".join(visstring)
                    dr_cont = None

                if dr_cont is None:
                    dr_cont = ClassifElementProto()
                    dr_cont.name = cl

                    visstring = ["0"] * (options.maxzoom - options.minzoom + 1)

                if len(zstyle) == 0:
                    continue

                has_lines = False
                has_icons = False
                has_fills = False
                for st in zstyle:
                    st = dict([(k, v) for k, v in st.items() if str(v).strip(" 0.")])
                    if 'width' in st or 'pattern-image' in st:
                        has_lines = True
                    if 'icon-image' in st and st.get('icon-image') != 'none' or 'symbol-shape' in st or 'symbol-image' in st:
                        has_icons = True
                    if 'fill-color' in st and st.get('fill-color') != 'none':
                        has_fills = True

                has_text = None
                txfmt = []
                for st in zstyle:
                    if st.get('text') and st.get('text') != 'none' and st.get('text') not in txfmt:
                        txfmt.append(st.get('text'))
                        if has_text is None:
                            has_text = []
                        has_text.append(st)

                if (not has_lines) and (not has_text) and (not has_fills) and (not has_icons):
                    continue

                visstring[zoom] = "1"

                if zoom == 0 and not COMPATIBILITY.mapsme_legacy_output:
                    continue

                dr_element = DrawElementProto()
                dr_element.scale = zoom

                if runtime_conditions:
                    for rc in runtime_conditions:
                        dr_element.apply_if.append(str(rc))

                for st in zstyle:
                    if COMPATIBILITY.mapsme_legacy_output:
                        if st.get('-x-kot-layer') == 'top':
                            st['z-index'] = float(st.get('z-index', 0)) + 15001.
                        elif st.get('-x-kot-layer') == 'bottom':
                            st['z-index'] = float(st.get('z-index', 0)) - 15001.

                    has_casing_width_add = not COMPATIBILITY.mapsme_legacy_output and st.get('casing-width-add') is not None
                    if st.get('casing-width') not in (None, 0) or has_casing_width_add:  # and (st.get('width') or st.get('fill-color')):
                        is_area_st = 'fill-color' in st
                        if has_lines and (COMPATIBILITY.mapsme_legacy_output or not is_area_st) and st.get('casing-linecap', 'butt') == 'butt':
                            dr_line = LineRuleProto()

                            base_width = st.get('width', 0)
                            if base_width == 0 and not COMPATIBILITY.mapsme_legacy_output:
                                for wst in zstyle:
                                    if wst.get('width') not in (None, 0):
                                        # Rail bridge styles use width from ::dash object instead of ::default.
                                        if base_width == 0 or wst.get('object-id') != '::default':
                                            base_width = wst.get('width', 0)
                                # 'casing-width' has precedence over 'casing-width-add'.
                                if has_casing_width_add and st.get('casing-width') in (None, 0):
                                    st['casing-width'] = base_width + st.get('casing-width-add')
                                    base_width = 0

                            casing_width = base_width + st.get('casing-width') * 2
                            dr_line.width = casing_width if COMPATIBILITY.mapsme_legacy_output else round(casing_width, 2)
                            dr_line.color = mwm_encode_color(colors, st, "casing")
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_line.priority = legacy_casing_line_priority(st)
                            elif st.get('object-id') == '::default':
                                # An automatic casing line should be rendered below the "main" line, hence auto priority -1.
                                auto_comment = 'casing'
                                dr_line.priority = get_drape_priority(cl, 'line', st.get('object-id'), 'line', auto_comment, -1)
                                store_visibility(cl, 'line', st.get('object-id'), zoom, auto_comment)
                            else:
                                # A casing line explicitly defined via ::object_id.
                                dr_line.priority = get_drape_priority(cl, 'line', st.get('object-id'))
                                store_visibility(cl, 'line', st.get('object-id'), zoom)
                            for i in st.get('casing-dashes', st.get('dashes', [])):
                                dr_line.dashdot.dd.extend([float(i)])
                            addPattern(dr_line.dashdot.dd)
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_line.dashdot.SetInParent()
                            dr_line.cap = dr_linecaps.get(st.get('casing-linecap', 'butt'), BUTTCAP)
                            dr_line.join = dr_linejoins.get(st.get('casing-linejoin', 'round'), ROUNDJOIN)
                            dr_element.lines.extend([dr_line])

                        if has_fills and is_area_st and float(st.get('fill-opacity', 1)) > 0:
                            dr_element.area.border.color = mwm_encode_color(colors, st, "casing")
                            dr_element.area.border.width = st.get('casing-width', 0)

                        # Let's try without this additional line style overhead. Needed only for casing in road endings.
                        # if st.get('casing-linecap', st.get('linecap', 'round')) != 'butt':
                        #     dr_line = LineRuleProto()
                        #     dr_line.width = st.get('width', 0) + (st.get('casing-width') * 2)
                        #     dr_line.color = mwm_encode_color(colors, st, "casing")
                        #     dr_line.priority = -15000
                        #     dashes = st.get('casing-dashes', st.get('dashes', []))
                        #     dr_line.dashdot.dd.extend(dashes)
                        #     dr_line.cap = dr_linecaps.get(st.get('casing-linecap', 'round'), ROUNDCAP)
                        #     dr_line.join = dr_linejoins.get(st.get('casing-linejoin', 'round'), ROUNDJOIN)
                        #     dr_element.lines.extend([dr_line])

                    if has_lines:
                        if st.get('width'):
                            dr_line = LineRuleProto()
                            dr_line.width = st.get('width', 0)
                            dr_line.color = mwm_encode_color(colors, st)
                            for i in st.get('dashes', []):
                                dash = max(float(i), 1) if COMPATIBILITY.mapsme_legacy_output else float(i)
                                dr_line.dashdot.dd.extend([dash])
                            addPattern(dr_line.dashdot.dd)
                            dr_line.cap = dr_linecaps.get(st.get('linecap', 'butt'), BUTTCAP)
                            dr_line.join = dr_linejoins.get(st.get('linejoin', 'round'), ROUNDJOIN)
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_line.priority = legacy_line_priority(st)
                            else:
                                dr_line.priority = get_drape_priority(cl, 'line', st.get('object-id'))
                                store_visibility(cl, 'line', st.get('object-id'), zoom)
                            dr_element.lines.extend([dr_line])
                        if st.get('pattern-image'):
                            dr_line = LineRuleProto()
                            dr_line.width = 0
                            dr_line.color = 0
                            icon = mwm_encode_image(st, prefix='pattern')
                            dr_line.pathsym.name = icon[0]
                            dr_line.pathsym.step = float(st.get('pattern-spacing', 0)) - 16
                            dr_line.pathsym.offset = st.get('pattern-offset', 0)
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_line.priority = legacy_line_priority(st)
                            else:
                                dr_line.priority = get_drape_priority(cl, 'line', st.get('object-id'))
                                store_visibility(cl, 'line', st.get('object-id'), zoom)
                            dr_element.lines.extend([dr_line])

                    if st.get('shield-font-size') and (not COMPATIBILITY.mapsme_legacy_output or has_lines):
                        dr_element.shield.height = int(st.get('shield-font-size', 10))
                        dr_element.shield.text_color = mwm_encode_color(colors, st, "shield-text")
                        if st.get('shield-text-halo-radius', 0) != 0:
                            dr_element.shield.text_stroke_color = mwm_encode_color(colors, st, "shield-text-halo", "white")
                        dr_element.shield.color = mwm_encode_color(colors, st, "shield")
                        if st.get('shield-outline-radius', 0) != 0:
                            dr_element.shield.stroke_color = mwm_encode_color(colors, st, "shield-outline", "white")
                        if COMPATIBILITY.mapsme_legacy_output:
                            dr_element.shield.priority = legacy_shield_priority(st)
                        else:
                            dr_element.shield.priority = get_drape_priority(cl, 'shield', st.get('object-id'))
                            store_visibility(cl, 'shield', st.get('object-id'), zoom)
                        if st.get('shield-min-distance', 0) != 0:
                            dr_element.shield.min_distance = int(st.get('shield-min-distance', 0))

                    if has_icons:
                        if st.get('icon-image') and st.get('icon-image') != 'none':
                            if COMPATIBILITY.mapsme_legacy_output and not has_icons_for_areas:
                                dr_element.symbol.apply_for_type = 1
                            icon = mwm_encode_image(st)
                            dr_element.symbol.name = icon[0]
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_element.symbol.priority = legacy_icon_priority(st)
                            else:
                                dr_element.symbol.priority = get_drape_priority(cl, 'icon', st.get('object-id'))
                                store_visibility(cl, 'icon', st.get('object-id'), zoom)
                            if 'icon-min-distance' in st:
                                dr_element.symbol.min_distance = int(st.get('icon-min-distance', 0))
                            has_icons = False
                        if st.get('symbol-shape'):
                            # TODO: not used in current styles; do "circles" work in drape at all?
                            dr_element.circle.radius = float(st.get('symbol-size'))
                            dr_element.circle.color = mwm_encode_color(colors, st, 'symbol-fill')
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_element.circle.priority = legacy_circle_priority(st)
                            else:
                                dr_element.circle.priority = get_drape_priority(cl, 'circle', st.get('object-id'))
                                store_visibility(cl, 'circle', st.get('object-id'), zoom)
                            has_icons = False

                    if has_text and st.get('text') and st.get('text') != 'none':
                        # Take only first 2 captions: primary, secondary.
                        has_text = has_text[:2]
                        if COMPATIBILITY.mapsme_legacy_output and not COMPATIBILITY.mapsme_2016_text_order:
                            has_text.reverse()

                        dr_text = dr_element.caption
                        text_priority_key = 'caption'
                        if st.get('text-position', 'center') == 'line':
                            dr_text = dr_element.path_text
                            text_priority_key = 'pathtext'

                        dr_cur_subtext = dr_text.primary
                        for sp in has_text[:]:
                            if COMPATIBILITY.mapsme_legacy_output and not COMPATIBILITY.mapsme_2016_text_order:
                                dr_cur_subtext = dr_text.secondary if len(has_text) == 2 else dr_text.primary
                            dr_cur_subtext.height = int(float(sp.get('font-size', "10").split(",")[0]))
                            if not COMPATIBILITY.mapsme_legacy_output and 'text-color' not in st:
                                print(f'ERROR: text-color not set for z{zoom} {cl}')
                                validation_errors_count += 1
                            dr_cur_subtext.color = mwm_encode_color(colors, sp, "text")
                            if st.get('text-halo-radius', 0) != 0:
                                dr_cur_subtext.stroke_color = mwm_encode_color(colors, sp, "text-halo", "white")
                            if 'text-offset' in sp or 'text-offset-y' in sp:
                                dr_cur_subtext.offset_y = int(sp.get('text-offset-y', sp.get('text-offset', 0)))
                            elif 'text-offset-x' in sp:
                                dr_cur_subtext.offset_x = int(sp.get('text-offset-x', 0))
                            elif not COMPATIBILITY.mapsme_legacy_output and st.get('text-position', 'center') == 'center' and dr_element.symbol.priority:
                                print(f'ERROR: an icon is present, but caption\'s text-offset is not set for z{zoom} {cl}')
                                validation_errors_count += 1
                            if 'text' in sp and (COMPATIBILITY.mapsme_legacy_output and sp.get('text') != 'name' or not COMPATIBILITY.mapsme_legacy_output and sp.get('text') not in ('name', 'int_name')):
                                dr_cur_subtext.text = sp.get('text')
                            if 'text-optional' in sp:
                                is_valid, value = to_boolean(sp.get('text-optional', ''))
                                if is_valid:
                                    dr_cur_subtext.is_optional = value
                                else:
                                    dr_cur_subtext.is_optional = True
                            elif not COMPATIBILITY.mapsme_legacy_output and text_priority_key == 'caption' and dr_element.symbol.priority:
                                # On by default for all captions (not path texts) with icons.
                                dr_cur_subtext.is_optional = True
                            if not COMPATIBILITY.mapsme_legacy_output or COMPATIBILITY.mapsme_2016_text_order:
                                dr_cur_subtext = dr_text.secondary
                            if COMPATIBILITY.mapsme_legacy_output and not COMPATIBILITY.mapsme_2016_text_order:
                                has_text.pop()

                        auto_comment = None
                        if COMPATIBILITY.mapsme_legacy_output:
                            base_z = 16000 if text_priority_key == 'pathtext' else 15000
                            dr_text.priority = legacy_text_priority(st, base_z)
                        elif text_priority_key == 'caption' and dr_element.symbol.priority:
                            # A caption with an icon.
                            # Mandatory captions use icon's priority.
                            auto_prio_mod = 0
                            auto_comment = 'mandatory'
                            if dr_text.primary.is_optional:
                                # Optional captions are automatically placed below most other overlays.
                                auto_comment = 'optional'
                                auto_prio_mod = -OVERLAYS_MAX_PRIORITY
                            dr_text.priority = get_drape_priority(cl, 'icon', st.get('object-id'),
                                                                  text_priority_key, auto_comment, auto_prio_mod)
                        else:
                            # A pathtext or a standalone caption.
                            dr_text.priority = get_drape_priority(cl, text_priority_key, st.get('object-id'))

                        if not COMPATIBILITY.mapsme_legacy_output:
                            store_visibility(cl, text_priority_key, st.get('object-id'), zoom, auto_comment)

                        # Process captions block once.
                        has_text = None

                    if has_fills:
                        if 'fill-color' in st and st.get('fill-color') != 'none' and float(st.get('fill-opacity', 1)) > 0:
                            dr_element.area.color = mwm_encode_color(colors, st, "fill")
                            if COMPATIBILITY.mapsme_legacy_output:
                                dr_element.area.priority, bgpos = legacy_area_priority(st, bgpos)
                            else:
                                dr_element.area.priority = get_drape_priority(cl, 'area', st.get('object-id'))
                                store_visibility(cl, 'area', st.get('object-id'), zoom)
                            has_fills = False

                str_dr_element = dr_cont.name + "/" + str(dr_element)
                if str_dr_element not in all_draw_elements:
                    all_draw_elements.add(str_dr_element)
                    dr_cont.element.extend([dr_element])

    if dr_cont is not None:
        if dr_cont.element:
            drules.cont.extend([dr_cont])

        visibility["world|" + class_tree[cl] + "|"] = "".join(visstring)

    if not COMPATIBILITY.mapsme_legacy_output:
        validate_visibilities(options.maxzoom)

    if not COMPATIBILITY.mapsme_legacy_output and validation_errors_count:
        print()
        exit('FAILED to write regenerated drules files!\n'
             f'There are {validation_errors_count} validation errors (see in the log above).\n'
             'Fix all errors first and re-run.')

    if COMPATIBILITY.use_priority_files:
        output = ''
        for prio_range in prio_ranges.keys():
            dump_priorities(prio_range, options.priorities_path, options.maxzoom)
            output += f'{"" if not output else ", "}{len(prio_ranges[prio_range]["priorities"])} {prio_range}'
        print(f'Re-formated priorities files: {output}.')

    # Write drules_proto.bin and drules_proto.txt files

    drules_bin = open(os.path.join(options.outfile + '.bin'), "wb")
    drules_bin.write(drules.SerializeToString())
    drules_bin.close()

    if options.txt:
        drules_txt = open(os.path.join(options.outfile + '.txt'), "wb")
        drules_txt.write(str(drules).encode())
        drules_txt.close()

    # Write classificator.txt and visibility.txt files

    visnodes = set()
    for k, v in visibility.items():
        vis = k.split("|")
        for i in range(1, len(vis) - 1):
            visnodes.add("|".join(vis[0:i]) + "|")
    viskeys = list(set(list(visibility.keys()) + list(visnodes)))

    def cmprepl(a, b):
        if a == b:
            return 0
        a = a.replace("|", "-")
        b = b.replace("|", "-")
        if a > b:
            return 1
        return -1
    viskeys.sort(key=functools.cmp_to_key(cmprepl))

    # TODO: Introduce new function to dump `visibility.txt` and `classificator.txt` for better testability
    visibility_file = open(os.path.join(ddir, 'visibility.txt'), "w")
    classificator_file = open(os.path.join(ddir, 'classificator.txt'), "w")

    oldoffset = ""
    for k in viskeys:
        offset = "    " * (k.count("|") - 1)
        for i in range(int(len(oldoffset) / 4), int(len(offset) / 4), -1):
            print("    " * i + "{}", file=visibility_file)
            print("    " * i + "{}", file=classificator_file)
        oldoffset = offset
        end = "-"
        if k in visnodes:
            end = "+"
        print(offset + k.split("|")[-2] + "  " + visibility.get(k, "0" * (options.maxzoom + 1)) + "  " + end, file=visibility_file)
        print(offset + k.split("|")[-2] + "  " + end, file=classificator_file)
    for i in range(int(len(offset) / 4), 0, -1):
        print("    " * i + "{}", file=visibility_file)
        print("    " * i + "{}", file=classificator_file)

    visibility_file.close()
    classificator_file.close()

    # TODO: Introduce new function to dump `colors.txt` for better testability
    colors_file = open(colors_file_name, "w")
    for c in sorted(colors):
        colors_file.write("%d\n" % (c))
    colors_file.close()

    # TODO: Introduce new function to dump `patterns.txt` for better testability
    patterns_file = open(patterns_file_name, "w")
    for p in patterns:
        patterns_file.write("%s\n" % (' '.join(str(elem) for elem in p)))
    patterns_file.close()


def main():
    parser = OptionParser()
    parser.add_option("-s", "--stylesheet", dest="filename",
                      help="read MapCSS stylesheet from FILE", metavar="FILE")
    parser.add_option("-f", "--minzoom", dest="minzoom", default=0, type="int",
                      help="minimal available zoom level", metavar="ZOOM")
    parser.add_option("-t", "--maxzoom", dest="maxzoom", default=None, type="int",
                      help="maximal available zoom level", metavar="ZOOM")
    parser.add_option("-o", "--output-file", dest="outfile", default="-",
                      help="output filename", metavar="FILE")
    parser.add_option("-x", "--txt", dest="txt", action="store_true",
                      help="create a text file for output", default=False)
    parser.add_option("", "--format-priorities-only", dest="format_priorities_only", action="store_true",
                      help="only sort the priorities", default=False)
    parser.add_option("-p", "--priorities-path", dest="priorities_path",
                      help="path to priorities *.prio.txt files", metavar="PATH")
    parser.add_option("-d", "--data-path", dest="data",
                      help="path to mapcss-mapping.csv and other files", metavar="PATH")
    parser.add_option("", "--compatibility-profile", dest="compatibility_profile",
                      help="compatibility preset: " + ", ".join(compatibility_profile_names()),
                      default=COMPATIBILITY_PROFILE, metavar="PROFILE")
    parser.add_option("", "--runtime-condition-mode", dest="runtime_condition_mode",
                      help="override runtime condition mode: organicmaps, comaps, mapsme, or mapsme-fallback",
                      default=None, metavar="MODE")
    parser.add_option("", "--priority-mode", dest="priority_mode",
                      help="override priority mode: priority_files or mapsme",
                      default=None, metavar="MODE")

    (options, args) = parser.parse_args()

    try:
        compatibility = build_compatibility_config(
            options.compatibility_profile,
            options.priority_mode,
            options.runtime_condition_mode
        )
    except ValueError as e:
        parser.error(str(e))

    options.priority_mode = compatibility.priority_mode
    options.runtime_condition_mode = compatibility.runtime_condition_mode
    options.maxzoom = resolve_default_maxzoom(options.maxzoom, compatibility=compatibility)

    if compatibility.use_priority_files and (options.priorities_path is None or not os.path.isdir(options.priorities_path)):
        parser.error("A path to priorities *.prio.txt files is required.")
    if options.priorities_path is not None:
        options.priorities_path = os.path.normpath(options.priorities_path)

    if options.format_priorities_only:
        format_priorities(options)
    else:
        if (options.filename is None):
            parser.error("MapCSS stylesheet filename is required")

        if options.outfile == "-":
            parser.error("Please specify base output path.")

        komap_mapswithme(options)

if __name__ == '__main__':
    if PROFILE:
        import cProfile
        cProfile.run('main()', 'profile.tmp')
        import pstats
        p = pstats.Stats('profile.tmp')
        p.sort_stats('cumulative').print_stats(10)
    else:
        main()
