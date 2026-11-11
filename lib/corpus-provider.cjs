'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { inflateSync } = require('node:zlib');
const { loadPublicInputEdition } = require('./public-input-edition.cjs');
const ROOT = path.resolve(__dirname, '..');
const CASE_ID = /^(STD|INT|MM)-(00[1-9]|0[1-9][0-9]|100)$/;
const PUBLIC_EXTENSIONS = new Set(['.txt', '.csv', '.json', '.svg', '.png', '.dxf']);
const PRIVATE_NAME = /(?:^|\/)(?:native-commercial(?:\/.*)?|contract\.json|model-state[^/]*|reference[^/]*|independent-reference[^/]*|native[^/]*|receipt[^/]*|input-blind-review[^/]*|acceptance[^/]*|manifest\.json|source-plan[^/]*|.*ground-truth.*)$/i;
const HIDDEN_MENTION = /model-state-\d+\.json|independent-reference\.json|reference-requests\.json|native-receipt[^\s]*|input-blind-review\.json/i;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
// Bump when scope resolution, projection, or the agent-visible report protocol
// changes. Runtime/evaluator records bind this independently of authored hashes.
const RESPONSE_CONTRACT_VERSION = 'research300-response-v1';
const RESPONSE_UNITS = {
  m: 'length', mm: 'length', rad: 'rotation',
  N: 'force', kN: 'force', 'N.m': 'moment', 'N*m': 'moment',
  'kN.m': 'moment', 'kN*m': 'moment', 'kN·m': 'moment',
};

