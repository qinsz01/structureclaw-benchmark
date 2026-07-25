#!/usr/bin/env node

// Renders ground-truth models into structural plan drawings (PNG).
// Two styles per model: construction-plan and mechanics-diagram.
// Usage: node tests/llm-benchmark/fixtures/plan-renderer.mjs

import sharp from "sharp";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const modelsPath = join(__dirname, "ground-truth-models.json");
const outDir = join(__dirname, "drawings");
mkdirSync(outDir, { recursive: true });

const models = JSON.parse(readFileSync(modelsPath, "utf-8"));
const DRAWING_MODEL_IDS = new Set([
  "beam-simple-6m",
  "beam-complex-12m",
  "frame-simple-1s1b",
  "frame-complex-2s2b",
  "truss-simple-tri",
  "truss-complex-trap",
  "portal-simple-18m",
  "portal-complex-ds",
  "dspan-simple-5-6",
  "dspan-complex-3span",
  "frame3d-simple",
  "frame3d-complex",
  "frame3d-concrete",
]);

// --- SVG generation helpers ---

/** Format a number for dimension labels: integer if whole, 1 decimal otherwise */
function fmt(n) {
  const r = Math.round(n * 10) / 10;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

const COLORS = {
  member: "#222",
  grid: "#8ab4f8",
  gridLine: "#cce0ff",
  dim: "#1565c0",
  dimLine: "#90caf9",
  load: "#c62828",
  loadArrow: "#d32f2f",
  support: "#555",
  bg: "#fff",
  node: "#1565c0",
};

function svgWrap(w, h, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <rect width="${w}" height="${h}" fill="${COLORS.bg}"/>
    <style>
      text { font-family: 'Courier New', 'SimHei', monospace; }
    </style>
    ${body}
  </svg>`;
}

function makeTransform(nodes, padding = { l: 140, r: 140, t: 90, b: 140 }, w = 960, h = 600) {
  const xs = nodes.map(n => n.x);
  const zs = nodes.map(n => n.z);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minZ = Math.min(...zs), maxZ = Math.max(...zs);
  const dataW = maxX - minX || 1;
  const dataH = maxZ - minZ || 1;
  const drawW = w - padding.l - padding.r;
  const drawH = h - padding.t - padding.b;
  const scale = Math.min(drawW / dataW, drawH / dataH);
  const ox = padding.l + (drawW - dataW * scale) / 2;
  const oy = padding.t + (drawH - dataH * scale) / 2;
  const tx = (x) => ox + (x - minX) * scale;
  const tz = (z) => oy + (maxZ - z) * scale;
  return { tx, tz, scale, minX, maxX, minZ, maxZ, w, h, padding };
}

function pinSupport(cx, cy) {
  return `<polygon points="${cx},${cy} ${cx - 10},${cy + 14} ${cx + 10},${cy + 14}" fill="none" stroke="${COLORS.support}" stroke-width="2"/>
    <line x1="${cx - 14}" y1="${cy + 16}" x2="${cx + 14}" y2="${cy + 16}" stroke="${COLORS.support}" stroke-width="2"/>`;
}

function rollerSupport(cx, cy, freeAxis = "x") {
  if (freeAxis === "z") {
    return `<polygon points="${cx},${cy} ${cx + 14},${cy - 10} ${cx + 14},${cy + 10}" fill="none" stroke="${COLORS.support}" stroke-width="2"/>
    <circle cx="${cx + 18}" cy="${cy - 6}" r="3" fill="none" stroke="${COLORS.support}" stroke-width="1.5"/>
    <circle cx="${cx + 18}" cy="${cy + 6}" r="3" fill="none" stroke="${COLORS.support}" stroke-width="1.5"/>
    <line x1="${cx + 22}" y1="${cy - 14}" x2="${cx + 22}" y2="${cy + 14}" stroke="${COLORS.support}" stroke-width="2"/>`;
  }
  return `<polygon points="${cx},${cy} ${cx - 10},${cy + 14} ${cx + 10},${cy + 14}" fill="none" stroke="${COLORS.support}" stroke-width="2"/>
    <circle cx="${cx - 6}" cy="${cy + 18}" r="3" fill="none" stroke="${COLORS.support}" stroke-width="1.5"/>
    <circle cx="${cx + 6}" cy="${cy + 18}" r="3" fill="none" stroke="${COLORS.support}" stroke-width="1.5"/>
    <line x1="${cx - 14}" y1="${cy + 22}" x2="${cx + 14}" y2="${cy + 22}" stroke="${COLORS.support}" stroke-width="2"/>`;
}

function fixedSupport(cx, cy, vertical = true) {
  if (vertical) {
    return `<line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy + 20}" stroke="${COLORS.support}" stroke-width="3"/>
      <line x1="${cx - 12}" y1="${cy + 20}" x2="${cx + 12}" y2="${cy + 20}" stroke="${COLORS.support}" stroke-width="3"/>
      ${[0,1,2,3].map(i => `<line x1="${cx - 10 + i * 7}" y1="${cy + 20}" x2="${cx - 14 + i * 7}" y2="${cy + 26}" stroke="${COLORS.support}" stroke-width="1.5"/>`).join("")}`;
  }
  return `<line x1="${cx}" y1="${cy}" x2="${cx + 20}" y2="${cy}" stroke="${COLORS.support}" stroke-width="3"/>
    <line x1="${cx + 20}" y1="${cy - 12}" x2="${cx + 20}" y2="${cy + 12}" stroke="${COLORS.support}" stroke-width="3"/>`;
}

function dimLine(x1, y1, x2, y2, label, offset = 25) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const isHorizontal = Math.abs(y1 - y2) < 2;
  if (isHorizontal) {
    const dy = y1 + offset;
    return `<line x1="${x1}" y1="${y1}" x2="${x1}" y2="${dy + 5}" stroke="${COLORS.dimLine}" stroke-width="0.8" stroke-dasharray="3,2"/>
      <line x1="${x2}" y1="${y2}" x2="${x2}" y2="${dy + 5}" stroke="${COLORS.dimLine}" stroke-width="0.8" stroke-dasharray="3,2"/>
      <line x1="${x1}" y1="${dy}" x2="${x2}" y2="${dy}" stroke="${COLORS.dim}" stroke-width="1"/>
      <text x="${mx}" y="${dy + 14}" text-anchor="middle" font-size="13" fill="${COLORS.dim}" font-weight="bold">${label}</text>`;
  }
  const dx = x1 - offset;
  return `<line x1="${x1}" y1="${y1}" x2="${dx - 5}" y2="${y1}" stroke="${COLORS.dimLine}" stroke-width="0.8" stroke-dasharray="3,2"/>
    <line x1="${x2}" y1="${y2}" x2="${dx - 5}" y2="${y2}" stroke="${COLORS.dimLine}" stroke-width="0.8" stroke-dasharray="3,2"/>
    <line x1="${dx}" y1="${y1}" x2="${dx}" y2="${y2}" stroke="${COLORS.dim}" stroke-width="1"/>
    <text x="${dx - 8}" y="${my + 4}" text-anchor="end" font-size="13" fill="${COLORS.dim}" font-weight="bold">${label}</text>`;
}

function dimensionChainLabel(axis, coordinates) {
  const intervals = coordinates
    .slice(1)
    .map((value, index) => value - coordinates[index])
    .filter((value) => value > 0)
    .map((value) => `${fmt(value)}m`);
  return `${axis}: ${intervals.join(" + ")}`;
}

function classifyPlanarSupport(restraints) {
  if (restraints === undefined || restraints === null) return "none";
  if (!Array.isArray(restraints) || restraints.length !== 6 || !restraints.every(value => typeof value === "boolean")) {
    throw new Error("Planar support restraints must contain six booleans in ux/uy/uz/rx/ry/rz order");
  }
  if (!restraints.some(Boolean)) return "none";
  const [ux, , uz, , ry] = restraints;
  if (ux && uz && ry) return "fixed";
  if (ux && uz && !ry) return "pinned";
  if (!ux && uz && !ry) return "roller-x";
  if (ux && !uz && !ry) return "roller-z";
  return "partial";
}

function renderPlanarSupport(restraints, cx, cy) {
  const kind = classifyPlanarSupport(restraints);
  if (kind === "none") return "";
  const labels = {
    fixed: "FIXED [UX UZ RY]",
    pinned: "PIN [UX UZ]",
    "roller-x": "ROLLER-X [UZ]",
    "roller-z": "ROLLER-Z [UX]",
  };
  let symbol = "";
  if (kind === "fixed") symbol = fixedSupport(cx, cy);
  else if (kind === "pinned") symbol = pinSupport(cx, cy);
  else if (kind === "roller-x") symbol = rollerSupport(cx, cy, "x");
  else if (kind === "roller-z") symbol = rollerSupport(cx, cy, "z");
  else throw new Error(`The plan renderer cannot represent partial support restraints ${JSON.stringify(restraints)}`);
  return `${symbol}<text x="${cx + 17}" y="${cy + 29}" font-size="9" fill="${COLORS.support}" font-weight="bold" paint-order="stroke" stroke="#fff" stroke-width="3">${labels[kind]}</text>`;
}

function validateFixed3dSupport(restraints) {
  if (!Array.isArray(restraints) || restraints.length !== 6 || !restraints.every(value => typeof value === "boolean")) {
    throw new Error("3-D support restraints must contain six booleans in ux/uy/uz/rx/ry/rz order");
  }
  if (!restraints.some(Boolean)) return false;
  if (!restraints.every(Boolean)) {
    throw new Error(`The 3-D benchmark renderer currently supports fixed restraints only, received ${JSON.stringify(restraints)}`);
  }
  return true;
}

function groupedDistributedLoads(model) {
  const groups = new Map();
  for (const lc of model.load_cases || []) {
    for (const load of lc.loads || []) {
      if (load.type !== "distributed") continue;
      const elementId = load.element;
      const w = Math.abs(load.wz || load.wy || 0);
      if (!elementId || w <= 0) continue;
      if (!groups.has(elementId)) groups.set(elementId, { elementId, loads: [] });
      groups.get(elementId).loads.push({ caseId: lc.id, w });
    }
  }
  return [...groups.values()];
}

function distributedLoadLabel(loads, element, model) {
  const story = model.stories?.find(candidate => candidate.id === element.story);
  const usesStoryAreaLoad = story?.floorLoadUnit === "kN/m2"
    && Number(story.floorLoad) > 0
    && Number(story.tributaryWidthM) > 0
    && Math.abs(Number(story.equivalentLineLoad) - loads[0]?.w) <= 1e-9
    && loads.length === 1;
  if (usesStoryAreaLoad) {
    return `${loads[0].caseId}: p = ${fmt(story.floorLoad)} kN/m2; bt=${fmt(story.tributaryWidthM)}m`;
  }
  return loads.map((load) => `${load.caseId}: q = ${fmt(load.w)} kN/m`).join(" + ");
}

function pointLoadMarkup(caseId, magnitude, cx, cy, structureTopY, placeBelow = false) {
  const label = `${caseId}: P = ${fmt(magnitude)} kN`;
  const labelWidth = Math.max(96, label.length * 7);
  if (placeBelow) {
    const boxY = cy + 58;
    return `<line x1="${cx}" y1="${cy + 3}" x2="${cx}" y2="${cy + 45}" stroke="${COLORS.loadArrow}" stroke-width="3"/>
      <polygon points="${cx - 5},${cy + 39} ${cx + 5},${cy + 39} ${cx},${cy + 51}" fill="${COLORS.loadArrow}"/>
      <rect x="${cx - labelWidth / 2}" y="${boxY}" width="${labelWidth}" height="21" fill="#fff" stroke="${COLORS.loadArrow}" stroke-width="1.2" rx="3"/>
      <text x="${cx}" y="${boxY + 15}" text-anchor="middle" font-size="11" fill="${COLORS.load}" font-weight="bold">${label}</text>`;
  }
  const arrowTop = Math.min(cy - 58, structureTopY - 18);
  const boxY = arrowTop - 30;
  return `<rect x="${cx - labelWidth / 2}" y="${boxY}" width="${labelWidth}" height="21" fill="#fff" stroke="${COLORS.loadArrow}" stroke-width="1.2" rx="3"/>
    <text x="${cx}" y="${boxY + 15}" text-anchor="middle" font-size="11" fill="${COLORS.load}" font-weight="bold">${label}</text>
    <line x1="${cx}" y1="${arrowTop}" x2="${cx}" y2="${cy - 6}" stroke="${COLORS.loadArrow}" stroke-width="3"/>
    <polygon points="${cx - 5},${cy - 12} ${cx + 5},${cy - 12} ${cx},${cy - 2}" fill="${COLORS.loadArrow}"/>`;
}

function trussTopElevationLabels(entry, transform) {
  if (entry.id !== "truss-complex-trap") return "";
  return entry.model.nodes
    .filter((node) => node.id.startsWith("T"))
    .map((node) => `<text x="${transform.tx(node.x)}" y="${transform.tz(node.z) + 19}" text-anchor="middle" font-size="10" fill="${COLORS.dim}" font-weight="bold" paint-order="stroke" stroke="#fff" stroke-width="3">z=${fmt(node.z)}m</text>`)
    .join("");
}

// --- Style A: Construction Plan ---

function renderConstructionPlan(entry) {
  const { model } = entry;
  const nodes = model.nodes;
  const t = makeTransform(nodes, { l: 140, r: 140, t: 55, b: 140 }, 960, 620);
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const structureTopY = Math.min(...nodes.map((node) => t.tz(node.z)));
  const placePointLoadsBelow = model.elements.some((element) => element.type === "truss");

  let body = "";

  // Grid lines
  const xs = [...new Set(nodes.map(n => n.x))].sort((a, b) => a - b);
  const zs = [...new Set(nodes.map(n => n.z))].sort((a, b) => a - b);

  for (const x of xs) {
    const sx = t.tx(x);
    body += `<line x1="${sx}" y1="${t.padding.t - 20}" x2="${sx}" y2="${t.h - t.padding.b + 20}" stroke="${COLORS.gridLine}" stroke-width="0.6" stroke-dasharray="6,4"/>`;
  }
  for (const z of zs) {
    const sy = t.tz(z);
    body += `<line x1="${t.padding.l - 20}" y1="${sy}" x2="${t.w - t.padding.r + 20}" y2="${sy}" stroke="${COLORS.gridLine}" stroke-width="0.6" stroke-dasharray="6,4"/>`;
  }

  // Elements
  for (const el of model.elements) {
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    if (!n1 || !n2) continue;
    const x1 = t.tx(n1.x), y1 = t.tz(n1.z);
    const x2 = t.tx(n2.x), y2 = t.tz(n2.z);
    const sw = el.type === "column" ? 4 : el.type === "truss" ? 2 : 3;
    body += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${COLORS.member}" stroke-width="${sw}" stroke-linecap="round"/>`;
  }

  // Supports
  for (const n of nodes) {
    const sx = t.tx(n.x), sy = t.tz(n.z);
    if (!n.restraints) continue;
    body += renderPlanarSupport(n.restraints, sx, sy);
  }

  // Distributed loads
  for (const group of groupedDistributedLoads(model)) {
    const el = model.elements.find(e => e.id === group.elementId);
    if (!el) continue;
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    const x1 = t.tx(n1.x), y1 = t.tz(n1.z);
    const x2 = t.tx(n2.x), y2 = t.tz(n2.z);
    const count = Math.max(3, Math.min(8, Math.round(Math.hypot(x2 - x1, y2 - y1) / 30)));
    for (let i = 0; i <= count; i++) {
      const frac = i / count;
      const ax = x1 + (x2 - x1) * frac;
      const ay = y1 + (y2 - y1) * frac;
      body += `<line x1="${ax}" y1="${ay - 30}" x2="${ax}" y2="${ay - 4}" stroke="${COLORS.loadArrow}" stroke-width="1.5"/>`;
      body += `<polygon points="${ax - 3},${ay - 8} ${ax + 3},${ay - 8} ${ax},${ay - 2}" fill="${COLORS.loadArrow}"/>`;
    }
    body += `<line x1="${x1}" y1="${y1 - 30}" x2="${x2}" y2="${y2 - 30}" stroke="${COLORS.loadArrow}" stroke-width="1"/>`;
    const lx = (x1 + x2) / 2, ly = (y1 + y2) / 2 - 38;
    body += `<text x="${lx}" y="${ly}" text-anchor="middle" font-size="12" fill="${COLORS.load}" font-weight="bold">${distributedLoadLabel(group.loads, el, model)}</text>`;
  }

  // Point loads are appended after dimensions so their straight vectors remain unobstructed.
  let pointLoadBody = "";
  for (const lc of model.load_cases || []) {
    for (const load of lc.loads || []) {
      if (load.node) {
        const n = nodeMap.get(load.node);
        if (!n) continue;
        const sx = t.tx(n.x), sy = t.tz(n.z);
        const fz = Math.abs(load.fz || 0);
        if (fz > 0) {
          pointLoadBody += pointLoadMarkup(lc.id, fz, sx, sy, structureTopY, placePointLoadsBelow);
        }
      }
    }
  }

  // Dimension lines
  if (xs.length >= 2) {
    for (let i = 0; i < xs.length - 1; i++) {
      const span = xs[i + 1] - xs[i];
      const offset = placePointLoadsBelow ? 110 : 35 + (xs.length - 2) * 12;
      if (span > 0) body += dimLine(t.tx(xs[i]), t.tz(Math.min(...zs)), t.tx(xs[i + 1]), t.tz(Math.min(...zs)), `${fmt(span)}m`, offset);
    }
  }
  if (zs.length >= 2) {
    for (let i = 0; i < zs.length - 1; i++) {
      const h = zs[i + 1] - zs[i];
      if (h > 0) body += dimLine(t.tx(Math.min(...xs)), t.tz(zs[i]), t.tx(Math.min(...xs)), t.tz(zs[i + 1]), `${fmt(h)}m`, 40);
    }
  }

  body += pointLoadBody;
  body += trussTopElevationLabels(entry, t);
  return svgWrap(t.w, t.h, body);
}

