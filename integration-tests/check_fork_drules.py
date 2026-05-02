#!/usr/bin/env python3

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FULL_DRULES_GEN = REPO_ROOT / "integration-tests" / "full_drules_gen.py"
sys.path.insert(0, str(REPO_ROOT / "src"))

ORGANICMAPS_REPO = "https://github.com/organicmaps/organicmaps.git"
ORGANICMAPS_COMMIT = "b3a04bee373ab723e661523166d8d37e45c9ed2e"

COMAPS_REPO = "https://codeberg.org/comaps/comaps.git"
COMAPS_COMMIT = "19e486669105dc419e3357aee62652f2771141ed"
COMAPS_KOTHIC_REPO = "https://codeberg.org/comaps/kothic.git"
COMAPS_KOTHIC_COMMIT = "1cba3a0347b21c1b20d36da0f4a3245bc27e0f38"

MAPSME_OMIM_REPO = "https://github.com/mapsme/omim.git"
MAPSME_OMIM_COMMIT = "1892903b63f2c85b16ed4966d21fe76aba06b9ba"
MAPSME_KOTHIC_REPO = "https://github.com/mapsme/kothic.git"
MAPSME_KOTHIC_COMMIT = "cbaff545dd5d2343dcbd30285884dd4afa509d93"

STYLE_NAMES = (
    "default_light",
    "default_dark",
    "outdoors_light",
    "outdoors_dark",
    "vehicle_light",
    "vehicle_dark",
)

STYLE_DATA_PATHS = (
    "data/mapcss-dynamic.txt",
    "data/mapcss-mapping.csv",
    "data/styles/default",
    "data/styles/outdoors",
    "data/styles/vehicle",
)

MAPSME_STYLE_DATA_PATHS = (
    "data/mapcss-dynamic.txt",
    "data/mapcss-mapping.csv",
    "data/styles/clear",
    "data/styles/vehicle",
)

ORGANICMAPS_BASELINE_PATHS = tuple(
    f"data/drules_proto_{style_name}.bin"
    for style_name in STYLE_NAMES
)

MAPSME_STYLES = (
    ("drules_proto_clear", "styles/clear/style-clear/style.mapcss"),
    ("drules_proto_dark", "styles/clear/style-night/style.mapcss"),
    ("drules_proto_vehicle_clear", "styles/vehicle/style-clear/style.mapcss"),
    ("drules_proto_vehicle_dark", "styles/vehicle/style-night/style.mapcss"),
)


def run(args, cwd=None, env=None):
    print("+", " ".join(str(arg) for arg in args), flush=True)
    subprocess.run(args, cwd=cwd, check=True, env=env)


def clone_sparse(repo, commit, destination, paths):
    destination.mkdir(parents=True)
    run(["git", "init", "--initial-branch", "ci", str(destination)])
    run(["git", "-C", str(destination), "remote", "add", "origin", repo])
    run(["git", "-C", str(destination), "sparse-checkout", "init", "--no-cone"])
    run(["git", "-C", str(destination), "sparse-checkout", "set", "--no-cone", *paths])
    run([
        "git", "-C", str(destination),
        "fetch", "--depth", "1", "--filter=blob:none", "origin", commit
    ])
    run(["git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD"])