function getResponseContract(record, turnIndex) {
  const contract = record.contract;
  if (!Number.isInteger(turnIndex) || turnIndex < 0 || !contract?.turns?.[turnIndex]) throw new Error('turnIndex out of range');
  const turn = contract.turns[turnIndex];
  const ids = (object, key) => {
    if (!Object.hasOwn(object, key)) return null;
    const value = object[key];
    if (!Array.isArray(value) || value.some(id => typeof id !== 'string' || !id.trim()) || new Set(value).size !== value.length) throw new Error(`${key} must contain unique nonempty IDs`);
    return value;
  };
  const outputIds = ids(turn, 'requiredOutputIds'), quantityIds = ids(turn, 'requiredQuantityIds');
  const allOutputs = contract.requiredOutputs;
  if (!Array.isArray(allOutputs)) throw new Error('requiredOutputs must be an array');
  const byOutput = new Map();
  for (const output of allOutputs) {
    if (!output || typeof output.id !== 'string' || byOutput.has(output.id)) throw new Error('requiredOutputs IDs must be unique');
    ids(output, 'turnIds');
    if (!ids(output, 'quantityIds') || !['numerical', 'derived', 'figure', 'interaction'].includes(output.kind)) throw new Error('Invalid requiredOutputs kind or quantityIds');
    byOutput.set(output.id, output);
  }
  const eligible = output => output.state === turn.state && (!output.turnIds || output.turnIds.includes(turn.id));
  if (outputIds?.some(id => !byOutput.has(id) || !eligible(byOutput.get(id)))) throw new Error('requiredOutputIds must resolve to outputs for this turn and state');
  const outputs = allOutputs.filter(output => eligible(output) && (outputIds === null || outputIds.includes(output.id)));
  const sharedState = contract.turns.filter(t => t.state === turn.state && t.expectation !== 'clarify').length > 1;
  if (turn.expectation !== 'clarify' && sharedState && outputIds === null && quantityIds === null && outputs.some(output => !output.turnIds)) {
    throw new Error('Ambiguous turn output scope: shared state requires requiredOutputIds, requiredQuantityIds or output.turnIds');
  }
  const outputQuantities = new Set(outputs.flatMap(output => output.quantityIds || []));
  if (quantityIds?.some(id => !outputQuantities.has(id))) throw new Error('requiredQuantityIds must belong to current required outputs');
  const wanted = new Set(quantityIds === null ? outputQuantities : quantityIds);
  // Figure prose can mention every station in its bundle. A partial numeric
  // allowlist cannot safely redact that prose or redefine the requested figure.
  if (outputs.some(output => output.kind === 'figure' && output.quantityIds.some(id => !wanted.has(id)))) throw new Error('requiredQuantityIds partially excludes a figure output; bind a separate current-turn figure');
  const blocking = turn.expectation === 'clarify';
  if (blocking && (wanted.size || outputs.some(output => output.kind !== 'interaction'))) throw new Error('Blocking clarify turn cannot require numerical or figure outputs');
  const states = record.referenceRequests?.states || [];
  if (!Array.isArray(states)) throw new Error('Invalid response request states');
  const matching = states.filter(state => state.state === turn.state);
  if (matching.length > 1) throw new Error('Ambiguous response request state');
  const requests = matching[0] || { quantities: [], derived: [] };
  const byQuantity = new Map();
  for (const [kind, records] of [['quantity', requests.quantities || []], ['derived', requests.derived || []]]) {
    if (!Array.isArray(records)) throw new Error('Invalid response request definitions');
    for (const request of records) {
      if (!request || typeof request.id !== 'string') throw new Error('Invalid response quantity ID');
      // Only reported IDs need to be unique across selections; unrelated private
      // calculation records may legally reuse an ID under different selections.
      byQuantity.set(request.id, byQuantity.has(request.id) ? null : { kind, request });
    }
  }
  if ([...wanted].some(id => !byQuantity.has(id))) throw new Error('requiredQuantityIds / requiredOutputs quantity IDs do not resolve in current state');
  if ([...wanted].some(id => byQuantity.get(id) === null)) throw new Error('Ambiguous response quantity ID');
  const units = Object.hasOwn(turn, 'outputUnits') ? turn.outputUnits : {};
  if (typeof units !== 'object' || units === null || Array.isArray(units)) throw new Error('outputUnits must be an object');
  for (const [key, unit] of Object.entries(units)) {
    const targets = [...wanted].map(id => byQuantity.get(id).request).filter(q => q.id === key || q.component === key);
    if (!targets.length || !Object.hasOwn(RESPONSE_UNITS, unit) || targets.some(q => RESPONSE_UNITS[unit] !== RESPONSE_UNITS[q.unit])) throw new Error('outputUnits must name current quantities/components with dimension-compatible units');
  }
  const unitFor = q => Object.hasOwn(units, q.id) ? units[q.id] : Object.hasOwn(units, q.component) ? units[q.component] : q.unit;
  const text = value => {
    if (typeof value !== 'string' || !value.trim() || /[\r\n|]/.test(value) || HIDDEN_MENTION.test(value)) throw new Error('Invalid public response selector');
    return value;
  };
  const privateIds = states.flatMap(state => [...(state.quantities || []), ...(state.derived || [])]).map(q => q.id).filter(id => typeof id === 'string' && !wanted.has(id));
  const description = value => {
    if (typeof value !== 'string' || !value.trim() || HIDDEN_MENTION.test(value)) throw new Error('Invalid public output description');
    // Author prose is public only if it does not reintroduce hidden calculation
    // keys omitted by the structured projection. Check whole ID tokens so a
    // short private ID does not match a number or part of a public identifier.
    for (const id of privateIds) {
      const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      if (new RegExp(`(?:^|[^\\p{L}\\p{N}_:@/-])${escaped}(?=$|[^\\p{L}\\p{N}_:@/-])`, 'u').test(value)) throw new Error('Public output description exposes a non-current quantity ID');
    }
    return value;
  };
  const quantities = [], derived = [];
  for (const id of wanted) {
    const { kind, request: q } = byQuantity.get(id);
    if (kind === 'derived') {
      if (!['difference', 'sum', 'max', 'min', 'max_abs'].includes(q.operation) || !Object.hasOwn(RESPONSE_UNITS, unitFor(q))) throw new Error('Invalid public derived definition');
      if (!Array.isArray(q.operands) || !q.operands.length || q.operands.some(id => typeof id !== 'string' || !byQuantity.get(id)) || (q.operation === 'difference' && q.operands.length !== 2)) throw new Error('Invalid public derived operands');
      const definition = { id: text(q.id), operation: q.operation, unit: text(unitFor(q)), description: description(q.description) };
      const extrema = ['max', 'min', 'max_abs'].includes(q.operation);
      if (Object.hasOwn(q, 'tiePolicy') && (!extrema || !['first', 'any'].includes(q.tiePolicy))) throw new Error('Invalid public derived tiePolicy');
      if (extrema) definition.tiePolicy = q.tiePolicy || 'first';
      // A calculation dependency is not a requested answer. Include an operand
      // list only if the whole list is independently public on this turn. Never
      // traverse the private dependency graph or publish a partial formula.
      if (Array.isArray(q.operands) && q.operands.length && q.operands.every(operand => wanted.has(operand))) definition.operands = q.operands.map(text);
      derived.push(definition);
    } else {
      if (!['case', 'combination'].includes(q.selection?.kind) || !['node', 'member'].includes(q.location?.kind)) throw new Error('Invalid public response selection/location');
      const dimension = /^(u[xyz])$/.test(q.component) ? 'length' : /^r[xyz]$/.test(q.component) ? 'rotation' : /^(F[xyz]|N|V[23])$/.test(q.component) ? 'force' : /^(M[xyz23]|T)$/.test(q.component) ? 'moment' : null;
      if (!dimension || RESPONSE_UNITS[q.unit] !== dimension || RESPONSE_UNITS[unitFor(q)] !== dimension) throw new Error('Invalid public response component/unit combination');
      const location = { kind: q.location.kind, id: text(q.location.id) };
      if (location.kind === 'member') {
        if (!Number.isFinite(q.location.positionM) || q.location.positionM < 0 || !['left', 'right'].includes(q.location.side)) throw new Error('Invalid public member station/side');
        location.positionM = q.location.positionM; location.side = q.location.side;
      }
      quantities.push({ id: text(q.id), selection: { kind: q.selection.kind, id: text(q.selection.id) }, location, component: text(q.component), unit: text(unitFor(q)) });
    }
  }
  const publicOutputs = outputs.filter(output => !sharedState || outputIds !== null || output.turnIds).map(output => {
    const projected = { id: text(output.id), kind: text(output.kind), quantityIds: (output.quantityIds || []).filter(id => wanted.has(id)).map(text) };
    // Descriptions specify the requested visible behavior; expectedQuestions,
    // grading rules and private author notes never enter this projection.
    if (['figure', 'interaction'].includes(output.kind)) {
      projected.description = description(output.description);
    }
    return projected;
  }).filter(output => output.quantityIds.length || ['figure', 'interaction'].includes(output.kind));
  return {
    version: RESPONSE_CONTRACT_VERSION,
    format: {
      type: 'markdown-table', target: 'report.markdown',
      columns: ['quantityId', 'selection', 'location', 'component', 'value', 'unit'],
      header: '| quantityId | selection | location | component | value | unit |\n| --- | --- | --- | --- | --- | --- |',
      rowTemplate: '| <quantityId> | <case:ID or combination:ID> | <nodeID or memberID@positionM:left/right> | <component> | <signed numeric value> | <unit> |',
      selection: 'Use case:<id> or combination:<id>; the two selection kinds are distinct even when IDs match.',
      location: 'Use the node ID, or member ID followed by @positionM:left or @positionM:right. Member positionM is in metres, including when displacement is reported in mm.',
      value: 'Report a finite signed numeric value for every listed quantity. Preserve negative values; do not replace signed results with magnitudes.',
      unit: 'Use the unit declared for each quantity on this turn. Unit changes convert the result, not the physical model.',
      derived: {
        target: 'report.derivedQuantities', fields: ['id', 'value', 'unit'],
        messageFormat: 'In the current assistant answer include a fenced json block containing {"derivedQuantities":[...]}. Each entry has id, finite signed numeric value, unit, governingOperand and governingSelection. For difference and sum set both governing fields to null. For max, min and max_abs identify the signed governing result. This is also the structure for report.derivedQuantities when emitting a structured report.',
        markdownAlternative: '| derived | <id> | <signed numeric value> | <unit> | <governingOperand or -> | <case:ID or combination:ID or -> |; use - in both governing columns for difference and sum.',
        governingFields: ['governingOperand', 'governingSelection'],
        governingOperand: 'For max, min and max_abs identify the governing reported quantityId, or the governing public node/member ID when no operand IDs are listed. For max_abs retain the signed governing value. Omitted operand lists use the scope in the definition description.',
        governingSelection: 'For a governing result give {kind:"case" or "combination",id:"<selection ID>"}.',
        governingLocation: 'When a bare public node/member ID is ambiguous among governing candidates, also supply governingLocation: {kind:"node",id:"<node ID>"} or {kind:"member",id:"<member ID>",positionM:<metres>,side:"left" or "right"}. Keep governingOperand as the bare ID; identify the exact station and side in this separate object.',
        tiePolicy: 'For extrema, first selects the first co-governing result in the order stated in the task or definition; any permits any co-governing result. Always report the chosen result with its own sign and exact governing identity and selection.',
      },
    },
    quantities, derived, outputs: publicOutputs,
  };
}