// --- Style B: Mechanics Diagram ---

function renderMechanicsDiagram(entry) {
  const { model } = entry;
  const nodes = model.nodes;
  const t = makeTransform(nodes, { l: 120, r: 140, t: 55, b: 130 }, 920, 550);
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const structureTopY = Math.min(...nodes.map((node) => t.tz(node.z)));
  const placePointLoadsBelow = model.elements.some((element) => element.type === "truss");

  let body = "";

  // Elements
  for (const el of model.elements) {
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    if (!n1 || !n2) continue;
    body += `<line x1="${t.tx(n1.x)}" y1="${t.tz(n1.z)}" x2="${t.tx(n2.x)}" y2="${t.tz(n2.z)}" stroke="${COLORS.member}" stroke-width="2.5" stroke-linecap="round"/>`;
  }

  // Nodes
  for (const n of nodes) {
    const sx = t.tx(n.x), sy = t.tz(n.z);
    body += `<circle cx="${sx}" cy="${sy}" r="4" fill="${COLORS.node}"/>`;
    body += `<text x="${sx + 8}" y="${sy - 8}" font-size="10" fill="${COLORS.node}">${n.id}</text>`;
  }

  // Supports
  for (const n of nodes) {
    if (!n.restraints) continue;
    const sx = t.tx(n.x), sy = t.tz(n.z);
    body += renderPlanarSupport(n.restraints, sx, sy);
  }

  // Distributed loads
  for (const group of groupedDistributedLoads(model)) {
    const el = model.elements.find(e => e.id === group.elementId);
    if (!el) continue;
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    const x1 = t.tx(n1.x), y1 = t.tz(n1.z);
    const x2 = t.tx(n2.x), y2 = t.tz(n2.z);
    const count = Math.max(2, Math.min(6, Math.round(Math.hypot(x2 - x1, y2 - y1) / 40)));
    for (let i = 0; i <= count; i++) {
      const frac = i / count;
      const ax = x1 + (x2 - x1) * frac;
      const ay = y1 + (y2 - y1) * frac;
      body += `<line x1="${ax}" y1="${ay - 28}" x2="${ax}" y2="${ay - 4}" stroke="${COLORS.loadArrow}" stroke-width="1.5"/>`;
      body += `<polygon points="${ax - 3},${ay - 8} ${ax + 3},${ay - 8} ${ax},${ay - 2}" fill="${COLORS.loadArrow}"/>`;
    }
    body += `<line x1="${x1}" y1="${y1 - 28}" x2="${x2}" y2="${y2 - 28}" stroke="${COLORS.loadArrow}" stroke-width="1"/>`;
    const lx = (x1 + x2) / 2, ly = Math.min(y1, y2) - 36;
    body += `<text x="${lx}" y="${ly}" text-anchor="middle" font-size="12" fill="${COLORS.load}" font-weight="bold">${distributedLoadLabel(group.loads, el, model)}</text>`;
  }

  // Point loads are appended after dimensions so their straight vectors remain unobstructed.
  let pointLoadBody = "";
  for (const lc of model.load_cases || []) {
    for (const load of lc.loads || []) {
      if (load.node) {
        const n = nodeMap.get(load.node);
        if (!n) continue;
        const sx = t.tx(n.x), sy = t.tz(n.z);
        const fz = Math.abs(load.fz || 0);
        if (fz > 0) {
          pointLoadBody += pointLoadMarkup(lc.id, fz, sx, sy, structureTopY, placePointLoadsBelow);
        }
      }
    }
  }

  // Consecutive dimensions preserve every bay and story independently.
  const xs = [...new Set(nodes.map(n => n.x))].sort((a, b) => a - b);
  const zs = [...new Set(nodes.map(n => n.z))].sort((a, b) => a - b);
  if (xs.length >= 2) {
    for (let i = 0; i < xs.length - 1; i++) {
      body += dimLine(t.tx(xs[i]), t.tz(Math.min(...zs)), t.tx(xs[i + 1]), t.tz(Math.min(...zs)), `${fmt(xs[i + 1] - xs[i])}m`, placePointLoadsBelow ? 110 : 35);
    }
  }
  if (zs.length >= 2) {
    for (let i = 0; i < zs.length - 1; i++) {
      body += dimLine(t.tx(Math.min(...xs)), t.tz(zs[i]), t.tx(Math.min(...xs)), t.tz(zs[i + 1]), `${fmt(zs[i + 1] - zs[i])}m`, 35);
    }
  }

  body += pointLoadBody;
  body += trussTopElevationLabels(entry, t);
  return svgWrap(t.w, t.h, body);
}

