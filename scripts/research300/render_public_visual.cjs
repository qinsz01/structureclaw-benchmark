'use strict';
// Local, deterministic raster boundary. No paths, external resources or metadata.
const sharp = require('sharp');
const fs = require('node:fs');
const PIPELINE = 'visual-v2-sharp-rgb-72dpi-png9-v1';

function publicPNG(raw) {
  const pieces = [raw.subarray(0, 8)];
  for (let offset = 8; offset < raw.length;) {
    const length = raw.readUInt32BE(offset);
    const kind = raw.toString('ascii', offset + 4, offset + 8);
    if (['IHDR', 'IDAT', 'IEND'].includes(kind)) pieces.push(raw.subarray(offset, offset + length + 12));
    offset += length + 12;
  }
  return Buffer.concat(pieces);
}

(async () => {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  const pages = {};
  // Sequential rasterization bounds memory on the large spatial cases.
  sharp.concurrency(1);
  for (const [name, svg] of Object.entries(input.pages || {})) {
    if (/<!ENTITY|<!DOCTYPE|<image\b|href\s*=/i.test(svg)) throw new Error('External SVG content is forbidden');
    const png = await sharp(Buffer.from(svg), { density: 72, limitInputPixels: 32e6 })
      .flatten({ background: '#ffffff' }).removeAlpha().toColourspace('srgb')
      .png({ compressionLevel: 9, adaptiveFiltering: false, palette: false, effort: 10 }).toBuffer();
    pages[name] = publicPNG(png).toString('base64');
  }
  process.stdout.write(JSON.stringify({ renderer: { pipeline: PIPELINE, versions: sharp.versions }, pages }));
})().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1; });