function assertRelative(relative) {
  if (typeof relative !== 'string' || !relative || /[\\:%\x00-\x1f\x7f]/.test(relative)
      || path.posix.isAbsolute(relative) || relative.split('/').some(p => !p || p === '.' || p === '..' || p.startsWith('.'))) {
    throw new Error(`Unsafe relative path: ${JSON.stringify(relative)}`);
  }
}

// Reject all symlinks (including aliases to evaluator files inside the case). The
// benchmark is an immutable file corpus, so no legitimate input needs a link.
function resolveCaseFile(caseDir, relative, { directory = false } = {}) {
  assertRelative(relative);
  const base = path.resolve(caseDir);
  if (fs.lstatSync(base).isSymbolicLink()) throw new Error('Symlink case directory is forbidden');
  let current = base;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.lstatSync(current).isSymbolicLink()) throw new Error(`Symlink path is forbidden: ${relative}`);
  }
  const real = fs.realpathSync(current), realBase = fs.realpathSync(base);
  if (!real.startsWith(realBase + path.sep)) throw new Error(`Path escapes case: ${relative}`);
  const stat = fs.statSync(real);
  if (directory ? !stat.isDirectory() : !stat.isFile()) throw new Error(`Not a ${directory ? 'directory' : 'regular file'}: ${relative}`);
  return real;
}

