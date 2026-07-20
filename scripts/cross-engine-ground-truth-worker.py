from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one cross-engine validation case")
    parser.add_argument("--sclaw-root", required=True)
    parser.add_argument("--engine", choices=("opensees", "pkpm", "yjk"), required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def configure_imports(root: Path, engine: str) -> None:
    paths = [
        root / "backend" / "src" / "agent-skills" / "analysis" / f"{engine}-static",
        root / "backend" / "src" / "agent-skills" / "analysis" / "runtime",
        root / "backend" / "src" / "skill-shared" / "python",
        root / ".runtime" / "pkpm-api" / "APIPythonTest_python312",
    ]
    for path in reversed(paths):
        if path.is_dir():
            sys.path.insert(0, str(path))


def file_identity(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "file": path.name,
        "parent": path.parent.name,
        "sha256": digest.hexdigest(),
    }


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def open_sees_identity() -> dict[str, Any]:
    import openseespy.opensees as ops

    runtime_package = "openseespywin" if platform.system() == "Windows" else "openseespylinux"
    return {
        "name": "OpenSeesPy",
        "version": str(ops.version()),
        "packageVersion": package_version("openseespy"),
        "runtimePackage": runtime_package,
        "runtimePackageVersion": package_version(runtime_package),
    }


def pkpm_identity() -> dict[str, Any]:
    import APIPyInterface

    return {
        "name": "PKPM/SATWE",
        "configuredVersion": Path(os.environ["PKPM_CYCLE_PATH"]).parents[1].name,
        "cycle": file_identity(os.environ.get("PKPM_CYCLE_PATH")),
        "api": file_identity(getattr(APIPyInterface, "__file__", None)),
        "apiPackageVersion": package_version("pkpm-api"),
    }


def yjk_identity() -> dict[str, Any]:
    root_value = os.environ.get("YJKS_ROOT") or os.environ.get("YJK_PATH")
    root = Path(root_value) if root_value else None
    executable = root / "yjks.exe" if root else None
    return {
        "name": "YJK",
        "configuredVersion": os.environ.get("YJK_VERSION", "8.0.0"),
        "installation": root.name if root else None,
        "executable": file_identity(str(executable) if executable else None),
    }


def run_open_sees(model_dict: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    from opensees_static_analysis import OpenSeesStaticExecutor
    from runtime import OpenSeesStaticAnalyzer
    from structure_protocol.structure_model_v2 import StructureModelV2

    model = StructureModelV2.model_validate(model_dict)
    analyzer = OpenSeesStaticAnalyzer(model)
    result = OpenSeesStaticExecutor(analyzer).run(parameters)
    if result.get("status") != "success":
        raise RuntimeError(f"OpenSees returned status {result.get('status')!r}")
    return result


def run_commercial(model_dict: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    from runtime import run_analysis

    result = run_analysis(model_dict, parameters)
    if result.get("status") != "success":
        raise RuntimeError(f"Commercial engine returned status {result.get('status')!r}")
    return result


def main() -> None:
    args = parse_args()
    root = Path(args.sclaw_root).resolve()
    configure_imports(root, args.engine)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    model = payload["model"]
    parameters = payload.get("parameters", {})
    if args.engine == "opensees":
        result = run_open_sees(model, parameters)
        identity = open_sees_identity()
    elif args.engine == "pkpm":
        result = run_commercial(model, parameters)
        identity = pkpm_identity()
    else:
        result = run_commercial(model, parameters)
        identity = yjk_identity()
    Path(args.output).write_text(
        json.dumps({"identity": identity, "result": result}, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
