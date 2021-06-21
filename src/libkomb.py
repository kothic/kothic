from mapcss import MapCSS, Condition
import json
import sys
import mapcss.webcolors
from optparse import OptionParser

whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex

def to_mapbox_condition(condition):
    t = condition.type
    params = condition.params

    # if params[0] == "::class":
    if params[0][:2] == "::":
        return True

    if t == "eq":
        return ["==", ["get", params[0]], params[1]]
    if t == "ne":
        return ["!=", ["get", params[0]], params[1]]
    if t == "regex":
        return True
    if t == "true":
        return ["==", ["get", params[0]], "yes"]
    if t == "untrue":
        return ["==", ["get", params[0]], "no"]
    if t == "set":
        return ["to-boolean", ["get", params[0]]]
    if t == "unset":
        return ["!", ["to-boolean", ["get", params[0]]]]
    if t == "<":
        return ["<", ["to-number", ["get", params[0]]], float(params[1])]
    if t == "<=":
        return ["<=", ["to-number", ["get", params[0]]], float(params[1])]
    if t == ">":
        return [">", ["to-number", ["get", params[0]]], float(params[1])]
    if t == ">=":
        return [">=", ["to-number", ["get", params[0]]], float(params[1])]

    return True


def to_mapbox_expression(values_by_zoom):
    values_by_zoom = values_by_zoom.items()
    values_by_zoom = sorted(values_by_zoom, key=lambda k: k[0])
    j = 0
    for i in range(1, len(values_by_zoom)):
        if values_by_zoom[i][1] != values_by_zoom[i - 1][1]:
            j += 1
            values_by_zoom[j] = values_by_zoom[i]
    values_by_zoom = values_by_zoom[0 : j + 1]

    if len(values_by_zoom) == 1:
        return values_by_zoom[0][1]

    expression = ["step", ["zoom"], values_by_zoom[0][1]]
    for (zoom, value) in values_by_zoom:
        expression.append(zoom)
        expression.append(value)

    return expression


mapbox_linecaps = {"none": "butt", "butt": "butt", "round": "round", "square": "square"}