// --- 3D Isometric Rendering ---

/** Isometric projection in SVG screen coordinates: x-right-down, y-left-down, z-up */
function isoProject(x, y, z) {
  const ix = (x - y) * Math.cos(Math.PI / 6);
  const iy = (x + y) * Math.sin(Math.PI / 6) - z;
  return { ix, iy };
}

function storyTops(model) {
  let z = 0;
  return (model.stories || []).map((story) => {
    z += Number(story.height) || 0;
    return { ...story, topZ: z };
  });
}

function equivalentLineLoadForStory(model, storyId) {
  const storyElements = new Set(
    (model.elements || [])
      .filter((element) => element.story === storyId)
      .map((element) => element.id)
  );
  for (const loadCase of model.load_cases || []) {
    for (const load of loadCase.loads || []) {
      if (load.type === "distributed" && storyElements.has(load.element)) {
        const value = Math.abs(load.wz || load.wy || 0);
        if (value > 0) return value;
      }
    }
  }
  return 0;
}

function storyLoadLabel(model, story) {
  const declaredFloorLoad = Array.isArray(story.floor_loads)
    ? story.floor_loads.find((load) => Number(load?.value) > 0)
    : null;
  const areaLoad = Math.abs(Number(story.floorLoad ?? declaredFloorLoad?.value ?? story.dead_load) || 0);
  const lineLoad = equivalentLineLoadForStory(model, story.id);
  const loadCase = (model.load_cases || []).find((candidate) => (
    (candidate.loads || []).some((load) => load.story === story.id)
  )) || (model.load_cases || []).find((candidate) => candidate.type === declaredFloorLoad?.type);
  const prefix = loadCase ? `${story.id} ${loadCase.id}` : story.id;
  if (areaLoad > 0) return `${prefix}: p = ${fmt(areaLoad)} kN/m2`;
  if (lineLoad > 0) return `${prefix}: q = ${fmt(lineLoad)} kN/m`;
  return "";
}

