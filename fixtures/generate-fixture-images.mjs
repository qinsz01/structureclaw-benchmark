#!/usr/bin/env node

// Generates structural diagram PNG fixtures for multimodal benchmark scenarios.
// Usage: node tests/llm-benchmark/fixtures/generate-fixture-images.mjs

import sharp from "sharp";
import { mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = __dirname;

const W = 640;
const H = 400;

function svg(body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <rect width="${W}" height="${H}" fill="#fff"/>
    <style>
      text { font-family: 'Courier New', monospace; fill: #222; }
      .dim { font-size: 16px; fill: #1a65ac; font-weight: bold; }
      .label { font-size: 13px; fill: #555; }
      .member { stroke: #333; stroke-width: 2.5; fill: none; stroke-linecap: round; }
      .support { fill: #666; stroke: #333; stroke-width: 1.5; }
      .load-arrow { stroke: #c0392b; stroke-width: 1.8; fill: none; marker-end: url(#arrowR); }
      .reaction { stroke: #27ae60; stroke-width: 1.8; fill: none; }
    </style>
    <defs>
      <marker id="arrowR" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <path d="M0,0 L8,3 L0,6 Z" fill="#c0392b"/>
      </marker>
      <marker id="arrowD" markerWidth="6" markerHeight="8" refX="3" refY="8" orient="auto">
        <path d="M0,0 L6,0 L3,8 Z" fill="#c0392b"/>
      </marker>
    </defs>
    ${body}
  </svg>`;
}

function triangleSupport(cx, cy, size = 14) {
  const pts = `${cx},${cy} ${cx - size},${cy + size * 1.2} ${cx + size},${cy + size * 1.2}`;
  const baseY = cy + size * 1.2;
  return `<polygon points="${pts}" class="support"/>
    <line x1="${cx - size - 4}" y1="${baseY + 4}" x2="${cx + size + 4}" y2="${baseY + 4}" stroke="#666" stroke-width="2"/>
    <line x1="${cx - size - 2}" y1="${baseY + 8}" x2="${cx + size + 2}" y2="${baseY + 8}" stroke="#999" stroke-width="1"/>`;
}

function rollerSupport(cx, cy, size = 14) {
  const pts = `${cx},${cy} ${cx - size},${cy + size * 1.2} ${cx + size},${cy + size * 1.2}`;
  const baseY = cy + size * 1.2;
  return `<polygon points="${pts}" class="support"/>
    <circle cx="${cx - size * 0.55}" cy="${baseY + 5}" r="3" fill="#fff" stroke="#666" stroke-width="1.5"/>
    <circle cx="${cx + size * 0.55}" cy="${baseY + 5}" r="3" fill="#fff" stroke="#666" stroke-width="1.5"/>
    <line x1="${cx - size - 4}" y1="${baseY + 11}" x2="${cx + size + 4}" y2="${baseY + 11}" stroke="#666" stroke-width="2"/>`;
}

// 1. beam-sketch.png — simply supported beam with UDL
const beamSketch = svg(`
  <!-- beam line -->
  <line x1="120" y1="180" x2="520" y2="180" class="member"/>
  <circle cx="320" cy="180" r="4" fill="#1a65ac"/>
  <!-- supports -->
  ${triangleSupport(120, 180)}
  ${rollerSupport(520, 180)}
  <!-- UDL arrows -->
  ${Array.from({ length: 9 }, (_, i) => {
    const x = 160 + i * 40;
    return `<line x1="${x}" y1="100" x2="${x}" y2="175" class="load-arrow"/>`;
  }).join("\n  ")}
  <line x1="160" y1="100" x2="480" y2="100" stroke="#c0392b" stroke-width="1.5"/>
  <text x="320" y="90" text-anchor="middle" class="dim">LC1: q = 20 kN/m</text>
  <!-- complete consecutive dimension chain -->
  ${[120, 320, 520].map(x => `<line x1="${x}" y1="180" x2="${x}" y2="270" stroke="#90caf9" stroke-width="1" stroke-dasharray="4,3"/>`).join("\n  ")}
  <line x1="120" y1="260" x2="520" y2="260" stroke="#1a65ac" stroke-width="1"/>
  <text x="220" y="285" text-anchor="middle" class="dim">3m</text>
  <text x="420" y="285" text-anchor="middle" class="dim">3m</text>
  <!-- labels -->
  <text x="120" y="230" text-anchor="middle" class="label">A</text>
  <text x="520" y="230" text-anchor="middle" class="label">B</text>
`);

// 2. frame-sketch.png — 2-story 1-bay frame
const frameSketch = svg(`
  <!-- columns and beams -->
  <rect x="160" y="100" width="4" height="220" fill="#333" rx="1"/>
  <rect x="436" y="100" width="4" height="220" fill="#333" rx="1"/>
  <line x1="160" y1="210" x2="440" y2="210" class="member"/>
  <line x1="160" y1="100" x2="440" y2="100" class="member"/>
  <!-- fixed supports -->
  <line x1="145" y1="322" x2="175" y2="322" stroke="#333" stroke-width="3"/>
  <line x1="425" y1="322" x2="455" y2="322" stroke="#333" stroke-width="3"/>
  <line x1="160" y1="320" x2="160" y2="322" stroke="#333" stroke-width="2.5"/>
  <line x1="440" y1="320" x2="440" y2="322" stroke="#333" stroke-width="2.5"/>
  <!-- floor area load arrows -->
  ${[200, 280, 360].map(x => `<line x1="${x}" y1="72" x2="${x}" y2="95" class="load-arrow"/>`).join("\n  ")}
  <text x="300" y="55" text-anchor="middle" class="dim">D: p = 10 kN/m2; bt = 6m</text>
  ${[200, 280, 360].map(x => `<line x1="${x}" y1="182" x2="${x}" y2="205" class="load-arrow"/>`).join("\n  ")}
  <text x="300" y="168" text-anchor="middle" class="dim">D: p = 10 kN/m2; bt = 6m</text>
  <!-- dimensions -->
  <text x="140" y="160" text-anchor="end" class="dim">3.6m</text>
  <text x="140" y="270" text-anchor="end" class="dim">3.6m</text>
  <line x1="152" y1="100" x2="152" y2="210" stroke="#1a65ac" stroke-width="1" stroke-dasharray="3,3"/>
  <line x1="152" y1="210" x2="152" y2="320" stroke="#1a65ac" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="300" y="340" text-anchor="middle" class="dim">6m</text>
  <line x1="160" y1="332" x2="440" y2="332" stroke="#1a65ac" stroke-width="1" stroke-dasharray="3,3"/>
`);

// 3. truss-diagram.png — triangular truss
const trussDiagram = svg(`
  <!-- bottom chord -->
  <line x1="100" y1="260" x2="540" y2="260" class="member"/>
  <!-- top chord -->
  <line x1="100" y1="260" x2="320" y2="100" class="member"/>
  <line x1="320" y1="100" x2="540" y2="260" class="member"/>
  <!-- web members -->
  <line x1="210" y1="180" x2="320" y2="260" class="member"/>
  <line x1="210" y1="180" x2="430" y2="180" class="member"/>
  <line x1="320" y1="100" x2="320" y2="260" class="member" stroke-dasharray="6,3"/>
  <line x1="430" y1="180" x2="320" y2="260" class="member"/>
  <!-- supports -->
  ${triangleSupport(100, 260)}
  <circle cx="540" cy="260" r="5" fill="#666" stroke="#333" stroke-width="1.5"/>
  <line x1="525" y1="268" x2="555" y2="268" stroke="#666" stroke-width="2"/>
  <line x1="530" y1="274" x2="550" y2="274" stroke="#999" stroke-width="1"/>
  <!-- node loads -->
  ${[210, 320, 430].map(x => `<line x1="${x}" y1="70" x2="${x}" y2="${x === 320 ? 95 : 175}" class="load-arrow" style="stroke-width:3"/><rect x="${x - 53}" y="35" width="106" height="24" fill="#fff" stroke="#c0392b" stroke-width="1" rx="3"/><text x="${x}" y="52" text-anchor="middle" font-size="11" fill="#c0392b" font-weight="bold">LC1: P = 20 kN</text>`).join("\n  ")}
  <!-- joint markers and explicit elevations -->
  ${[[100,260],[210,180],[320,100],[320,260],[430,180],[540,260]].map(([x,y]) => `<circle cx="${x}" cy="${y}" r="4" fill="#1a65ac"/>`).join("\n  ")}
  <text x="218" y="205" font-size="13" fill="#1a65ac" font-weight="bold" paint-order="stroke" stroke="#fff" stroke-width="4">z=1.5m</text>
  <text x="330" y="120" font-size="13" fill="#1a65ac" font-weight="bold" paint-order="stroke" stroke="#fff" stroke-width="4">z=3m</text>
  <text x="438" y="205" font-size="13" fill="#1a65ac" font-weight="bold" paint-order="stroke" stroke="#fff" stroke-width="4">z=1.5m</text>
  <!-- complete consecutive dimension chain -->
  ${[100, 210, 320, 430, 540].map(x => `<line x1="${x}" y1="260" x2="${x}" y2="335" stroke="#90caf9" stroke-width="1" stroke-dasharray="3,3"/>`).join("\n  ")}
  <line x1="100" y1="325" x2="540" y2="325" stroke="#1a65ac" stroke-width="1"/>
  ${[155, 265, 375, 485].map(x => `<text x="${x}" y="350" text-anchor="middle" class="dim">3m</text>`).join("\n  ")}
  <text x="80" y="180" text-anchor="end" class="dim">3m</text>
  <line x1="88" y1="100" x2="88" y2="260" stroke="#1a65ac" stroke-width="1" stroke-dasharray="3,3"/>
`);

// 4. portal-frame-diagram.png — portal frame
const portalFrame = svg(`
  <!-- left column -->
  <line x1="120" y1="310" x2="120" y2="120" class="member"/>
  <!-- right column -->
  <line x1="520" y1="310" x2="520" y2="120" class="member"/>
  <!-- roof beam -->
  <line x1="120" y1="120" x2="520" y2="120" class="member"/>
  <!-- fixed supports -->
  <line x1="105" y1="312" x2="135" y2="312" stroke="#333" stroke-width="3"/>
  <line x1="505" y1="312" x2="535" y2="312" stroke="#333" stroke-width="3"/>
  <!-- UDL on roof -->
  ${Array.from({ length: 9 }, (_, i) => {
    const x = 150 + i * 42;
    const yTop = 112;
    return `<line x1="${x}" y1="${yTop - 25}" x2="${x}" y2="${yTop - 3}" class="load-arrow"/>`;
  }).join("\n  ")}
  <text x="320" y="70" text-anchor="middle" class="dim">LC1: q = 6 kN/m</text>
  <!-- dimensions -->
  <text x="320" y="340" text-anchor="middle" class="dim">18m</text>
  <text x="95" y="215" text-anchor="end" class="dim">7m</text>
  <line x1="108" y1="120" x2="108" y2="310" stroke="#1a65ac" stroke-width="1" stroke-dasharray="3,3"/>
`);

// 5. incomplete-dimensions.png — frame without dimensions
const incompleteDimensions = svg(`
  <!-- vague frame shape, no numbers -->
  <line x1="160" y1="300" x2="160" y2="120" class="member"/>
  <line x1="480" y1="300" x2="480" y2="120" class="member"/>
  <line x1="160" y1="120" x2="480" y2="120" class="member"/>
  <line x1="160" y1="210" x2="480" y2="210" class="member"/>
  <!-- supports -->
  ${triangleSupport(160, 300)}
  ${triangleSupport(480, 300)}
  <!-- question marks -->
  <text x="120" y="210" text-anchor="middle" font-size="24" fill="#c0392b">?</text>
  <text x="320" y="330" text-anchor="middle" font-size="24" fill="#c0392b">?</text>
  <text x="320" y="105" text-anchor="middle" font-size="24" fill="#c0392b">?</text>
`);

// 6. cropped-frame-sketch.png — partial frame drawing with missing labels
const croppedFrameSketch = svg(`
  <rect x="0" y="0" width="${W}" height="${H}" fill="#fff"/>
  <g transform="translate(-70, 20)">
    <line x1="160" y1="110" x2="160" y2="315" class="member"/>
    <line x1="440" y1="110" x2="440" y2="315" class="member"/>
    <line x1="160" y1="110" x2="440" y2="110" class="member"/>
    <line x1="160" y1="210" x2="440" y2="210" class="member"/>
    <line x1="145" y1="318" x2="175" y2="318" stroke="#333" stroke-width="3"/>
    <line x1="425" y1="318" x2="455" y2="318" stroke="#333" stroke-width="3"/>
    ${[205, 285, 365].map(x => `<line x1="${x}" y1="82" x2="${x}" y2="105" class="load-arrow"/>`).join("\n    ")}
  </g>
  <rect x="420" y="0" width="220" height="${H}" fill="#fff"/>
  <rect x="0" y="300" width="${W}" height="100" fill="#fff"/>
  <text x="78" y="190" text-anchor="middle" font-size="22" fill="#c0392b">?</text>
`);

const fixtures = [
  {
    name: "beam-sketch.png",
    svg: beamSketch,
    textCounts: { "LC1: q = 20 kN/m": 1, "3m": 2 },
  },
  {
    name: "frame-sketch.png",
    svg: frameSketch,
    textCounts: { "D: p = 10 kN/m2; bt = 6m": 2, "3.6m": 2, "6m": 1 },
  },
  {
    name: "truss-diagram.png",
    svg: trussDiagram,
    textCounts: { "LC1: P = 20 kN": 3, "3m": 5, "z=1.5m": 2, "z=3m": 1 },
  },
  {
    name: "portal-frame-diagram.png",
    svg: portalFrame,
    textCounts: { "LC1: q = 6 kN/m": 1, "18m": 1, "7m": 1 },
  },
  { name: "incomplete-dimensions.png", svg: incompleteDimensions },
  { name: "cropped-frame-sketch.png", svg: croppedFrameSketch },
];

function assertFixtureTextEvidence(name, svgContent, textCounts = {}) {
  const values = [...svgContent.matchAll(/<text\b[^>]*>([^<]*)<\/text>/g)].map((match) => match[1]);
  for (const [expected, count] of Object.entries(textCounts)) {
    const actual = values.filter((value) => value === expected).length;
    if (actual !== count) {
      throw new Error(`${name}: expected ${count} visible '${expected}' labels, found ${actual}`);
    }
  }
}

async function generateAll() {
  for (const { name, svg: svgContent, textCounts } of fixtures) {
    assertFixtureTextEvidence(name, svgContent, textCounts);
    const outPath = join(outDir, name);
    await sharp(Buffer.from(svgContent)).png().toFile(outPath);
    const info = await sharp(outPath).metadata();
    console.log(`  ${name}: ${info.width}x${info.height}, ${info.size} bytes`);
  }

  // 7. blurry-image.png — blur the beam sketch
  const beamPath = join(outDir, "beam-sketch.png");
  const blurryPath = join(outDir, "blurry-image.png");
  await sharp(beamPath).blur(8).toFile(blurryPath);
  const blurryInfo = await sharp(blurryPath).metadata();
  console.log(`  blurry-image.png: ${blurryInfo.width}x${blurryInfo.height}, ${blurryInfo.size} bytes`);

  console.log("\nAll fixtures generated.");
}

generateAll().catch((err) => {
  console.error("Error generating fixtures:", err);
  process.exit(1);
});