function listFiles(base, prefix = '') {
  const files = [];
  for (const entry of fs.readdirSync(prefix ? resolveCaseFile(base, prefix, { directory: true }) : base, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) throw new Error(`Symlink path is forbidden: ${relative}`);
    if (entry.isDirectory()) files.push(...listFiles(base, relative));
    else { resolveCaseFile(base, relative); files.push(relative); }
  }
  return files;
}

function containsPrivateData(value) {
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some(containsPrivateData);
  const keys = Object.keys(value);
  if (keys.some(k => /^(referenceKind|referenceRequests|sameEngineTruthStatus|requirementCoverage|sourcePlan|expectedQuestions|modelStates|acceptedEvidence|nativeReceipt)$/i.test(k))) return true;
  if (Array.isArray(value.quantities) && value.quantities.some(q => q && ('value' in q || 'tolerance' in q))) return true;
  if (value.schema_version && value.nodes && value.elements) return true;
  if (value.nodes && value.elements && (value.load_cases || value.analysis_control)) return true;
  if (value.selection && value.location && ('value' in value || 'tolerance' in value)) return true;
  return Object.values(value).some(containsPrivateData);
}

const PNG_CRC_TABLE = Uint32Array.from({ length: 256 }, (_, byte) => {
  let crc = byte;
  for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  return crc >>> 0;
});
function pngCRC(bytes, start, end) {
  let crc = 0xffffffff;
  for (let index = start; index < end; index++) crc = (crc >>> 8) ^ PNG_CRC_TABLE[(crc ^ bytes[index]) & 255];
  return (crc ^ 0xffffffff) >>> 0;
}

