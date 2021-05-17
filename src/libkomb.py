from mapcss import MapCSS
import json
import mapcss.webcolors

whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex

style = MapCSS(0, 30)
# style.parse(open("styles/osmosnimki-maps.mapcss", "r").read())
style.parse(filename="styles/clear/style-clear/style.mapcss")
# style.parse(filename="styles/test.mapcss")


def to_mapbox_condition(condition):
    t = condition.type
    params = condition.params

    # TODO:
    if params[0] == "::class":
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
        return ["<", ["get", params[0]], "yes"]
    if t == "<=":
        return ["<=", ["get", params[0]], "yes"]
    if t == ">":
        return [">", ["get", params[0]], "yes"]
    if t == ">=":
        return [">=", ["get", params[0]], "yes"]

    return True

mapbox_linecaps = {
    'none': 'butt',
    'butt': 'butt',
    'round': 'round',
    'square': 'square'
}

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
            "tiles": ["http://localhost:3000/{z}-{x}-{y}.mvt"],
            "type": "vector",
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
        if condition.type in ("eq", "ne", "<", "<=", ">", ">="):
            tags[condition.params[0]] = condition.params[1]
        elif condition.type == "true":
            tags[condition.params[0]] = "yes"
        elif condition.type == "untrue":
            tags[condition.params[0]] = "no"
        elif condition.type == "set":
            tags[condition.params[0]] = condition.params[0]

    tags["name"] = "name"
    tags["addr:housenumber"] = "addr:housenumber"
    tags["addr:housename"] = "addr:housename"
    tags["ref"] = "ref"
    tags["int_name"] = "int_name"
    tags["addr:flats"] = "addr:flats"

    mapbox_style_layer_filter = ["all"] + map(to_mapbox_condition, conditions)

    for zoom in range(0, 24):
        zstyle = {}
        zstyle = style.get_style_dict(subject, tags, zoom, olddict=zstyle, cache=False);
        zstyle = zstyle.values()

        has_lines = False
        for st in zstyle:
            zindex = st.get("z-index", 0)

            if "width" in st and "color" in st:
                mapbox_style_layer = {
                    "zindex": zindex,
                    "priority": min((int(st.get("z-index", 0)) + 1000), 20000),
                    "type": "line",
                    "minzoom": zoom,
                    "maxzoom": zoom + 1,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    "id": str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["paint"]["line-width"] = st.get("width", 0)
                mapbox_style_layer["paint"]["line-color"] = whatever_to_hex(
                    st.get("color")
                )
                if st.get("opacity"):
                    mapbox_style_layer["paint"]["line-opacity"] = st.get("opacity")
                if st.get("dashes"):
                    mapbox_style_layer["paint"]["line-dasharray"] = st.get("dashes")
                if st.get("linecap"):
                    mapbox_style_layer["layout"]["line-cap"] = mapbox_linecaps[st.get("linecap")]
                if st.get("linejoin"):
                    mapbox_style_layer["layout"]["line-join"] = st.get("linejoin")

                mapbox_style_layer_id += 1

                mapbox_style_layers.append(mapbox_style_layer)
            if "fill-color" in st:
                mapbox_style_layer = {
                    "zindex": zindex,
                    "type": "fill",
                    "minzoom": zoom,
                    "maxzoom": zoom + 1,
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

                mapbox_style_layer["paint"]["fill-color"] = whatever_to_hex(
                    st.get("fill-color")
                )
                if st.get("fill-opacity"):
                    mapbox_style_layer["paint"]["fill-opacity"] = st.get("fill-opacity")

                mapbox_style_layer_id += 1

                mapbox_style_layers.append(mapbox_style_layer)
            if st.get("text"):
                mapbox_style_layer = {
                    "zindex": zindex,
                    "type": "symbol",
                    "minzoom": zoom,
                    "maxzoom": zoom + 1,
                    "filter": mapbox_style_layer_filter,
                    "layout": {},
                    "paint": {},
                    "id": str(mapbox_style_layer_id),
                    "source-layer": subject,
                    "source": "composite",
                }

                mapbox_style_layer["layout"]["text-field"] = ["get", st.get("text")]
                if st.get("text-position") == "line":
                    mapbox_style_layer["layout"]["symbol-placement"] = (
                        {"line": "line", "center": "line-center"}
                    )[st.get("text-position")]
                if st.get("font-size"):
                    mapbox_style_layer["layout"]["text-size"] = float(
                        st.get("font-size").split(",").pop()
                    )
                if st.get("text-transform"):
                    mapbox_style_layer["layout"]["text-transform"] = st.get(
                        "text-transform"
                    )
                if st.get("text-allow-overlap"):
                    mapbox_style_layer["layout"]["text-allow-overlap"] = st.get(
                        "text-allow-overlap"
                    )
                if st.get("text-offset"):
                    mapbox_style_layer["layout"]["text-offset"] = [
                        0,
                        st.get("text-offset"),
                    ]
                if st.get("text-color"):
                    mapbox_style_layer["paint"]["text-color"] = whatever_to_hex(st.get("text-color"))
                if st.get("text-opacity"):
                    mapbox_style_layer["paint"]["text-opacity"] = st.get("text-opacity")
                if st.get("text-halo-radius"):
                    mapbox_style_layer["paint"]["text-halo-width"] = float(st.get("text-halo-radius"))
                if st.get("text-halo-color"):
                    mapbox_style_layer["paint"]["text-halo-color"] = whatever_to_hex(st.get("text-halo-color"))

                base_z = 15000
                mapbox_style_layer["priority"] = min(
                    19000, (base_z + int(st.get("z-index", 0)))
                )

                mapbox_style_layer_id += 1

                mapbox_style_layers.append(mapbox_style_layer)


mapbox_style["layers"] = sorted(mapbox_style["layers"], key=lambda k: k["priority"])

print(json.dumps(mapbox_style))
