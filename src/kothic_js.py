from dataclasses import dataclass, field
import argparse
import ast as py_ast
import json
import re
from pathlib import Path

try:
    from .mapcss import MapCSS, parseCondition
    from .mapcss.Eval import Eval
    from .mapcss.webcolors.webcolors import cairo_to_hex
except ImportError:
    from mapcss import MapCSS, parseCondition
    from mapcss.Eval import Eval
    from mapcss.webcolors.webcolors import cairo_to_hex


VALUE_CONDITIONS = {"eq", "ne", "regex", "<", "<=", ">", ">=", "true", "untrue"}
PRESENCE_CONDITIONS = {"set", "unset"}
IMAGE_PROPERTIES = {"icon-image", "fill-image"}
NUMERIC_PROPERTIES = {
    "z-index",
    "width",
    "opacity",
    "fill-opacity",
    "casing-width",
    "casing-opacity",
    "text-offset",
    "max-width",
    "text-halo-radius",
}
JS_CONDITION_OPERATORS = {
    "eq": "===",
    "ne": "!==",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
}
JS_BINARY_OPERATORS = {
    py_ast.Add: "+",
    py_ast.Sub: "-",
    py_ast.Mult: "*",
    py_ast.Div: "/",
    py_ast.Mod: "%",
}
JS_COMPARISON_OPERATORS = {
    py_ast.Eq: "===",
    py_ast.NotEq: "!==",
    py_ast.Lt: "<",
    py_ast.LtE: "<=",
    py_ast.Gt: ">",
    py_ast.GtE: ">=",
}
MAPCSS_EVAL_FUNCTIONS = {
    "any",
    "boolean",
    "int",
    "join",
    "list",
    "max",
    "metric",
    "min",
    "num",
    "sqrt",
    "str",
    "zmetric",
}
COMMENT = re.compile(r"/\*.*?\*/", re.S)
CONDITION = re.compile(r"\[(.+?)\]", re.S)
RULE_BLOCK = re.compile(r"([^{}]+)(\{[^{}]*\})", re.S)
SUBPART = re.compile(r"(::[-*\w]+)")
UNSUPPORTED_PARENT_SELECTOR = "__kothic_js_unsupported_parent_selector__"


@dataclass
class KothicJsMetadata:
    sprite_images: dict = field(default_factory=dict)
    external_images: list = field(default_factory=list)
    presence_tags: list = field(default_factory=list)
    value_tags: list = field(default_factory=list)
    subparts: list = field(default_factory=list)


def collect_metadata(style):
    """Collect the kothic-js style module metadata available from MapCSS."""
    images = set()
    subparts = {"default"}
    presence_tags = set()
    value_tags = set()

    for chooser in style.choosers:
        for rule in chooser.ruleChains:
            _collect_rule_metadata(rule, presence_tags, value_tags, subparts)

        for declaration in chooser.styles:
            _collect_declaration_metadata(declaration, images, value_tags)

    presence_tags -= value_tags

    return KothicJsMetadata(
        sprite_images={},
        external_images=sorted(images),
        presence_tags=sorted(presence_tags),
        value_tags=sorted(value_tags),
        subparts=sorted(subparts),
    )


def generate_style_module(style, name):
    metadata = collect_metadata(style)
    subparts = metadata.subparts
    declarations = []

    for chooser in style.choosers:
        selector_js = [
            _rule_js(rule)
            for rule in chooser.ruleChains
        ]
        selector_js = [selector for selector in selector_js if selector]

        if not selector_js:
            continue

        body = []
        for declaration in chooser.styles:
            subpart = _chooser_subpart(chooser)
            for key, value in declaration.items():
                body.append(_style_statement_js(subpart, key, value))

        declarations.append(
            "        if (%s) {\n%s\n        }" % (
                " || ".join("(%s)" % selector for selector in selector_js),
                "\n".join(body),
            )
        )

    subpart_vars = ", ".join("s_%s = {}" % subpart for subpart in subparts)
    subpart_fill = "\n".join(
        "        if (Object.keys(s_%s).length) {\n"
        "            style[%s] = s_%s;\n"
        "        }" % (subpart, _js_string(subpart), subpart)
        for subpart in subparts
    )

    return """(function (MapCSS) {
    'use strict';

    function restyle(style, tags, zoom, type, selector) {
        var %s;
%s
%s
        return style;
    }

    var sprite_images = %s,
        external_images = %s,
        presence_tags = %s,
        value_tags = %s;

    MapCSS.loadStyle(%s, restyle, sprite_images, external_images, presence_tags, value_tags);
    MapCSS.preloadExternalImages(%s);
})(MapCSS);
""" % (
        subpart_vars,
        "\n".join(declarations),
        subpart_fill,
        json.dumps(metadata.sprite_images, sort_keys=True),
        json.dumps(metadata.external_images),
        json.dumps(metadata.presence_tags),
        json.dumps(metadata.value_tags),
        _js_string(name),
        _js_string(name),
    )