function render3dParameterLegends(model, transform, xs, ys, zs) {
  const dimensionBoxX = 80;
  const dimensionBoxY = transform.h - 58;
  const dimensionBoxW = transform.w - 160;
  const dimensionLabels = [
    dimensionChainLabel("X", xs),
    dimensionChainLabel("Y", ys),
    dimensionChainLabel("Z", zs),
  ];
  let body = `<rect x="${dimensionBoxX}" y="${dimensionBoxY}" width="${dimensionBoxW}" height="34" fill="#fff" stroke="${COLORS.dimLine}" stroke-width="1" rx="3"/>`;
  for (let index = 0; index < dimensionLabels.length; index++) {
    const x = dimensionBoxX + dimensionBoxW * (index + 0.5) / dimensionLabels.length;
    body += `<text x="${x}" y="${dimensionBoxY + 22}" text-anchor="middle" font-size="12" fill="${COLORS.dim}" font-weight="bold">${dimensionLabels[index]}</text>`;
  }

  const loadLabels = storyTops(model)
    .map((story) => storyLoadLabel(model, story))
    .filter(Boolean);
  if (loadLabels.length > 0) {
    const loadBoxW = 190;
    const loadBoxX = transform.w - loadBoxW - 18;
    const loadBoxY = 18;
    const loadBoxH = 18 + loadLabels.length * 20;
    body += `<rect x="${loadBoxX}" y="${loadBoxY}" width="${loadBoxW}" height="${loadBoxH}" fill="#fff" stroke="#ef9a9a" stroke-width="1" rx="3"/>`;
    for (let index = 0; index < loadLabels.length; index++) {
      body += `<text x="${loadBoxX + 10}" y="${loadBoxY + 20 + index * 20}" font-size="12" fill="${COLORS.load}" font-weight="bold">${loadLabels[index]}</text>`;
    }
  }
  const supportBoxX = 18;
  const supportBoxY = 18;
  const supportBoxW = 315;
  body += `<rect x="${supportBoxX}" y="${supportBoxY}" width="${supportBoxW}" height="38" fill="#fff" stroke="#bdbdbd" stroke-width="1" rx="3"/>`;
  body += `<text x="${supportBoxX + 10}" y="${supportBoxY + 24}" font-size="11" fill="${COLORS.support}" font-weight="bold">All base supports: FIXED [UX UY UZ RX RY RZ]</text>`;
  return body;
}