function validatePublicPNG(bytes, relative) {
  const fail = reason => { throw new Error(`Invalid PNG ${reason}: ${relative}`); };
  if (!bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) fail('signature');
  let offset = 8, rowBytes = 0, decodedLength = 0, ended = false;
  const imageChunks = [];
  while (offset + 12 <= bytes.length) {
    const length = bytes.readUInt32BE(offset), type = bytes.toString('latin1', offset + 4, offset + 8), end = offset + length + 12;
    if (length > 0x7fffffff || end > bytes.length) fail('chunk length');
    // Current authored images need only these chunks. Reject every ancillary
    // channel, including unknown private chunks, before bytes become public.
    if (!['IHDR', 'IDAT', 'IEND'].includes(type)) fail('unsupported or hidden metadata chunk');
    if (bytes.readUInt32BE(end - 4) !== pngCRC(bytes, offset + 4, end - 4)) fail('chunk CRC');
    if (offset === 8 && type !== 'IHDR') fail('missing initial IHDR');
    if (type === 'IHDR') {
      if (offset !== 8 || length !== 13) fail('IHDR order or length');
      const width = bytes.readUInt32BE(offset + 8), height = bytes.readUInt32BE(offset + 12);
      const bitDepth = bytes[offset + 16], colorType = bytes[offset + 17];
      if (!width || !height || width > 0x7fffffff || height > 0x7fffffff) fail('dimensions');
      // Pillow's authored RGB and RGBA images use 8-bit, non-interlaced
      // scanlines. Unsupported modes are rejected explicitly, not half-parsed.
      if (bitDepth !== 8 || ![2, 6].includes(colorType) || bytes[offset + 18] !== 0 || bytes[offset + 19] !== 0 || bytes[offset + 20] !== 0) fail('unsupported pixel format or interlace mode');
      rowBytes = width * (colorType === 2 ? 3 : 4) + 1;
      decodedLength = rowBytes * height;
      // Bound inflation before allocation; the largest authored drawing is
      // under 27 MiB, while this limit permits substantially larger drawings.
      if (!Number.isSafeInteger(decodedLength) || decodedLength > 256 * 1024 * 1024) fail('unsupported decoded dimensions');
    } else if (type === 'IDAT') {
      imageChunks.push(bytes.subarray(offset + 8, end - 4));
    } else {
      if (length !== 0 || !imageChunks.length || end !== bytes.length) fail('ending, missing IDAT or appended bytes');
      ended = true;
    }
    offset = end;
    if (ended) break;
  }
  if (!ended) fail('missing or truncated IEND');
  const compressed = Buffer.concat(imageChunks);
  let decoded;
  try { decoded = inflateSync(compressed, { info: true, maxOutputLength: decodedLength }); }
  catch (_) { fail('compressed image data'); }
  // zlib otherwise silently ignores bytes after its stream. Require both exact
  // pixel length and consumption, closing a second hidden plaintext channel.
  if (decoded.engine.bytesWritten !== compressed.length || decoded.buffer.length !== decodedLength) fail('image data length or trailing compressed bytes');
  for (let row = 0; row < decodedLength; row += rowBytes) if (decoded.buffer[row] > 4) fail('scanline filter');
}

function assertPublicText(text, relative) {
  if (HIDDEN_MENTION.test(text) || /(?:contract\.json|reference-provenance\.json|native-commercial\/)/i.test(text)) throw new Error(`Hidden file reference in attachment: ${relative}`);
  let object;
  try { object = JSON.parse(text); } catch (_) { /* Prose is permitted. */ }
  if (containsPrivateData(object) || /"(?:referenceKind|modelStates|requirementCoverage|expectedQuestions|acceptedEvidence)"\s*:/.test(text)) throw new Error(`Private model/reference data in attachment: ${relative}`);
}