def convert_file(
    input_path,
    output_path=None,
    name=None,
    static_tags=None,
    dynamic_tags=None,
    minzoom=0,
    maxzoom=19,
):
    input_path = Path(input_path)
    if name is None:
        name = input_path.with_suffix("").as_posix()

    return convert_files(
        [input_path],
        output_path=output_path,
        name=name,
        static_tags=static_tags,
        dynamic_tags=dynamic_tags,
        minzoom=minzoom,
        maxzoom=maxzoom,
    )


def convert_files(
    input_paths,
    output_path=None,
    name=None,
    static_tags=None,
    dynamic_tags=None,
    minzoom=0,
    maxzoom=19,
):
    input_paths = [Path(input_path) for input_path in input_paths]
    if not input_paths:
        raise ValueError("At least one MapCSS input file is required")
    if name is None:
        name = input_paths[0].with_suffix("").as_posix()

    dynamic_tags = dynamic_tags or set()
    css = "\n".join(prepare_css_for_js_conversion(input_path) for input_path in input_paths)
    inferred_static_tags = infer_static_tags_from_css(css)
    for dynamic_tag in dynamic_tags:
        inferred_static_tags.pop(dynamic_tag, None)
    inferred_static_tags.update(static_tags or {})

    parser = MapCSS(minzoom, maxzoom + 1)
    parser.parse(
        css=css,
        filename=", ".join(str(input_path) for input_path in input_paths),
        static_tags=inferred_static_tags,
        dynamic_tags=dynamic_tags,
        clamp=False,
    )

    js = generate_style_module(parser, name)
    if output_path is not None:
        Path(output_path).write_text(js)
    return js


def infer_static_tags(input_path):
    """Infer selector tags so kothic-js conversion can parse legacy MapCSS."""
    css = COMMENT.sub("", Path(input_path).read_text())
    return infer_static_tags_from_css(css)


def infer_static_tags_from_css(css):
    static_tags = {}
    for condition_text in CONDITION.findall(css):
        condition = parseCondition(condition_text)
        tag = condition.extract_tag()
        if tag != "*" and not tag.startswith("::"):
            static_tags[tag] = False
    return static_tags


def prepare_css_for_js_conversion(input_path):
    css = Path(input_path).read_text()

    def replace_rule(match):
        selectors = match.group(1)
        declaration = match.group(2)
        converted = [
            _unsupported_parent_selector(selector) if ">" in selector else selector
            for selector in selectors.split(",")
        ]
        return ",".join(converted) + declaration

    return RULE_BLOCK.sub(replace_rule, css)


def _unsupported_parent_selector(selector):
    subpart_match = SUBPART.search(selector)
    subpart = subpart_match.group(1) if subpart_match else ""
    return UNSUPPORTED_PARENT_SELECTOR + subpart


def _collect_rule_metadata(rule, presence_tags, value_tags, subparts):
    for condition in rule.conditions:
        if condition.params[0].startswith("::"):
            if condition.type == "eq" and condition.params[1].startswith("::"):
                subparts.add(_normalize_subpart(condition.params[1]))
            continue

        if condition.type in VALUE_CONDITIONS:
            value_tags.add(condition.params[0])
        elif condition.type in PRESENCE_CONDITIONS:
            presence_tags.add(condition.params[0])