def clone_full(repo, commit, destination):
    run(["git", "clone", "--depth", "1", repo, str(destination)])
    current_commit = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"],
        text=True
    ).strip()
    if current_commit != commit:
        run(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", commit])
        run(["git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD"])


def compare_files(generated, baseline, suffixes, generated_prefix="", baseline_prefix=""):
    for style_name in STYLE_NAMES:
        for suffix in suffixes:
            generated_file = generated / f"{generated_prefix}{style_name}{suffix}"
            baseline_file = baseline / f"{baseline_prefix}{style_name}{suffix}"
            if not filecmp.cmp(generated_file, baseline_file, shallow=False):
                raise SystemExit(f"{generated_file} differs from {baseline_file}")
            print(f"match {generated_file.name}", flush=True)


def compare_named_files(generated, baseline, names, suffixes):
    for name in names:
        for suffix in suffixes:
            generated_file = generated / f"{name}{suffix}"
            baseline_file = baseline / f"{name}{suffix}"
            if not filecmp.cmp(generated_file, baseline_file, shallow=False):
                raise SystemExit(f"{generated_file} differs from {baseline_file}")
            print(f"match {generated_file.name}", flush=True)


def normalize_drules(path):
    import drules_struct_pb2

    drules = drules_struct_pb2.ContainerProto()
    drules.ParseFromString(path.read_bytes())
    normalize_mapsme_oracle_port_artifacts(drules)
    return drules.SerializeToString(deterministic=True)


def normalize_mapsme_oracle_port_artifacts(message):
    """Normalize Python 2 -> 3 port noise in the temporary MAPS.ME oracle."""
    from google.protobuf.descriptor import FieldDescriptor

    for field, value in message.ListFields():
        if field.is_repeated:
            if field.message_type and field.full_name == "ColorsElementProto.value":
                value.sort(key=lambda item: (item.name, item.color, item.x, item.y))
            if field.message_type:
                for item in value:
                    normalize_mapsme_oracle_port_artifacts(item)
            elif field.type in (FieldDescriptor.TYPE_DOUBLE, FieldDescriptor.TYPE_FLOAT):
                rounded = [round(item, 12) for item in value]
                del value[:]
                value.extend(rounded)
        elif field.message_type:
            normalize_mapsme_oracle_port_artifacts(value)
        elif field.type in (FieldDescriptor.TYPE_DOUBLE, FieldDescriptor.TYPE_FLOAT):
            setattr(message, field.name, round(value, 12))


def compare_normalized_drules(generated, baseline, names):
    for name in names:
        generated_file = generated / f"{name}.bin"
        baseline_file = baseline / f"{name}.bin"
        if normalize_drules(generated_file) != normalize_drules(baseline_file):
            raise SystemExit(f"{generated_file} differs from {baseline_file}")
        print(f"match {generated_file.name}", flush=True)


def port_python2_fork_to_python3(checkout):
    try:
        from lib2to3.refactor import RefactoringTool, get_fixers_from_package
    except ModuleNotFoundError as e:
        raise SystemExit(
            "MAPS.ME fork oracle needs Python's lib2to3. "
            "Run this check with Python 3.9, as configured in CI."
        ) from e

    source_root = checkout / "src"
    files = [str(path) for path in source_root.rglob("*.py")]
    tool = RefactoringTool(get_fixers_from_package("lib2to3.fixes"))
    tool.refactor(files, write=True)

    libkomwm = source_root / "libkomwm.py"
    libkomwm.write_text(
        libkomwm.read_text()
        .replace("from drules_struct_pb2 import *", "from functools import cmp_to_key\nfrom drules_struct_pb2 import *")
        .replace("viskeys.sort(cmprepl)", "viskeys.sort(key=cmp_to_key(cmprepl))")
        .replace("len(oldoffset) / 4", "len(oldoffset) // 4")
        .replace("len(offset) / 4", "len(offset) // 4")
    )
    style_chooser = source_root / "mapcss" / "StyleChooser.py"
    style_chooser.write_text(
        style_chooser.read_text().replace(
            "self.ruleChains[-1].runtime_conditions.sort()",
            "self.ruleChains[-1].runtime_conditions.sort(key=repr)",
        )
    )
    eval_py = source_root / "mapcss" / "Eval.py"
    eval_py.write_text(
        eval_py.read_text().replace(
            '"tag": lambda x: max([tags.add(x), 0]),',
            '"tag": lambda x: (tags.add(x) or 0),',
        )
    )
    webcolors = source_root / "mapcss" / "webcolors" / "webcolors.py"
    webcolors.write_text(
        webcolors.read_text().replace(
            "return '#%02x%02x%02x' % rgb_triplet",
            "return '#%02x%02x%02x' % tuple(int(round(v)) for v in rgb_triplet)",
        )
    )


def run_mapsme_generator(script, data_path, output_path, stylesheet, extra_args=(), env=None):
    run([
        sys.executable,
        str(script),
        "-s", str(data_path / stylesheet),
        "-o", str(output_path),
        "-t", "21",
        *extra_args,
    ], env=env)


def normalize_mapsme_oracle_input(data_path):
    """Keep MAPS.ME oracle comparison focused on intentional legacy behavior.

    The pinned MAPS.ME fork parser mis-parses declarations like
    `text:"addr:housename"` as a key named `text:"addr`.  Modern Kothic should
    parse that as the `text` property with a colon-bearing value.  Normalize the
    temporary oracle input so the old fork produces the same semantic style
    before comparing all other MAPS.ME compatibility details.
    """
    for stylesheet in (data_path / "styles").rglob("*.mapcss"):
        stylesheet.write_text(
            stylesheet.read_text().replace('text:"addr:housename"', 'text: "addr:housename"')
        )


def check_organicmaps(workspace):
    checkout = workspace / "organicmaps"
    output = workspace / "organicmaps-generated"
    clone_sparse(
        ORGANICMAPS_REPO,
        ORGANICMAPS_COMMIT,
        checkout,
        (*STYLE_DATA_PATHS, *ORGANICMAPS_BASELINE_PATHS),
    )

    run([
        sys.executable,
        str(FULL_DRULES_GEN),
        "-d", str(checkout / "data"),
        "-o", str(output),
        "--compatibility-profile", "organicmaps",
        "--name-prefix", "drules_proto_",
    ])

    compare_files(output, checkout / "data", (".bin",), "drules_proto_", "drules_proto_")


def check_comaps(workspace):
    data_checkout = workspace / "comaps"
    fork_checkout = workspace / "comaps-kothic"
    oracle_data = workspace / "comaps-oracle-data"
    oracle_output = workspace / "comaps-oracle-output"
    generated_data = workspace / "comaps-generated-data"
    generated_output = workspace / "comaps-generated-output"

    clone_sparse(COMAPS_REPO, COMAPS_COMMIT, data_checkout, STYLE_DATA_PATHS)
    clone_full(COMAPS_KOTHIC_REPO, COMAPS_KOTHIC_COMMIT, fork_checkout)

    shutil.copytree(data_checkout / "data", oracle_data)
    shutil.copytree(data_checkout / "data", generated_data)
    oracle_output.mkdir()
    generated_output.mkdir()

    run([
        sys.executable,
        str(fork_checkout / "integration-tests" / "full_drules_gen.py"),
        "-d", str(oracle_data),
        "-o", str(oracle_output),
        "--txt",
    ])
    run([
        sys.executable,
        str(FULL_DRULES_GEN),
        "-d", str(generated_data),
        "-o", str(generated_output),
        "--compatibility-profile", "comaps",
        "--txt",
    ])

    compare_files(generated_output, oracle_output, (".bin", ".txt"))


def check_mapsme(workspace):
    data_checkout = workspace / "mapsme-omim"
    fork_checkout = workspace / "mapsme-kothic"
    oracle_data = workspace / "mapsme-oracle-data"
    generated_data = workspace / "mapsme-generated-data"

    clone_sparse(MAPSME_OMIM_REPO, MAPSME_OMIM_COMMIT, data_checkout, MAPSME_STYLE_DATA_PATHS)
    clone_full(MAPSME_KOTHIC_REPO, MAPSME_KOTHIC_COMMIT, fork_checkout)
    port_python2_fork_to_python3(fork_checkout)

    shutil.copytree(data_checkout / "data", oracle_data)
    shutil.copytree(data_checkout / "data", generated_data)
    normalize_mapsme_oracle_input(oracle_data)
    oracle_env = dict(os.environ, PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="python")

    for output_name, stylesheet in MAPSME_STYLES:
        run_mapsme_generator(
            fork_checkout / "src" / "libkomwm.py",
            oracle_data,
            oracle_data / output_name,
            stylesheet,
            env=oracle_env,
        )
        run_mapsme_generator(
            REPO_ROOT / "src" / "libkomwm.py",
            generated_data,
            generated_data / output_name,
            stylesheet,
            ("--compatibility-profile", "mapsme"),
        )

    compare_normalized_drules(
        generated_data,
        oracle_data,
        tuple(output_name for output_name, _stylesheet in MAPSME_STYLES),
    )


def main():
    parser = argparse.ArgumentParser(description="Compare generated drules with fork baselines.")
    parser.add_argument(
        "--project",
        choices=("organicmaps", "comaps", "mapsme"),
        action="append",
        help="Project to check. Defaults to all supported projects.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary workspace for debugging.",
    )
    args = parser.parse_args()

    projects = args.project or ("organicmaps", "comaps", "mapsme")
    workspace = Path(tempfile.mkdtemp(prefix="kothic-fork-drules-"))
    print(f"workspace: {workspace}", flush=True)
    try:
        if "organicmaps" in projects:
            check_organicmaps(workspace)
        if "comaps" in projects:
            check_comaps(workspace)
        if "mapsme" in projects:
            check_mapsme(workspace)
    finally:
        if args.keep_temp:
            print(f"kept workspace: {workspace}", flush=True)
        else:
            shutil.rmtree(workspace)


if __name__ == "__main__":
    main()
