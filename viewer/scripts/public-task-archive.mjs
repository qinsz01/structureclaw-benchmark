import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import inputExport from '../../scripts/export-research300-inputs.cjs';

/** Package only the standalone public tasks, never the reference viewer data. */
export function writePublicTaskArchive(root, outputDirectory) {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'research300-tasks-'));
  try {
    const tasks = path.join(temporary, 'tasks');
    inputExport.exportResearch300Inputs({ root, output: tasks });
    const archive = path.join(temporary, 'benchmark-inputs.zip');
    const result = spawnSync(
      'python3',
      [
        '-c',
        [
          'from pathlib import Path',
          'import sys, zipfile',
          'source, target = Path(sys.argv[1]), Path(sys.argv[2])',
          'with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:',
          ' for file in sorted(source.rglob("*")):',
          '  if file.is_file(): output.write(file, file.relative_to(source).as_posix())',
        ].join('\n'),
        tasks,
        archive,
      ],
      { encoding: 'utf8', timeout: 60000 },
    );
    if (result.error || result.status !== 0)
      throw new Error(`Public task archive failed: ${result.error?.message || result.stderr}`);
    fs.mkdirSync(outputDirectory, { recursive: true });
    const staging = fs.mkdtempSync(path.join(outputDirectory, '.benchmark-inputs-'));
    try {
      const ready = path.join(staging, 'benchmark-inputs.zip');
      fs.copyFileSync(archive, ready);
      fs.renameSync(ready, path.join(outputDirectory, 'benchmark-inputs.zip'));
    } finally {
      fs.rmSync(staging, { recursive: true, force: true });
    }
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}
