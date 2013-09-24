from drules_struct_pb2 import *

import os
import csv
import json
import mapcss.webcolors
whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex
whatever_to_cairo = mapcss.webcolors.webcolors.whatever_to_cairo

WIDTH_SCALE = 1.0


def komap_mapswithme(options, style):
    if options.outfile == "-":
        print "Please specify base output path."
        exit()
    else:
        ddir = os.path.dirname(options.outfile)
    drules = ContainerProto()

    visibility_file = open(os.path.join(ddir, 'visibility.txt'), "w")
    classificator_file = open(os.path.join(ddir, 'classificator.txt'), "w")
    types_file = open(os.path.join(ddir, 'types.txt'), "w")
    drules_bin = open(os.path.join(options.outfile + '.bin'), "wb")
    drules_txt = open(os.path.join(options.outfile + '.txt'), "wb")

    classificator = {}
    class_order = []
    class_tree = {}
    visibility = {}

    for row in csv.reader(open(os.path.join(ddir, 'mapcss-mapping.csv')), delimiter=';'):
        pairs = [i.strip(']').split("=") for i in row[1].split(',')[0].split('[')]
        kv = {}
        for i in pairs:
            if len(i) == 1:
                if i[0]:
                    if i[0][0] == "!":
                        kv[i[0][1:].strip('?')] = "no"
                    else:
                        kv[i[0].strip('?')] = "yes"
            else:
                kv[i[0]] = i[1]
        classificator[row[0].replace("|", "-")] = kv
        if row[2] != "x":
            class_order.append(row[0].replace("|", "-"))
            print >> types_file, row[0]
        else:
            # compatibility mode
            if row[6]:
                print >> types_file, row[6]
            else:
                print >> types_file, "mapswithme"
        class_tree[row[0].replace("|", "-")] = row[0]
    class_order.sort()

    def mwm_encode_color(st, prefix='', default='black'):
        if prefix:
            prefix += "-"
        opacity = hex(255 - int(255 * float(st.get(prefix + "opacity", 1))))
        if opacity == "0x0":
            opacity = "0x"
        color = whatever_to_hex(st.get(prefix + 'color', default))
        color = color[1] + color[1] + color[3] + color[3] + color[5] + color[5]
        return int(opacity + color, 16)

    bgpos = 0

    dr_linecaps = {'none': BUTTCAP, 'butt': BUTTCAP, 'round': ROUNDCAP}
    dr_linejoins = {'none': NOJOIN, 'bevel': BEVELJOIN, 'round': ROUNDJOIN}

    for cl in class_order:
        visstring = ["0"] * (options.maxzoom + 1)
        dr_cont = ClassifElementProto()
        dr_cont.name = cl

        for zoom in xrange(options.minzoom, options.maxzoom + 1):
            txclass = classificator[cl]
            txclass["name"] = "name"
            txclass["addr:housenumber"] = "addr:housenumber"
            txclass["ref"] = "ref"
            txclass["int_name"] = "int_name"
            has_icons_for_areas = False
            zstyle = {}

            if "area" not in txclass:
                zstyle = style.get_style_dict("line", txclass, zoom, olddict=zstyle)
                # for st in zstyle:
                #    if "fill-color" in st:
                #        del st["fill-color"]

            if True:
                areastyle = style.get_style_dict("area", txclass, zoom, olddict=zstyle)
                for st in areastyle.values():
                    if "icon-image" in st or 'symbol-shape' in st:
                        has_icons_for_areas = True
                zstyle = areastyle

            if "area" not in txclass:
                nodestyle = style.get_style_dict("node", txclass, zoom, olddict=zstyle)
                # for st in nodestyle:
                #    if "fill-color" in st:
                #        del st["fill-color"]
                zstyle = nodestyle
            zstyle = zstyle.values()
            has_lines = False
            has_text = []
            has_icons = False
            has_fills = False
            for st in zstyle:
                st = dict([(k, v) for k, v in st.iteritems() if str(v).strip(" 0.")])
                if 'width' in st or 'pattern-image' in st:
                    has_lines = True
                if 'icon-image' in st or 'symbol-shape' in st:
                    has_icons = True
                if 'fill-color' in st:
                    has_fills = True
            txfmt = []
            for st in zstyle:
                if 'text' in st and not st.get('text') in txfmt:
                    txfmt.append(st.get('text'))
                    has_text.append(st)

            if has_lines or has_text or has_fills or has_icons:
                visstring[zoom] = "1"
                dr_element = DrawElementProto()
                dr_element.scale = zoom

                for st in zstyle:
                    if st.get('-x-kot-layer') == 'top':
                        st['z-index'] = float(st.get('z-index', 0)) + 15001.
                    if st.get('-x-kot-layer') == 'bottom':
                        st['z-index'] = float(st.get('z-index', 0)) - 15001.

                    if st.get('casing-width') not in (None, 0):  # and (st.get('width') or st.get('fill-color')):
                        dr_line = LineRuleProto()
                        dr_line.width = (st.get('width', 0) * WIDTH_SCALE) + (st.get('casing-width') * WIDTH_SCALE * 2)
                        dr_line.color = mwm_encode_color(st, "casing")
                        dr_line.priority = min(int(st.get('z-index', 0)), 20000)
                        dashes = st.get('casing-dashes', st.get('dashes', []))
                        dr_line.dashdot.dd.extend(dashes)
                        dr_line.cap = dr_linecaps.get(st.get('casing-linecap', 'butt'), BUTTCAP)
                        dr_line.join = dr_linejoins.get(st.get('casing-linejoin', 'round'), ROUNDJOIN)
                        dr_element.lines.extend([dr_line])

                    if st.get('width'):
                        dr_line = LineRuleProto()
                        dr_line.width = (st.get('width', 0) * WIDTH_SCALE)
                        dr_line.color = mwm_encode_color(st)
                        for i in st.get('dashes', []):
                            dr_line.dashdot.dd.extend([max(float(i), 1) * WIDTH_SCALE])
                        dr_line.cap = dr_linecaps.get(st.get('linecap', 'butt'), BUTTCAP)
                        dr_line.join = dr_linejoins.get(st.get('linejoin', 'round'), ROUNDJOIN)
                        dr_line.priority = min((int(st.get('z-index', 0)) + 1000), 20000)
                        dr_element.lines.extend([dr_line])

                    if st.get('pattern-image'):
                        dr_line = LineRuleProto()
                        dr_line.width = 0
                        dr_line.color = 0
                        dr_line.pathsym.name = st.get('pattern-image', "").replace(".svg", "")
                        dr_line.pathsym.step = float(st.get('pattern-spacing', 0)) - 16
                        dr_line.pathsym.offset = st.get('pattern-offset', 0)
                        dr_line.priority = int(st.get('z-index', 0)) + 1000
                        dr_element.lines.extend([dr_line])

                    if has_icons:
                        if st.get('icon-image'):
                            if not has_icons_for_areas:
                                dr_element.symbol.apply_for_type = 1
                            dr_element.symbol.name = st.get('icon-image', "").replace(".svg", "")
                            dr_element.symbol.priority = min(19100, (16000 + int(st.get('z-index', 0))))
                            has_icons = False
                        if st.get('symbol-shape'):
                            dr_element.circle.radius = float(st.get('symbol-size'))
                            dr_element.circle.color = mwm_encode_color(st, 'symbol-fill')
                            dr_element.circle.priority = min(19000, (15000 + int(st.get('z-index', 0))))
                            has_icons = False

                    if has_text and st.get('text'):
                        has_text = has_text[:2]
                        has_text.reverse()
                        dr_text = dr_element.path_text
                        base_z = 15000
                        if st.get('text-position', 'center') == 'line':
                            dr_text = dr_element.path_text
                            base_z = 16000
                        else:
                            dr_text = dr_element.caption
                        for sp in has_text[:]:
                            dr_cur_subtext = dr_text.primary
                            if len(has_text) == 2:
                                dr_cur_subtext = dr_text.secondary
                            dr_cur_subtext.height = int(float(sp.get('font-size', "10").split(",")[0]))
                            dr_cur_subtext.color = mwm_encode_color(sp, "text")
                            if st.get('text-halo-radius', 0) != 0:
                                dr_cur_subtext.stroke_color = mwm_encode_color(sp, "text-halo", "white")
                            if 'text-offset' in sp or 'text-offset-y' in sp:
                                dr_cur_subtext.offset_y = int(sp.get('text-offset-y', sp.get('text-offset', 0)))
                            if 'text-offset-x' in sp:
                                dr_cur_subtext.offset_x = int(sp.get('text-offset-x', 0))
                            has_text.pop()
                        dr_text.priority = min(19000, (base_z + int(st.get('z-index', 0))))
                        has_text = False

                    if has_fills:
                        if ('fill-color' in st) and (float(st.get('fill-opacity', 1)) > 0):
                            dr_element.area.color = mwm_encode_color(st, "fill")
                            if st.get('fill-position', 'foreground') == 'background':
                                if 'z-index' not in st:
                                    bgpos -= 1
                                dr_element.area.priority = (int(st.get('z-index', bgpos)) - 16000)
                            else:
                                dr_element.area.priority = (int(st.get('z-index', 0)) + 1 + 1000)
                            has_fills = False
                dr_cont.element.extend([dr_element])
        if dr_cont.element:
            drules.cont.extend([dr_cont])
        visibility["world|" + class_tree[cl] + "|"] = "".join(visstring)

    prevvis = []
    visnodes = set()
    drules_bin.write(drules.SerializeToString())
    drules_txt.write(unicode(drules))

    for k, v in visibility.iteritems():
        vis = k.split("|")
        for i in range(1, len(vis) - 1):
            visnodes.add("|".join(vis[0:i]) + "|")
    viskeys = list(set(visibility.keys() + list(visnodes)))

    def cmprepl(a, b):
        if a == b:
            return 0
        a = a.replace("|", "-")
        b = b.replace("|", "-")
        if a > b:
            return 1
        return -1
    viskeys.sort(cmprepl)

    oldoffset = ""
    for k in viskeys:
        offset = "    " * (k.count("|") - 1)
        for i in range(len(oldoffset) / 4, len(offset) / 4, -1):
            print >>visibility_file, "    " * i + "{}"
            print >>classificator_file, "    " * i + "{}"

        oldoffset = offset
        end = "-"
        if k in visnodes:
            end = "+"
        print >>visibility_file, offset + k.split("|")[-2] + "  " + visibility.get(k, "0" * (options.maxzoom + 1)) + "  " + end
        print >>classificator_file, offset + k.split("|")[-2] + "  " + end
    for i in range(len(offset) / 4, 0, -1):
        print >>visibility_file, "    " * i + "{}"
        print >>classificator_file, "    " * i + "{}"