function make3dTransform(nodes, padding = { l: 120, r: 140, t: 75, b: 140 }, w = 960, h = 640) {
  const projected = nodes.map(n => isoProject(n.x, n.y, n.z));
  const ixs = projected.map(p => p.ix);
  const iys = projected.map(p => p.iy);
  const minIx = Math.min(...ixs), maxIx = Math.max(...ixs);
  const minIy = Math.min(...iys), maxIy = Math.max(...iys);
  const dataW = maxIx - minIx || 1;
  const dataH = maxIy - minIy || 1;
  const drawW = w - padding.l - padding.r;
  const drawH = h - padding.t - padding.b;
  const scale = Math.min(drawW / dataW, drawH / dataH);
  const ox = padding.l + (drawW - dataW * scale) / 2;
  const oy = padding.t + (drawH - dataH * scale) / 2;
  const tx = (x, y, z) => {
    const { ix } = isoProject(x, y, z);
    return ox + (ix - minIx) * scale;
  };
  const ty = (x, y, z) => {
    const { iy } = isoProject(x, y, z);
    return oy + (iy - minIy) * scale;
  };
  return { tx, ty, scale, w, h, padding, minIx, maxIx, minIy, maxIy };
}

function render3dConstruction(entry) {
  const { model } = entry;
  const nodes = model.nodes;
  const t = make3dTransform(nodes, { l: 120, r: 140, t: 45, b: 140 }, 960, 640);
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  let body = "";

  // Grid lines at ground level (z=0)
  const ys = [...new Set(nodes.map(n => n.y))].sort((a, b) => a - b);
  const xs = [...new Set(nodes.map(n => n.x))].sort((a, b) => a - b);
  const zs = [...new Set(nodes.map(n => n.z))].sort((a, b) => a - b);
  const xMax = Math.max(...xs);
  const yMax = Math.max(...ys);

  // Ground grid lines along X
  for (const y of ys) {
    const sx1 = t.tx(0, y, 0), sy1 = t.ty(0, y, 0);
    const sx2 = t.tx(xMax, y, 0), sy2 = t.ty(xMax, y, 0);
    body += `<line x1="${sx1}" y1="${sy1}" x2="${sx2}" y2="${sy2}" stroke="${COLORS.gridLine}" stroke-width="0.5" stroke-dasharray="4,3"/>`;
  }
  // Ground grid lines along Y
  for (const x of xs) {
    const sx1 = t.tx(x, 0, 0), sy1 = t.ty(x, 0, 0);
    const sx2 = t.tx(x, yMax, 0), sy2 = t.ty(x, yMax, 0);
    body += `<line x1="${sx1}" y1="${sy1}" x2="${sx2}" y2="${sy2}" stroke="${COLORS.gridLine}" stroke-width="0.5" stroke-dasharray="4,3"/>`;
  }

  // Elements - draw columns first, then beams
  const columns = model.elements.filter(e => e.type === "column");
  const beams = model.elements.filter(e => e.type !== "column");

  // Columns (thicker)
  for (const el of columns) {
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    if (!n1 || !n2) continue;
    body += `<line x1="${t.tx(n1.x, n1.y, n1.z)}" y1="${t.ty(n1.x, n1.y, n1.z)}" x2="${t.tx(n2.x, n2.y, n2.z)}" y2="${t.ty(n2.x, n2.y, n2.z)}" stroke="${COLORS.member}" stroke-width="3.5" stroke-linecap="round"/>`;
  }

  // Beams - X-direction (slightly thicker than Y)
  for (const el of beams) {
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    if (!n1 || !n2) continue;
    const isXBeam = n1.y === n2.y;
    const sw = isXBeam ? 2.5 : 2;
    body += `<line x1="${t.tx(n1.x, n1.y, n1.z)}" y1="${t.ty(n1.x, n1.y, n1.z)}" x2="${t.tx(n2.x, n2.y, n2.z)}" y2="${t.ty(n2.x, n2.y, n2.z)}" stroke="${COLORS.member}" stroke-width="${sw}" stroke-linecap="round"/>`;
  }

  // Supports at z=0
  for (const n of nodes) {
    if (!n.restraints) continue;
    if (!validateFixed3dSupport(n.restraints)) continue;
    const sx = t.tx(n.x, n.y, n.z);
    const sy = t.ty(n.x, n.y, n.z);
    body += `<rect x="${sx - 5}" y="${sy - 2}" width="10" height="10" fill="none" stroke="${COLORS.support}" stroke-width="2"/>`;
    body += `<line x1="${sx - 8}" y1="${sy + 10}" x2="${sx + 8}" y2="${sy + 10}" stroke="${COLORS.support}" stroke-width="2"/>`;
  }

  // Floor load arrows; exact magnitudes are listed in the unobstructed legend.
  for (const story of storyTops(model)) {
    const label = storyLoadLabel(model, story);
    if (!label) continue;
    const midY = yMax / 2;
    for (const xFrac of [0.25, 0.5, 0.75]) {
      const ax = t.tx(xMax * xFrac, midY, story.topZ + 0.65);
      const ay1 = t.ty(xMax * xFrac, midY, story.topZ + 0.65);
      const ay2 = t.ty(xMax * xFrac, midY, story.topZ + 0.08);
      body += `<line x1="${ax}" y1="${ay1}" x2="${ax}" y2="${ay2}" stroke="${COLORS.loadArrow}" stroke-width="1.5"/>`;
      body += `<polygon points="${ax - 3},${ay2 - 6} ${ax + 3},${ay2 - 6} ${ax},${ay2}" fill="${COLORS.loadArrow}"/>`;
    }
  }
  body += render3dParameterLegends(model, t, xs, ys, zs);

  return svgWrap(t.w, t.h, body);
}

