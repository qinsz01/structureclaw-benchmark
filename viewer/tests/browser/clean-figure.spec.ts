import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('normal figure downloads preserve the plotted values without audit metadata', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
  await page.goto('/#/case/MM-001?turn=t1&tab=reference');
  await page.getByRole('checkbox', { name: 'Discrete NODE deformation' }).check();
  for (const format of ['SVG', 'PNG']) {
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name: `Export response ${format}`, exact: true }).click();
    const bytes = fs.readFileSync((await (await pending).path())!);
    let text = '';
    if (format === 'SVG') {
      text = await page.evaluate(
        (raw) =>
          new DOMParser().parseFromString(raw, 'image/svg+xml').querySelector('metadata')!
            .textContent!,
        bytes.toString('utf8'),
      );
    } else {
      for (let offset = 8; offset < bytes.length;) {
        const length = bytes.readUInt32BE(offset);
        if (bytes.toString('ascii', offset + 4, offset + 8) === 'iTXt')
          text = bytes
            .subarray(offset + 8 + 'research300'.length + 5, offset + 8 + length)
            .toString('utf8');
        offset += length + 12;
      }
    }
    const value = JSON.parse(text);
    expect(value.caseId).toBe('MM-001');
    expect(value.engine).toBe('OpenSees');
    expect(value.quantities.length).toBeGreaterThan(0);
    expect(value.deformation.nodes.length).toBeGreaterThan(0);
    expect(text).not.toMatch(
      /sha256|[a-f0-9]{64}|sourceHash|referenceSource|receipt|tolerance|rawTrace|corpora\/research-300/i,
    );
  }
});
