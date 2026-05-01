#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def integration_python_files():
    return sorted(str(path.relative_to(REPO_ROOT)) for path in (REPO_ROOT / "integration-tests").glob("*.py"))


CHECKS = (
    (
        "Check Python 3 runtime blockers",
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select=E9,F63,F7,F82",
            "--exclude=src/drules_struct_pb2.py",
            "--target-version=py39",
        ],
    ),
    (
        "Lint maintained Python surfaces",
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "src",
            "tests",
            *integration_python_files(),
            "--exclude=src/drules_struct_pb2.py",
            "--target-version=py39",
        ],
    ),
    (
        "Compile Python sources",
        [sys.executable, "-m", "compileall", "-q", "src", "tests", "integration-tests"],
    ),
    (
        "Run unit-tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
    ),
    (
        "Check fork drules compatibility",
        [sys.executable, "integration-tests/check_fork_drules.py"],
    ),
)


def require_ci_python_runtime():
    try:
        import lib2to3.refactor  # noqa: F401
    except ModuleNotFoundError as e:
        raise SystemExit(
            "Full CI checks require Python with lib2to3 because the MAPS.ME "
            "oracle is ported from Python 2 during integration tests. "
            "Run this with Python 3.9, matching GitHub Actions."
        ) from e


def run_check(name, command):
    print(f"\n==> {name}", flush=True)
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main():
    require_ci_python_runtime()
    for name, command in CHECKS:
        run_check(name, command)


if __name__ == "__main__":
    main()