function render3dMechanics(entry) {
  const { model } = entry;
  const nodes = model.nodes;
  const t = make3dTransform(nodes, { l: 110, r: 130, t: 45, b: 120 }, 920, 580);
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  let body = "";

  // Elements
  const columns = model.elements.filter(e => e.type === "column");
  const beams = model.elements.filter(e => e.type !== "column");

  for (const el of columns) {
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    if (!n1 || !n2) continue;
    body += `<line x1="${t.tx(n1.x, n1.y, n1.z)}" y1="${t.ty(n1.x, n1.y, n1.z)}" x2="${t.tx(n2.x, n2.y, n2.z)}" y2="${t.ty(n2.x, n2.y, n2.z)}" stroke="${COLORS.member}" stroke-width="2.5" stroke-linecap="round"/>`;
  }
  for (const el of beams) {
    const n1 = nodeMap.get(el.nodes[0]);
    const n2 = nodeMap.get(el.nodes[1]);
    if (!n1 || !n2) continue;
    body += `<line x1="${t.tx(n1.x, n1.y, n1.z)}" y1="${t.ty(n1.x, n1.y, n1.z)}" x2="${t.tx(n2.x, n2.y, n2.z)}" y2="${t.ty(n2.x, n2.y, n2.z)}" stroke="${COLORS.member}" stroke-width="1.8" stroke-linecap="round"/>`;
  }

  // Node dots
  for (const n of nodes) {
    const sx = t.tx(n.x, n.y, n.z);
    const sy = t.ty(n.x, n.y, n.z);
    body += `<circle cx="${sx}" cy="${sy}" r="3" fill="${COLORS.node}"/>`;
  }

  // Supports
  for (const n of nodes) {
    if (!n.restraints) continue;
    if (!validateFixed3dSupport(n.restraints)) continue;
    const sx = t.tx(n.x, n.y, n.z);
    const sy = t.ty(n.x, n.y, n.z);
    body += `<line x1="${sx - 6}" y1="${sy + 3}" x2="${sx + 6}" y2="${sy + 3}" stroke="${COLORS.support}" stroke-width="2"/>`;
  }

  // Dimensions
  const xs = [...new Set(nodes.map(n => n.x))].sort((a, b) => a - b);
  const ys = [...new Set(nodes.map(n => n.y))].sort((a, b) => a - b);
  const zs = [...new Set(nodes.map(n => n.z))].sort((a, b) => a - b);
  const xMax = Math.max(...xs), yMax = Math.max(...ys);

  // Floor loads
  for (const story of storyTops(model)) {
    const label = storyLoadLabel(model, story);
    if (!label) continue;
    const midY = yMax / 2;
    for (const xFrac of [0.25, 0.5, 0.75]) {
      const ax = t.tx(xMax * xFrac, midY, story.topZ + 0.65);
      const ay1 = t.ty(xMax * xFrac, midY, story.topZ + 0.65);
      const ay2 = t.ty(xMax * xFrac, midY, story.topZ + 0.08);
      body += `<line x1="${ax}" y1="${ay1}" x2="${ax}" y2="${ay2}" stroke="${COLORS.loadArrow}" stroke-width="1.5"/>`;
      body += `<polygon points="${ax - 3},${ay2 - 6} ${ax + 3},${ay2 - 6} ${ax},${ay2}" fill="${COLORS.loadArrow}"/>`;
    }
  }

  body += render3dParameterLegends(model, t, xs, ys, zs);

  return svgWrap(t.w, t.h, body);
}