def _collect_declaration_metadata(declaration, images, value_tags):
    for key, value in declaration.items():
        if key in IMAGE_PROPERTIES:
            images.add(value)

        if key == "text" and isinstance(value, str):
            value_tags.add(value)

        if isinstance(value, Eval):
            value_tags.update(value.extract_tags())


def _normalize_subpart(subpart):
    if subpart.startswith("::"):
        subpart = subpart[2:]
    if subpart == "*":
        return "everything"
    return subpart.replace("-", "_") or "default"


def _chooser_subpart(chooser):
    for rule in chooser.ruleChains:
        for condition in rule.conditions:
            if (
                condition.type == "eq"
                and condition.params[0].startswith("::")
                and condition.params[1].startswith("::")
            ):
                return _normalize_subpart(condition.params[1])
    return "default"


def _rule_js(rule):
    parts = [_subject_js(rule.subject), _zoom_js(rule.minZoom, rule.maxZoom)]
    for condition in rule.conditions:
        if condition.params[0].startswith("::"):
            continue
        parts.append(_condition_js(condition))
    return " && ".join(part for part in parts if part)


def _subject_js(subject):
    if subject == "*":
        return "true"
    if subject == "line":
        subject = "way"
    if subject in {"node", "way", "relation", "coastline"}:
        return "type === %s" % _js_string(subject)
    return "selector === %s" % _js_string(subject)


def _zoom_js(min_zoom, max_zoom):
    parts = []
    if min_zoom > 0:
        parts.append("zoom >= %d" % min_zoom)
    if max_zoom < 19:
        parts.append("zoom <= %d" % max_zoom)
    return " && ".join(parts)


def _condition_js(condition):
    condition_type = condition.type
    key = condition.params[0]
    key_js = _js_string(key)

    if condition_type == "eq" and condition.params[1] == "yes":
        return _yes_condition_js(key_js)
    if condition_type == "ne" and condition.params[1] == "yes":
        return _no_condition_js(key_js)
    if condition_type in JS_CONDITION_OPERATORS:
        value = condition.params[1]
        return "tags[%s] %s %s" % (
            key_js,
            JS_CONDITION_OPERATORS[condition_type],
            _js_string(value),
        )
    if condition_type == "regex":
        return "RegExp(%s, 'i').test(tags[%s] || '')" % (
            _js_string(condition.params[1]),
            key_js,
        )
    if condition_type == "true":
        return _yes_condition_js(key_js)
    if condition_type == "set":
        return "tags.hasOwnProperty(%s)" % key_js
    if condition_type == "untrue":
        return _no_condition_js(key_js)
    if condition_type == "unset":
        return "!tags.hasOwnProperty(%s)" % key_js
    return "false"


def _yes_condition_js(key_js):
    return "(tags[%s] === '1' || tags[%s] === 'true' || tags[%s] === 'yes')" % (
        key_js,
        key_js,
        key_js,
    )


def _no_condition_js(key_js):
    return "(!tags.hasOwnProperty(%s) || tags[%s] === '-1' || tags[%s] === 'false' || tags[%s] === 'no')" % (
        key_js,
        key_js,
        key_js,
        key_js,
    )


def _style_statement_js(subpart, key, value):
    if isinstance(value, Eval):
        value_js = _eval_js(value, subpart)
    elif key == "text" and isinstance(value, str):
        value_js = "MapCSS.e_localize(tags, %s)" % _js_string(value)
    else:
        value_js = _style_value_js(key, value)

    return "            s_%s[%s] = %s;" % (
        subpart,
        _js_string(key),
        value_js,
    )


def _style_value_js(key, value):
    if isinstance(value, tuple):
        return _js_string(cairo_to_hex(value))
    if key in NUMERIC_PROPERTIES and isinstance(value, (int, float)):
        return str(int(value)) if float(value).is_integer() else str(value)
    return _js_string(value)


def _js_string(value):
    return json.dumps(str(value))


def _eval_js(value, subpart):
    tree = py_ast.parse(value.expr_text, mode="eval")
    return _eval_node_js(tree.body, subpart)


