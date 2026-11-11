"""Configure retained inputs without editing the byte-bound legacy programs.

Use --archive-root or SCLAW_BENCH_ARCHIVE. Repository source and corpora still
resolve in this checkout; retained reviews and old work directories resolve in
the archive. Outputs must be outside the read-only archive.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArchiveInputRoot(os.PathLike):
    def __init__(self, repository, archive):
        self.repository = Path(repository).resolve()
        self.archive = Path(archive).resolve()

    def __fspath__(self):
        return str(self.repository)

    def __str__(self):
        return str(self.repository)

    def __truediv__(self, relative):
        path = Path(relative)
        parts = path.parts
        retained = parts[:3] == ('docs', 'implementation', 'reviews')
        retained = retained or parts[:1] in [('.bench-work',), ('.worktrees',)]
        return (self.archive if retained else self.repository) / path


def load(relative, archive):
    path = ROOT / relative
    name = '_legacy_archive_' + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous_path = list(sys.path)
    try:
        sys.path[:0] = [str(path.parent), str(ROOT)]
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous_path
    module.ROOT = ArchiveInputRoot(ROOT, archive)
    return module


def writable(path, archive):
    if path.resolve().is_relative_to(archive.resolve()):
        raise ValueError('Outputs must be outside the read-only archive')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root', type=Path,
                        default=Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)))
    commands = parser.add_subparsers(dest='command', required=True)
    pilot = commands.add_parser('pilot30-audit')
    pilot.add_argument('--edition', type=Path, required=True)
    pilot.add_argument('--tools', type=Path, required=True)
    pilot.add_argument('--output', type=Path, required=True)
    archive = commands.add_parser('pilot30-archive')
    archive.add_argument('--review', type=Path, required=True)
    v2 = commands.add_parser('v2-audit')
    v2.add_argument('--edition', type=Path, required=True)
    v2.add_argument('--output', type=Path, required=True)
    v2.add_argument('--source-registry', type=Path,
                    default=ROOT / 'scripts/research300_v2/source_registry.json')
    v2.add_argument('--manual-geometry', type=Path)
    v2.add_argument('--schema-root', type=Path)
    v2.add_argument('--schema-python', type=Path)
    tests = commands.add_parser('pkpm-precision-tests')
    tests.add_argument('tests', nargs='*')
    args = parser.parse_args(argv)
    retained = args.archive_root.expanduser().resolve()
    if args.command == 'pkpm-precision-tests':
        module = load('scripts/research300/commercial/test_pkpm_precision.py', retained)
        module.CapturedEvidence.EVIDENCE = retained / (
            'docs/implementation/reviews/commercial-calibration-20261015/'
            'native-cases/pkpm/final-native-candidates')
        suite = unittest.defaultTestLoader.loadTestsFromNames(args.tests, module) if args.tests else (
            unittest.defaultTestLoader.loadTestsFromModule(module))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if args.command == 'pilot30-archive':
        module = load('scripts/pilot30/archive.py', retained)
        print(json.dumps(module.archive(writable(args.review.resolve(), retained))))
        return 0
    writable(args.output, retained)
    if args.command == 'pilot30-audit':
        module = load('scripts/pilot30/audit.py', retained)
        result = module.audit(args.edition.resolve(), args.tools.resolve())
    else:
        module = load('scripts/research300_v2/audit.py', retained)
        result = module.audit(args.edition.resolve(), args.source_registry.resolve(),
                              args.manual_geometry, args.schema_root, args.schema_python)
    with args.output.open('x') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps({key: value for key, value in result.items()
                      if not isinstance(value, (list, dict))}, ensure_ascii=False))
    return 0 if result['allPassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