function is3dModel(entry) {
  return entry.model.coordinate_system?.dimension === "3d";
}

function nonzero(value) {
  return Math.abs(Number(value) || 0) > 1e-12;
}

function validatePlanarDrawingEvidence(entry) {
  const { model } = entry;
  const nodeIds = new Set(model.nodes.map((node) => node.id));
  const elementIds = new Set(model.elements.map((element) => element.id));
  if (model.nodes.some((node) => nonzero(node.y))) {
    throw new Error(`${entry.id}: planar drawing nodes must lie in the global X-Z plane`);
  }
  for (const node of model.nodes) {
    if (node.restraints) renderPlanarSupport(node.restraints, 0, 0);
  }
  for (const loadCase of model.load_cases || []) {
    for (const load of loadCase.loads || []) {
      if (load.node) {
        if (!nodeIds.has(load.node)
          || !(Number(load.fz) < 0)
          || nonzero(load.fx)
          || nonzero(load.fy)) {
          throw new Error(`${entry.id}: point load ${loadCase.id} cannot be represented without loss`);
        }
      } else if (load.element) {
        if (!elementIds.has(load.element)
          || load.type !== "distributed"
          || !(Number(load.wz) < 0)
          || nonzero(load.wx)
          || nonzero(load.wy)) {
          throw new Error(`${entry.id}: distributed load ${loadCase.id} cannot be represented without loss`);
        }
      } else {
        throw new Error(`${entry.id}: load ${loadCase.id} has no renderable target`);
      }
      if (load.reference_frame !== "global") {
        throw new Error(`${entry.id}: only global load directions can be drawn unambiguously`);
      }
    }
  }
}

