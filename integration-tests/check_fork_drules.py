#!/usr/bin/env python3

import argparse
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FULL_DRULES_GEN = REPO_ROOT / "integration-tests" / "full_drules_gen.py"

ORGANICMAPS_REPO = "https://github.com/organicmaps/organicmaps.git"
ORGANICMAPS_COMMIT = "b3a04bee373ab723e661523166d8d37e45c9ed2e"

COMAPS_REPO = "https://codeberg.org/comaps/comaps.git"
COMAPS_COMMIT = "19e486669105dc419e3357aee62652f2771141ed"
COMAPS_KOTHIC_REPO = "https://codeberg.org/comaps/kothic.git"
COMAPS_KOTHIC_COMMIT = "1cba3a0347b21c1b20d36da0f4a3245bc27e0f38"

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

ORGANICMAPS_BASELINE_PATHS = tuple(
    f"data/drules_proto_{style_name}.bin"
    for style_name in STYLE_NAMES
)


def run(args, cwd=None):
    print("+", " ".join(str(arg) for arg in args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


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


def main():
    parser = argparse.ArgumentParser(description="Compare generated drules with fork baselines.")
    parser.add_argument(
        "--project",
        choices=("organicmaps", "comaps"),
        action="append",
        help="Project to check. Defaults to all supported projects.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary workspace for debugging.",
    )
    args = parser.parse_args()

    projects = args.project or ("organicmaps", "comaps")
    workspace = Path(tempfile.mkdtemp(prefix="kothic-fork-drules-"))
    print(f"workspace: {workspace}", flush=True)
    try:
        if "organicmaps" in projects:
            check_organicmaps(workspace)
        if "comaps" in projects:
            check_comaps(workspace)
    finally:
        if args.keep_temp:
            print(f"kept workspace: {workspace}", flush=True)
        else:
            shutil.rmtree(workspace)


if __name__ == "__main__":
    main()