def komap_mapbox(style, options):
    l = []
    for chooser in style.choosers:
        for rule in chooser.ruleChains:
            l.append((rule.subject, rule.conditions))

    l = [
        tuple([subject, list(conditions)])
        for subject, conditions in set(
            tuple([subject, tuple(conditions)]) for subject, conditions in l
        )
    ]

    mapbox_style_layers = []

    canvas_style = style.get_style_dict("canvas", {}, 0, olddict={}, cache=False)
    if canvas_style["::default"] is not None:
        background_style_layer = {
            "priority": -30000,
            "type": "background",
            "paint": {},
            "layout": {},
            "id": "bg",
        }

        if "background-color" in canvas_style["::default"]:
            background_style_layer["paint"]["background-color"] = whatever_to_hex(
                canvas_style["::default"]["background-color"]
            )

        mapbox_style_layers.append(background_style_layer)

    mapbox_style = {
        "version": 8,
        "name": "Basemap",
        "metadata": {},
        "sources": {
            "composite": {
                "tiles": [
                    options.tiles_url
                ],
                "type": "vector",
                "maxzoom": int(options.max_zoom),
            }
        },
        "glyphs": options.glyphs_url,
        "center": [27.582705, 53.908227],
        "zoom": 1,
        "layers": mapbox_style_layers,
        "id": "basemap",
    }

    mapbox_style_layer_id = 0

    bgpos = 0

    for subject, conditions in l:
        """
            TODO:
            if subject == "" then everything
            if subject == "way" then "line" + "area"
        """
        if subject not in ("area", "line", "node"):
            continue

        mapbox_style_layer_filter = ["all"] + map(to_mapbox_condition, conditions)
        conditions += [Condition('set', (c.params[0],)) for c in conditions if c.type in ('eq', 'true' '<', '<=', '>', '>=')]

        if len([c for c in conditions if c.type == 'eq' and c.params[0] == '::class']) == 0:
            conditions.append(Condition('eq', ('::class', '::default')))

        zs = {}
        for zoom in range(0, 24):
            zstyle = style.get_style_dict_2(subject, conditions, zoom)

            if 'text' in zstyle:
                tags = {}
                tags["name"] = "name"
                tags["addr:housenumber"] = "addr:housenumber"
                tags["addr:housename"] = "addr:housename"
                tags["ref"] = "ref"
                tags["int_name"] = "int_name"
                tags["addr:flats"] = "addr:flats"

                zstyle["text"] = zstyle["text"].compute(tags, {})

            for (prop_name, prop_value) in zstyle.items():
                if prop_name not in zs:
                    zs[prop_name] = {}
                zs[prop_name][zoom] = prop_value
        
        zzs = []
        break_zs = []
        prev = (None, None, None)
        for zoom in range(0, 23):
            z_indexes = zs.get("z-index", {})
            fill_positions = zs.get("fill-position", {})
            casing_linecaps = zs.get("casing-linecap", {})
            curr = (
                z_indexes.get(zoom, 0),
                fill_positions.get(zoom, "foreground"),
                casing_linecaps.get(zoom, "butt"),
            )
            if prev != curr:
                break_zs.append(zoom)
                prev = curr
        break_zs.append(24)
        for (minzoom, maxzoom) in list(zip(break_zs, break_zs[1:])):
            st = {}
            for (prop_name, prop_value_by_zoom) in zs.items():
                t = {
                    z: v
                    for z, v in prop_value_by_zoom.items()
                    if z >= minzoom and z < maxzoom
                }
                if len(t) > 0:
                    st[prop_name] = t

            if "z-index" in zs:
                st["z-index"] = zs["z-index"].get(minzoom, 0)
            if "fill-position" in zs:
                st["fill-position"] = zs["fill-position"].get(
                    minzoom, "foreground"
                )
            if "casing-linecap" in zs:
                st["casing-linecap"] = zs["casing-linecap"].get(
                    minzoom, "butt"
                )

            zzs.append((minzoom, maxzoom, st))

        for (minzoom, maxzoom, st) in zzs:
            if st.get("casing-width") and any(v > 0 for v in st.get("casing-width").values()):
                mapbox_style_layer = {
                    "type": "line",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    # "id": str(mapbox_style_layer_id) + "-casing",
                    # "id": "+".join([str(c) for c in conditions]) + "casing" + str(mapbox_style_layer_id),
                    "id": "+".join(build_kepler_hints(conditions)) + "casing" + str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["minzoom"] = sorted(st.get("casing-width").items(), key=lambda k: k[0])[0][0]

                mapbox_style_layer["paint"]["line-width"] = to_mapbox_expression(
                    {
                        z: v * 2 + st.get("width", {}).get(z, 0)
                        for z, v in st.get("casing-width").items()
                    },
                )

                mapbox_style_layer["paint"]["line-color"] = to_mapbox_expression(
                    {z: whatever_to_hex(v) for z, v in st.get("casing-color").items()}
                )

                if st.get("casing-opacity"):
                    mapbox_style_layer["paint"]["line-opacity"] = to_mapbox_expression(
                        st.get("casing-opacity")
                    )
                if st.get("casing-dashes"):
                    mapbox_style_layer["paint"][
                        "line-dasharray"
                    ] = to_mapbox_expression(
                        {z: ["literal", v] for z, v in st.get("casing-dashes").items()}
                    )
                if st.get("casing-linecap"):
                    mapbox_style_layer["layout"]["line-cap"] = mapbox_linecaps[
                        st.get("casing-linecap")
                    ]
                if st.get("casing-linejoin"):
                    mapbox_style_layer["layout"]["line-join"] = to_mapbox_expression(
                        st.get("casing-linejoin")
                    )

                if st.get("casing-linecap", "butt") == "butt":
                    mapbox_style_layer["priority"] = min(
                        int(st.get("z-index", 0)) + 999, 20000
                    )
                if st.get("casing-linecap", "round") != "butt":
                    mapbox_style_layer["priority"] = -15000

                mapbox_style_layer_id += 1
                mapbox_style_layers.append(mapbox_style_layer)
            if st.get("width") and any(v > 0 for v in st.get("width").values()) and st.get("color"):
                mapbox_style_layer = {
                    "priority": min((int(st.get("z-index", 0)) + 1000), 20000),
                    "type": "line",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    # "id": str(mapbox_style_layer_id),
                    # "id": "+".join([str(c) for c in conditions]) + "line" + str(mapbox_style_layer_id),
                    "id": "+".join(build_kepler_hints(conditions)) + str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["minzoom"] = sorted(st.get("width").items(), key=lambda k: k[0])[0][0]

                mapbox_style_layer["paint"]["line-width"] = to_mapbox_expression(
                    st.get("width")
                )

                mapbox_style_layer["paint"]["line-color"] = to_mapbox_expression(
                    {z: whatever_to_hex(v) for z, v in st.get("color").items()}
                )

                if st.get("opacity"):
                    mapbox_style_layer["paint"]["line-opacity"] = to_mapbox_expression(
                        st.get("opacity")
                    )
                if st.get("dashes"):
                    mapbox_style_layer["paint"][
                        "line-dasharray"
                    ] = to_mapbox_expression(
                        {z: ["literal", v] for z, v in st.get("dashes").items()}
                    )
                if st.get("linecap"):
                    mapbox_style_layer["layout"]["line-cap"] = to_mapbox_expression(
                        {z: mapbox_linecaps[v] for z, v in st.get("linecap").items()}
                    )
                if st.get("linejoin"):
                    mapbox_style_layer["layout"]["line-join"] = to_mapbox_expression(
                        st.get("linejoin")
                    )

                mapbox_style_layer_id += 1
                mapbox_style_layers.append(mapbox_style_layer)
            if "fill-color" in st and any(v is not None for v in st.get("fill-color").values()):
                # if False:
                mapbox_style_layer = {
                    "type": "fill",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    # "id": str(mapbox_style_layer_id),
                    # "id": "+".join([str(c) for c in conditions]) + "fill" + str(mapbox_style_layer_id),
                    "id": "+".join(build_kepler_hints(conditions)) + str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["minzoom"] = sorted(st.get("fill-color").items(), key=lambda k: k[0])[0][0]

                if st.get("fill-position", "foreground") == "background":
                    if "z-index" not in st:
                        bgpos -= 1
                        mapbox_style_layer["priority"] = bgpos - 16000
                    else:
                        zzz = int(st.get("z-index", 0))
                        if zzz > 0:
                            mapbox_style_layer["priority"] = zzz - 16000
                        else:
                            mapbox_style_layer["priority"] = zzz - 16700
                else:
                    mapbox_style_layer["priority"] = (
                        int(st.get("z-index", 0)) + 1 + 1000
                    )

                mapbox_style_layer["paint"]["fill-color"] = to_mapbox_expression(
                    {z: whatever_to_hex(v) for z, v in st.get("fill-color").items()}
                )

                if st.get("fill-opacity"):
                    mapbox_style_layer["paint"]["fill-opacity"] = to_mapbox_expression(
                        st.get("fill-opacity")
                    )

                mapbox_style_layer_id += 1
                mapbox_style_layers.append(mapbox_style_layer)
            if st.get("text"):
            # if "text" in st and any(len(v) > 0 for v in st.get("text").values()):
                mapbox_style_layer = {
                    "type": "symbol",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {
                        "text-font": ["Roboto"],
                        # TODO: remove organicmaps specific thing
                        "symbol-sort-key": ["-", ["to-number", ["get", "population"]]]
                    },
                    "paint": {},
                    # "id": str(mapbox_style_layer_id),
                    # "id": "+".join([str(c) for c in conditions]) + "text" + str(mapbox_style_layer_id),
                    "id": "+".join(build_kepler_hints(conditions)) + str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                if subject == "area":
                    mapbox_style_layer["filter"] = mapbox_style_layer["filter"] + [
                        ["==", ["geometry-type"], "Point"]
                    ]

                mapbox_style_layer["minzoom"] = sorted(st.get("text").items(), key=lambda k: k[0])[0][0]

                mapbox_style_layer["layout"]["text-field"] = to_mapbox_expression(
                    {z: ["get", v] for z, v in st.get("text").items()}
                )

                # if st.get("text-position") == "line":
                # mapbox_style_layer["layout"]["symbol-placement"] = (
                #     {"line": "line", "center": "line-center"}
                # )[st.get("text-position")]

                if st.get("text-position"):
                    symbol_placement = {
                        z: v for z, v in st.get("text-position").items() if v == "line"
                    }
                    if len(symbol_placement) > 0:
                        mapbox_style_layer["layout"][
                            "symbol-placement"
                        ] = to_mapbox_expression(symbol_placement)

                if st.get("font-size"):
                    mapbox_style_layer["layout"]["text-size"] = to_mapbox_expression(
                        {
                            z: float(v.split(",").pop())
                            for z, v in st.get("font-size").items()
                        }
                    )
                if st.get("text-transform"):
                    mapbox_style_layer["layout"][
                        "text-transform"
                    ] = to_mapbox_expression(st.get("text-transform"))
                if st.get("text-allow-overlap"):
                    mapbox_style_layer["layout"][
                        "text-allow-overlap"
                    ] = to_mapbox_expression(
                        {
                            z: v == "true"
                            for z, v in st.get("text-allow-overlap").items()
                        }
                    )
                if st.get("text-offset"):
                    mapbox_style_layer["layout"]["text-offset"] = to_mapbox_expression(
                        {
                            z: ["literal", [0, float(v)]]
                            for z, v in st.get("text-offset").items()
                        }
                    )
                if st.get("text-color"):
                    mapbox_style_layer["paint"]["text-color"] = to_mapbox_expression(
                        {z: whatever_to_hex(v) for z, v in st.get("text-color").items()}
                    )
                if st.get("text-opacity"):
                    mapbox_style_layer["paint"]["text-opacity"] = to_mapbox_expression(
                        {z: float(v) for z, v in st.get("text-opacity").items()}
                    )
                if st.get("text-halo-radius"):
                    mapbox_style_layer["paint"][
                        "text-halo-width"
                    ] = to_mapbox_expression(
                        {z: float(v) for z, v in st.get("text-halo-radius").items()}
                    )
                if st.get("text-halo-color"):
                    mapbox_style_layer["paint"][
                        "text-halo-color"
                    ] = to_mapbox_expression(
                        {
                            z: whatever_to_hex(v)
                            for z, v in st.get("text-halo-color").items()
                        }
                    )

                base_z = 15000
                mapbox_style_layer["priority"] = min(
                    19000, (base_z + int(st.get("z-index", 0)))
                )

                mapbox_style_layer_id += 1
                mapbox_style_layers.append(mapbox_style_layer)

    mapbox_style["layers"] = sorted(mapbox_style["layers"], key=lambda k: k["priority"])

    return mapbox_style


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--stylesheet", "--stylesheet", dest="filename")
    parser.add_option("--tiles-url", "--tiles-url", dest="tiles_url")
    parser.add_option("--max-zoom", "--max-zoom", dest="max_zoom")
    parser.add_option("--glyphs-url", "--glyphs-url", dest="glyphs_url")

    (options, args) = parser.parse_args()

    if options.filename is None or options.tiles_url is None or options.max_zoom is None:
        sys.stderr.write(">>> required arguments are not passed")
        exit(1)

    style = MapCSS(0, 30)
    style.parse(filename=options.filename)

    mapbox_style = komap_mapbox(style, options)

    print(json.dumps(mapbox_style))
