"""Regenerate all MM-B files in isolation and compare their exact raw bytes.

Run with the authoring Python environment, optionally adding ``--output receipt.json``.
Original cases are only read; regeneration runs in a fresh interpreter and a temporary
directory. Every authored case file is included, including evaluator-only author-review.json.
Only explicitly named, separately generated reference/review artifacts are excluded.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = Path("corpora/research-300/cases")
CASE_IDS = tuple(f"MM-{number:03}" for number in range(51, 101))
MODULES = (
    "mm_b_51_60",
    "mm_b_61_70",
    "mm_b_71_78_99_100",
    "mm_b_79_88",
    "mm_b_89_98",
)

# Import and build all source specifications before changing the exporter root.
# -B keeps even Python bytecode writes out of the original authoring tree.
REGENERATE = """
import importlib
import json
from pathlib import Path
import platform
import sys
import PIL

script_dir, destination, module_names = sys.argv[1:]
sys.path.insert(0, script_dir)
common = importlib.import_module('mm_b_common')
modules = [importlib.import_module(name) for name in json.loads(module_names)]
specs = [spec for module in modules for spec in module.build_specs()]
ids = [spec['id'] for spec in specs]
expected = [f'MM-{number:03}' for number in range(51, 101)]
if len(ids) != len(expected) or sorted(ids) != expected:
    raise RuntimeError('Generators must emit each MM-051..100 exactly once')