function assertPublicFile(caseDir, relative, privateHashes = new Set(), { allowMarkdown = false } = {}) {
  assertRelative(relative);
  const ext = path.extname(relative).toLowerCase();
  // The research corpus has no JPEG/PDF attachments. Keep them unavailable
  // until their container metadata and decoded content have an audited parser.
  // Legacy input routing does not call this research-only attachment guard.
  if (['.jpg', '.jpeg', '.pdf'].includes(ext)) throw new Error(`Invalid unsupported research attachment format: ${relative}`);
  if (PRIVATE_NAME.test(relative) || (!PUBLIC_EXTENSIONS.has(ext) && !(allowMarkdown && ext === '.md'))) throw new Error(`Not an allowed public attachment: ${relative}`);
  const file = resolveCaseFile(caseDir, relative), bytes = fs.readFileSync(file);
  if (privateHashes.has(sha256(bytes))) throw new Error(`Public attachment copies a private file: ${relative}`);
  if (ext === '.png') validatePublicPNG(bytes, relative);
  if (['.txt', '.csv', '.json', '.svg', '.dxf', '.md'].includes(ext)) {
    const text = bytes.toString('utf8');
    if (allowMarkdown) assertPublicText(text, relative);
    if (HIDDEN_MENTION.test(text)) throw new Error(`Hidden file reference in attachment: ${relative}`);
    // Inspect JSON regardless of extension, so renaming the answer is no bypass.
    let object;
    try { object = JSON.parse(text); } catch (error) { if (ext === '.json') throw new Error(`Invalid public JSON: ${relative}`); }
    if (containsPrivateData(object) || /"(?:referenceKind|modelStates|requirementCoverage)"\s*:/.test(text)) throw new Error(`Private model/reference data in attachment: ${relative}`);
    if (ext === '.svg') {
      const externalReference = [...text.matchAll(/\bhref\s*=\s*(["'])(.*?)\1|\burl\(\s*([^)]*)\)/gi)].some(m => !(m[2] ?? m[3]).trim().replace(/^["']|["']$/g, '').startsWith('#'));
      if (!/<svg\b/i.test(text) || externalReference || /<\s*(?:metadata|script|foreignObject|desc)\b|<!DOCTYPE|<!ENTITY|\bon\w+\s*=|\bhref\s*=\s*[^\s"']|(?:display\s*:\s*none|visibility\s*[:=]\s*["']?hidden|opacity\s*[:=]\s*["']?0(?:["';\s>]|$))/i.test(text)) throw new Error(`Hidden or active SVG content: ${relative}`);
    }
    if (ext === '.dxf') {
      const lines = text.trim().split(/\r?\n/).map(s => s.trim());
      if ([...bytes].some(b => b > 127) || lines.length % 2 || lines.some((line, i) => i % 2 === 0 && !/^[0-9]+$/.test(line)) || !lines.includes('ENTITIES') || lines.at(-1) !== 'EOF') throw new Error(`Invalid ASCII DXF attachment: ${relative}`);
    }
  }
  return file;
}

function validatePublicAttachments(caseDir, contract) {
  const errors = [], attempt = fn => { try { return fn(); } catch (e) { errors.push(e.message); } };
  if (!Array.isArray(contract.attachments) || !Array.isArray(contract.turns)) return ['attachments and turns must be arrays'];
  const whitelist = new Set(contract.attachments), privateHashes = new Set();
  if (whitelist.size !== contract.attachments.length) errors.push('Duplicate public attachment');
  const privateNames = new Set(['contract.json', 'reference-requests.json', 'independent-reference.json', ...(contract.modelStates || [])]);
  const files = attempt(() => listFiles(caseDir)) || [];
  for (const name of files) if (PRIVATE_NAME.test(name) || privateNames.has(name)) attempt(() => privateHashes.add(sha256(fs.readFileSync(resolveCaseFile(caseDir, name)))));
  for (const name of whitelist) attempt(() => assertPublicFile(caseDir, name, privateHashes));
  const released = new Set();
  for (const [index, turn] of contract.turns.entries()) {
    if (!Array.isArray(turn.attachments)) { errors.push(`turn ${index + 1} attachments must be an array`); continue; }
    for (const name of turn.attachments) {
      if (!whitelist.has(name)) errors.push(`turn ${index + 1} attachment is not whitelisted: ${name}`);
      if (released.has(name)) errors.push(`turn ${index + 1} attachment is not newly visible: ${name}`);
      released.add(name);
      attempt(() => assertPublicFile(caseDir, name, privateHashes));
    }
    if (typeof turn.instruction !== 'string' || HIDDEN_MENTION.test(turn.instruction)) errors.push(`turn ${index + 1} instruction is missing or references hidden files`);
  }
  for (const name of whitelist) if (!released.has(name)) errors.push(`Public attachment never assigned to a turn: ${name}`);
  return [...new Set(errors)];
}

function loadCorpus({ corpus = 'research-300', root = ROOT } = {}) {
  root = path.resolve(root);
  if (!['legacy-150', 'research-300'].includes(corpus)) throw new Error(`Unknown corpus: ${corpus}`);
  let cases;
  if (corpus === 'research-300') {
    const relative = 'corpora/research-300/cases';
    const base = resolveCaseFile(root, relative, { directory: true });
    cases = fs.readdirSync(base).sort().map(id => {
      if (!CASE_ID.test(id)) throw new Error(`Invalid research case ID: ${id}`);
      return { id, caseDir: resolveCaseFile(base, id, { directory: true }) };
    });
  } else {
    const base = resolveCaseFile(root, 'scenarios', { directory: true });
    cases = listFiles(base).filter(f => f.endsWith('.json')).flatMap(name => {
      const file = resolveCaseFile(base, name), payload = readJson(file);
      const records = Array.isArray(payload) ? payload : (Array.isArray(payload.scenarios) ? payload.scenarios : [payload]);
      return records.map(scenario => ({ id: scenario.id, caseDir: root, file, scenario }));
    });
  }
  if (new Set(cases.map(c => c.id)).size !== cases.length) throw new Error('Duplicate corpus case IDs');
  return { id: corpus, corpus, root, cases };
}

function loadCase(corpus, id) {
  if (!corpus || !Array.isArray(corpus.cases)) throw new Error('loadCase requires a loaded corpus');
  const entry = corpus.cases.find(c => c.id === id);
  if (!entry) throw new Error(`Unknown case: ${id}`);
  if (corpus.id === 'legacy-150') return { ...entry, corpus: corpus.id, root: corpus.root, contract: entry.scenario };
  const caseDir = resolveCaseFile(corpus.root, `corpora/research-300/cases/${id}`, { directory: true });
  const contract = readJson(resolveCaseFile(caseDir, 'contract.json'));
  if (contract.id !== id) throw new Error('Case directory and contract ID differ');
  const errors = validatePublicAttachments(caseDir, contract);
  if (errors.length) throw new Error(errors.join('; '));
  const prompt = fs.readFileSync(resolveCaseFile(caseDir, 'prompt.txt'), 'utf8');
  if (HIDDEN_MENTION.test(prompt)) throw new Error('Prompt references hidden files');
  const referenceRequests = readJson(resolveCaseFile(caseDir, 'reference-requests.json'));
  const models = contract.modelStates.map(file => readJson(resolveCaseFile(caseDir, file)));
  return { id, corpus: corpus.id, root: corpus.root, caseDir, contract, prompt, referenceRequests, models };
}

function getFrozenPublicTurnInput(record, turnIndex) {
  if (!Number.isInteger(turnIndex) || turnIndex < 0) throw new Error('turnIndex must be a nonnegative integer');
  const legacy = record.corpus === 'legacy-150';
  const contract = record.contract;
  const turns = legacy ? (contract.turns || [{ message: contract.message, attachments: contract.attachments || [] }]) : contract.turns;
  const turn = turns[turnIndex];
  if (!turn) throw new Error('turnIndex out of range');
  if (!legacy) {
    // Recheck on each turn: changing an attachment after loading is not a bypass.
    const errors = validatePublicAttachments(record.caseDir, contract);
    if (errors.length) throw new Error(errors.join('; '));
  }
  const attachments = (turn.attachments || []).map(attachment => {
    const relPath = legacy ? attachment.relPath : attachment;
    const file = legacy ? resolveCaseFile(record.root, relPath) : assertPublicFile(record.caseDir, relPath);
    return { name: path.basename(relPath), relPath, path: file };
  });
  const input = { id: record.id, turnId: turn.id || `t${turnIndex + 1}`, instruction: legacy ? turn.message : turn.instruction, attachments };
  if (!legacy) input.responseContract = getResponseContract(record, turnIndex);
  return input;
}

function getPublicTurnInput(record, turnIndex, options = {}) {
  if (!options || typeof options !== 'object' || Array.isArray(options) || Object.keys(options).length)
    throw new Error('Public input selection is unavailable; this benchmark has one current input');
  if (record.corpus === 'legacy-150') return getFrozenPublicTurnInput(record, turnIndex);
  if (!Number.isInteger(turnIndex) || turnIndex < 0 || !record.contract.turns?.[turnIndex]) throw new Error('turnIndex out of range');
  // Source attachments are checked again after loading, before their canonical
  // projection is regenerated and compared against its committed bytes.
  const errors = validatePublicAttachments(record.caseDir, record.contract);
  if (errors.length) throw new Error(errors.join('; '));
  return loadPublicInputEdition(record).turns[turnIndex];
}

module.exports = { loadCorpus, loadCase, getPublicTurnInput, getFrozenPublicTurnInput, getResponseContract, RESPONSE_CONTRACT_VERSION, resolveCaseFile, validatePublicAttachments, assertRelative, assertPublicFile, assertPublicText, listFiles, sha256, CASE_ID, PUBLIC_EXTENSIONS };