function validate3dDrawingEvidence(entry) {
  const { model } = entry;
  const storyIds = new Set((model.stories || []).map((story) => story.id));
  const loadedStories = new Set();
  const nodeElevations = [...new Set(model.nodes.map((node) => node.z))];
  for (const node of model.nodes) {
    if (node.restraints) validateFixed3dSupport(node.restraints);
  }
  for (const loadCase of model.load_cases || []) {
    for (const load of loadCase.loads || []) {
      if (load.type !== "distributed"
        || load.source !== "story_floor_loads"
        || !storyIds.has(load.story)
        || !(Number(load.wz) < 0)
        || nonzero(load.wx)
        || nonzero(load.wy)
        || load.reference_frame !== "global") {
        throw new Error(`${entry.id}: 3-D load ${loadCase.id} cannot be represented by a story-area-load legend`);
      }
      loadedStories.add(load.story);
    }
  }
  for (const story of storyTops(model)) {
    const declaredFloorLoads = Array.isArray(story.floor_loads) ? story.floor_loads : [];
    const hasCanonicalAreaLoad = story.floorLoadUnit === "kN/m2" && Number(story.floorLoad) > 0;
    const hasDeclaredAreaLoad = declaredFloorLoads.some((load) => Number(load?.value) > 0);
    if ((!hasCanonicalAreaLoad && !hasDeclaredAreaLoad)
      || (!loadedStories.has(story.id) && !hasDeclaredAreaLoad)
      || !nodeElevations.some((value) => Math.abs(value - story.topZ) <= 1e-9)) {
      throw new Error(`${entry.id}: story ${story.id} lacks complete visible area-load evidence`);
    }
  }
}

function validateDrawingEvidence(entry) {
  if (is3dModel(entry)) validate3dDrawingEvidence(entry);
  else validatePlanarDrawingEvidence(entry);
}

// --- Main ---

async function renderAll() {
  const drawingModels = models.filter((model) => DRAWING_MODEL_IDS.has(model.id));
  if (drawingModels.length !== DRAWING_MODEL_IDS.size) {
    throw new Error(`Expected ${DRAWING_MODEL_IDS.size} drawing models, found ${drawingModels.length}`);
  }
  for (const model of drawingModels) {
    validateDrawingEvidence(model);
    const is3d = is3dModel(model);
    for (const style of ["construction", "mechanics"]) {
      const suffix = style === "construction" ? "construction" : "mechanics";
      const fileName = `${model.id}-${suffix}.png`;
      let svg;
      if (is3d) {
        svg = style === "construction" ? render3dConstruction(model) : render3dMechanics(model);
      } else {
        svg = style === "construction" ? renderConstructionPlan(model) : renderMechanicsDiagram(model);
      }

      const outPath = join(outDir, fileName);
      await sharp(Buffer.from(svg)).png().toFile(outPath);
      const meta = await sharp(outPath).metadata();
      console.log(`  ${fileName}: ${meta.width}x${meta.height}, ${meta.size} bytes${is3d ? " (3D)" : ""}`);
    }
  }
  console.log(`\nRendered ${drawingModels.length * 2} drawings.`);
}

renderAll().catch((err) => { console.error("Error:", err); process.exit(1); });