def _eval_node_js(node, subpart):
    if isinstance(node, py_ast.Constant):
        if isinstance(node.value, str):
            return _js_string(node.value)
        return json.dumps(node.value)

    if isinstance(node, py_ast.Name):
        if node.id in {"True", "False"}:
            return node.id.lower()
        raise NotImplementedError("Unsupported eval() name: %s" % node.id)

    if isinstance(node, py_ast.UnaryOp):
        if isinstance(node.op, py_ast.USub):
            return "-%s" % _eval_node_js(node.operand, subpart)
        if isinstance(node.op, py_ast.UAdd):
            return "+%s" % _eval_node_js(node.operand, subpart)

    if isinstance(node, py_ast.BinOp):
        operator = JS_BINARY_OPERATORS.get(type(node.op))
        if operator is None:
            raise NotImplementedError("Unsupported eval() binary operator: %s" % type(node.op).__name__)
        return "(%s %s %s)" % (
            _eval_node_js(node.left, subpart),
            operator,
            _eval_node_js(node.right, subpart),
        )

    if isinstance(node, py_ast.Compare):
        return _compare_js(node, subpart)

    if isinstance(node, py_ast.Call):
        return _eval_call_js(node, subpart)

    raise NotImplementedError("Unsupported eval() expression: %s" % type(node).__name__)


def _compare_js(node, subpart):
    parts = []
    left = node.left
    for operator, comparator in zip(node.ops, node.comparators):
        js_operator = JS_COMPARISON_OPERATORS.get(type(operator))
        if js_operator is None:
            raise NotImplementedError("Unsupported eval() comparison operator: %s" % type(operator).__name__)
        parts.append(
            "%s %s %s" % (
                _eval_node_js(left, subpart),
                js_operator,
                _eval_node_js(comparator, subpart),
            )
        )
        left = comparator
    return "(%s)" % " && ".join(parts)


def _eval_call_js(node, subpart):
    if not isinstance(node.func, py_ast.Name):
        raise NotImplementedError("Unsupported eval() call target")

    function = node.func.id
    args = [_eval_node_js(arg, subpart) for arg in node.args]

    if function == "tag":
        return "MapCSS.e_tag(tags, %s)" % ", ".join(args)

    if function == "prop":
        return "MapCSS.e_prop(s_%s, %s)" % (subpart, ", ".join(args))

    if function == "cond":
        if len(args) != 3:
            raise NotImplementedError("cond() eval emission expects exactly three arguments")
        return "(%s ? %s : %s)" % (args[0], args[1], args[2])

    if function in MAPCSS_EVAL_FUNCTIONS:
        return "MapCSS.e_%s(%s)" % (function, ", ".join(args))

    raise NotImplementedError("Unsupported eval() function: %s" % function)


def _parse_static_tag(value):
    if ":" not in value:
        return value, True

    name, tag_type = value.rsplit(":", 1)
    return name, tag_type.lower() not in {"0", "false", "no", "dynamic"}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert MapCSS into a kothic-js style module."
    )
    parser.add_argument("-i", "--mapcss", required=True, help="MapCSS input file")
    parser.add_argument("-n", "--name", help="Style name for MapCSS.loadStyle")
    parser.add_argument("-o", "--output", help="Output JavaScript file")
    parser.add_argument("--minzoom", default=0, type=int, help="Minimal available zoom level")
    parser.add_argument("--maxzoom", default=19, type=int, help="Maximal available zoom level")
    parser.add_argument(
        "--static-tag",
        action="append",
        default=[],
        help="Known parser tag as key[:true|false]. Use false for presence-only tags.",
    )
    parser.add_argument(
        "--dynamic-tag",
        action="append",
        default=[],
        help="Known dynamic parser tag.",
    )
    args = parser.parse_args(argv)

    static_tags = dict(_parse_static_tag(tag) for tag in args.static_tag)
    dynamic_tags = set(args.dynamic_tag)
    js = convert_file(
        args.mapcss,
        output_path=args.output,
        name=args.name,
        static_tags=static_tags,
        dynamic_tags=dynamic_tags,
        minzoom=args.minzoom,
        maxzoom=args.maxzoom,
    )

    if args.output is None:
        print(js, end="")


if __name__ == "__main__":
    main()