common.ROOT = Path(destination)
common.export_specs(specs)
(common.ROOT / 'generation-receipt.json').write_text(json.dumps({
    'caseIds': sorted(ids),
    'pythonVersion': platform.python_version(),
    'pillowVersion': PIL.__version__,
}, indent=2) + '\\n', encoding='utf-8')
"""


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ordered(values):
    return sorted(values, key=lambda value: value.encode("utf-8"))


GENERATED_EVIDENCE = {
    'independent-reference.json', 'native-opensees-reference.json',
    'independent-reference-matrix-diagnostic.json',
    'native-input-receipt.json', 'native-solver-receipt.json',
    'native-raw-responses.json', 'native-checks.json',
    'native-independent-review.json', 'reference-provenance.json', 'acceptance.json',
}


def is_generated_evidence(relative):
    if len(relative.parts) > 1 and relative.parts[0] == 'native-commercial':
        return True
    if len(relative.parts) != 1:
        return False
    import re
    return relative.name in GENERATED_EVIDENCE or bool(re.fullmatch(
        r'native-run-[1-9][0-9]*-(?:case|combination)-[A-Za-z0-9_+.-]+\.json', relative.name
    ))


def inventory(cases_root):
    """Hash the complete owned file set, rejecting aliases outside the tree."""
    result = {}
    for case_id in CASE_IDS:
        case_dir = cases_root / case_id
        if case_dir.is_symlink() or not case_dir.is_dir():
            raise ValueError(f"Missing or symlinked case directory: {case_dir}")
        for path in sorted(case_dir.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Case files must not be symlinks: {path}")
            if path.is_file():
                if not is_generated_evidence(path.relative_to(case_dir)):
                    result[path.relative_to(cases_root).as_posix()] = sha256(path)
            elif not path.is_dir():
                raise ValueError(f"Unsupported case entry: {path}")
    return {path: result[path] for path in ordered(result)}


def compare(original, regenerated):
    return {
        "added": ordered(regenerated.keys() - original.keys()),
        "missing": ordered(original.keys() - regenerated.keys()),
        "changed": [
            {
                "path": path,
                "originalSha256": original[path],
                "regeneratedSha256": regenerated[path],
            }
            for path in ordered(original.keys() & regenerated.keys())
            if original[path] != regenerated[path]
        ],
    }


def manifest_sha256(files):
    # Canonical inventory digest binds both paths and raw byte hashes.
    payload = {
        "schemaVersion": 1,
        "files": [{"path": path, "sha256": files[path]} for path in ordered(files)],
    }
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def dependencies():
    scripts = ROOT / "scripts/research300"
    generators = [scripts / f"{name}.py" for name in (*MODULES, "mm_b_common")]
    generators += [scripts / "commercial/conventions.py", scripts / "reference_cli.py",
                   scripts / "reference_io.py"]
    generators += [ROOT / "scripts/representative-models.py", Path(__file__).resolve()]
    source_dir = ROOT / "planning/sources"
    if not source_dir.exists():
        source_dir = Path("/mnt/nas/qsz/01research/02structureclaw-bench/planning/sources")
    sources = [ROOT / "planning/capability-coverage-300.json"]
    sources += [source_dir / name for name in (
        "all-tasks-engines-v2.json", "all-models-engines-v2.json"
    )]
    fonts = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    cjk = Path("/home/codex_xjk/.local/share/fonts/NotoSansCJKsc-Regular.otf")
    if cjk.exists():
        fonts.append(cjk)
    return {"generators": generators, "sources": sources, "fonts": fonts}


def dependency_hashes(paths):
    return {
        kind: {str(path): sha256(path) for path in files}
        for kind, files in paths.items()
    }


def check(output=None):
    paths = dependencies()
    if output is not None:
        output = output.resolve()
        protected = {path.resolve() for files in paths.values() for path in files}
        if output in protected or (ROOT / CASE_PATH).resolve() in output.parents:
            raise ValueError("The receipt must not overwrite case files or authoring inputs")
    original = inventory(ROOT / CASE_PATH)
    before = dependency_hashes(paths)
    with TemporaryDirectory(prefix="mm-b-reproducibility-") as directory:
        destination = Path(directory)
        subprocess.run([
            sys.executable, "-B", "-c", REGENERATE,
            str(ROOT / "scripts/research300"), str(destination), json.dumps(MODULES),
        ], check=True)
        generated = inventory(destination / CASE_PATH)
        generation = json.loads((destination / "generation-receipt.json").read_text())
    differences = compare(original, generated)
    original_changes = compare(original, inventory(ROOT / CASE_PATH))
    after = dependency_hashes(paths)
    inputs_unchanged = before == after
    success = (
        not any(differences.values())
        and not any(original_changes.values())
        and inputs_unchanged
    )
    receipt = {
        "schemaVersion": 1,
        "status": "pass" if success else "fail",
        "scope": "Complete MM-051..100 authored files, including author-review.json; explicit generated evidence excluded",
        "originalRoot": str(ROOT),
        "caseCount": len(CASE_IDS),
        "originalFileCount": len(original),
        "regeneratedFileCount": len(generated),
        "matchedFileCount": sum(original.get(path) == digest for path, digest in generated.items()),
        "originalManifestSha256": manifest_sha256(original),
        "regeneratedManifestSha256": manifest_sha256(generated),
        "differences": differences,
        "originalChangesDuringCheck": original_changes,
        "authoringInputsUnchanged": inputs_unchanged,
        "dependenciesBefore": before,
        "dependenciesAfter": after,
        "generation": generation,
        "originalFiles": original,
        "regeneratedFiles": generated,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{receipt['status'].upper()}: {len(CASE_IDS)} cases; "
          f"{receipt['matchedFileCount']}/{len(original)} files reproduce byte-for-byte; "
          f"{len(differences['added'])} added, {len(differences['missing'])} missing, "
          f"{len(differences['changed'])} changed")
    if any(differences.values()):
        print(json.dumps(differences, ensure_ascii=False, indent=2))
    if any(original_changes.values()):
        print("FAIL: Original case files changed during verification", file=sys.stderr)
    if not inputs_unchanged:
        print("FAIL: Authoring inputs changed during verification", file=sys.stderr)
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a detailed JSON verification receipt")
    args = parser.parse_args()
    try:
        return check(args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
