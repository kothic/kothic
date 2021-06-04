from mapcss import MapCSS
import json
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


# def to_mapbox_expression(values_by_zoom, default=None):
#     stops = []
#     for zoom in range(0, 24):
#         if zoom in values_by_zoom:
#             stops.append([zoom, values_by_zoom[zoom]])

#     expression = { "stops": stops }
#     if default is not None:
#         expression["default"] = default

#     return expression


def to_mapbox_expression(values_by_zoom, default=None):
    l = values_by_zoom.values()
    if all(x == l[0] for x in l):
        return l[0]

    expression = ["step", ["zoom"], values_by_zoom.values().pop()]

    for zoom in range(0, 23):
        if zoom in values_by_zoom:
            expression.append(zoom)
            expression.append(values_by_zoom[zoom])

    return expression


mapbox_linecaps = {"none": "butt", "butt": "butt", "round": "round", "square": "square"}


def komap_mapbox(style):
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

    mapbox_style_layers = [
        {
            "zindex": -30000,
            "priority": -30000,
            "type": "background",
            "paint": {"background-color": "#E3E1D2"},
            "id": "bg",
        }
    ]

    mapbox_style = {
        "version": 8,
        "name": "Basemap",
        "metadata": {},
        "sources": {
            "composite": {
                # "tiles": ["http://localhost:3000/{z}-{x}-{y}.mvt"],
                # "tiles": ["http://localhost:7800/public.basemap/{z}/{x}/{y}.mvt"],
                "tiles": [
                    "https://geocint.kontur.io/pgtileserv/public.basemap/{z}/{x}/{y}.mvt"
                ],
                "type": "vector",
                "maxzoom": 14
            }
        },
        "glyphs": "mapbox://fonts/mapbox/{fontstack}/{range}.pbf",
        "center": [27.582705, 53.908227],
        "zoom": 15,
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

        tags = {}
        for condition in conditions:
            # < <= > >= require more checks
            if condition.type in ("eq", "ne", "<", "<=", ">", ">="):
                tags[condition.params[0]] = condition.params[1]
            elif condition.type == "true":
                tags[condition.params[0]] = "yes"
            elif condition.type == "untrue":
                tags[condition.params[0]] = "no"
            elif condition.type == "set":
                tags[condition.params[0]] = condition.params[0]
            # elif condition.type == "unset"

        tags["name"] = "name"
        tags["addr:housenumber"] = "addr:housenumber"
        tags["addr:housename"] = "addr:housename"
        tags["ref"] = "ref"
        tags["int_name"] = "int_name"
        tags["addr:flats"] = "addr:flats"

        mapbox_style_layer_filter = ["all"] + map(to_mapbox_condition, conditions)

        zs = {}
        for zoom in range(0, 24):
            zstyle = style.get_style_dict(subject, tags, zoom, olddict={}, cache=False)
            for key, st in zstyle.items():
                if key not in zs:
                    zs[key] = {}
                zss = zs[key]
                for (prop_name, prop_value) in st.items():
                    if prop_name not in zss:
                        zss[prop_name] = {}
                    zss[prop_name][zoom] = prop_value

        zzs = []
        for key in zs:
            break_zs = []
            prev = (None, None, None)
            for zoom in range(0, 23):
                z_indexes = zs[key].get("z-index", {})
                fill_positions = zs[key].get("fill-position", {})
                casing_linecaps = zs[key].get("casing-linecap", {})
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
                for (prop_name, prop_value_by_zoom) in zs[key].items():
                    t = {
                        z: v
                        for z, v in prop_value_by_zoom.items()
                        if z >= minzoom and z < maxzoom
                    }
                    if len(t) > 0:
                        st[prop_name] = t

                if "z-index" in zs[key]:
                    st["z-index"] = zs[key]["z-index"].get(minzoom, 0)
                if "fill-position" in zs[key]:
                    st["fill-position"] = zs[key]["fill-position"].get(
                        minzoom, "foreground"
                    )
                if "casing-linecap" in zs[key]:
                    st["casing-linecap"] = zs[key]["casing-linecap"].get(
                        minzoom, "butt"
                    )

                zzs.append((minzoom, maxzoom, st))

        for (minzoom, maxzoom, st) in zzs:
            if st.get("casing-width") and st.get("casing-color"):
                mapbox_style_layer = {
                    "type": "line",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    "id": str(mapbox_style_layer_id) + "-casing",
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["minzoom"] = [
                    z for z, v in st.get("casing-width").items() if v > 0
                ][0]
                mapbox_style_layer["paint"]["line-width"] = to_mapbox_expression(
                    {
                        z: v * 2 + st.get("width", {}).get(z, 0)
                        for z, v in st.get("casing-width").items()
                    },
                    default=0,
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
                        int(st.get("z-index", 0)), 20000
                    )
                if st.get("casing-linecap", "round") != "butt":
                    mapbox_style_layer["priority"] = -15000

                mapbox_style_layer_id += 1
                mapbox_style_layers.append(mapbox_style_layer)
            if "width" in st and "color" in st:
                mapbox_style_layer = {
                    "priority": min((int(st.get("z-index", 0)) + 1000), 20000),
                    "type": "line",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    "id": str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["minzoom"] = [
                    z for z, v in st.get("width").items() if v > 0
                ][0]

                mapbox_style_layer["paint"]["line-width"] = to_mapbox_expression(
                    st.get("width"), default=0
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
            if "fill-color" in st:
                # if False:
                mapbox_style_layer = {
                    "type": "fill",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    "id": str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                if st.get("fill-position", "foreground") == "background":
                    if "z-index" not in st:
                        bgpos -= 1
                    mapbox_style_layer["priority"] = (
                        int(st.get("z-index", bgpos)) - 16000
                    )
                else:
                    mapbox_style_layer["priority"] = (
                        int(st.get("z-index", 0)) + 1 + 1000
                    )

                mapbox_style_layer["paint"]["fill-color"] = to_mapbox_expression(
                    {z: whatever_to_hex(v) for z, v in st.get("fill-color").items()}
                )

                if st.get("fill-opacity"):
                    mapbox_style_layer["paint"]["fill-opacity"] = to_mapbox_expression(
                        st.get("fill-opacity"), default=0
                    )

                mapbox_style_layer_id += 1
                mapbox_style_layers.append(mapbox_style_layer)
            if st.get("text"):
                mapbox_style_layer = {
                    "type": "symbol",
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    "id": str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                if subject == "area":
                    mapbox_style_layer["filter"] = mapbox_style_layer["filter"] + [
                        ["==", ["geometry-type"], "Point"]
                    ]

                mapbox_style_layer["minzoom"] = [
                    z for z, v in st.get("text").items() if v > 0
                ][0]

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
                    ] = to_mapbox_expression({ z: v == "true" for z, v in st.get("text-allow-overlap").items()})
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


# style.parse(open("styles/osmosnimki-maps.mapcss", "r").read())
# style.parse(filename="styles/clear/style-clear/style.mapcss")

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--stylesheet", dest="filename", metavar="FILE")

    (options, args) = parser.parse_args()

    style = MapCSS(0, 30)
    style.parse(filename=options.filename)

    mapbox_style = komap_mapbox(style)

    print(json.dumps(mapbox_style))
