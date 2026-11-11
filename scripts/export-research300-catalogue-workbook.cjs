'use strict';

// Usage: node scripts/export-research300-catalogue-workbook.cjs catalogue.json catalogue.xlsx
// This renderer consumes the supplied canonical catalogue; it never reads cases,
// references, historical spreadsheets, or classification sources.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const GROUPS = ['family', 'category', 'structure', 'dimension', 'difficulty', 'modality', 'engine', 'language'];
const COUNTS = ['cases', 'turns', 'states', 'attachmentFiles', 'attachmentUses', 'markdownFiles', 'pngFiles', 'dxfFiles'];
const ROW_COUNTS = COUNTS.slice(1);
const REVIEW_STATUSES = new Set(['pending', 'passed', 'failed', 'partial', 'invalid']);
const TRIAL_STATUSES = new Set(['not-run', 'run']);

function invalid(location, explanation) {
  throw new TypeError(`Invalid catalogue: ${location} ${explanation}`);
}

function object(value, location) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid(location, 'must be an object');
}

function string(value, location, allowEmpty = false) {
  if (typeof value !== 'string' || (!allowEmpty && !value.trim())) invalid(location, 'must be a string');
  if (value.length > 32767) invalid(location, 'exceeds the Excel limit of 32767 characters');
}

function count(value, location) {
  if (!Number.isSafeInteger(value) || value < 0) invalid(location, 'must be a nonnegative safe integer');
}

function array(value, location) {
  if (!Array.isArray(value)) invalid(location, 'must be an array');
}

function validateCatalogue(catalogue) {
  object(catalogue, 'catalogue');
  if (catalogue.schemaVersion !== 1) invalid('schemaVersion', 'must be 1');
  if (catalogue.edition !== 'current') invalid('edition', 'must use current public inputs');
  object(catalogue.totals, 'totals');
  object(catalogue.definitions, 'definitions');
  object(catalogue.breakdowns, 'breakdowns');
  for (const key of COUNTS) count(catalogue.totals[key], `totals.${key}`);

  const choices = {};
  for (const group of GROUPS) {
    const definitions = catalogue.definitions[group];
    array(definitions, `definitions.${group}`);
    choices[group] = new Set();
    for (const [i, definition] of definitions.entries()) {
      const location = `definitions.${group}[${i}]`;
      object(definition, location);
      for (const key of ['key', 'zh', 'en']) string(definition[key], `${location}.${key}`);
      if (definition.description !== undefined) string(definition.description, `${location}.description`, true);
      if (definition.family !== undefined) string(definition.family, `${location}.family`);
      if (choices[group].has(definition.key)) invalid(`${location}.key`, 'is duplicated');
      choices[group].add(definition.key);
    }
  }
  for (const group of GROUPS) {
    for (const [i, definition] of catalogue.definitions[group].entries()) {
      if (definition.family !== undefined && !choices.family.has(definition.family)) invalid(`definitions.${group}[${i}].family`, 'is not defined');
    }
    const buckets = catalogue.breakdowns[group];
    array(buckets, `breakdowns.${group}`);
    const keys = new Set();
    for (const [i, bucket] of buckets.entries()) {
      const location = `breakdowns.${group}[${i}]`;
      object(bucket, location);
      for (const key of ['key', 'zh', 'en']) string(bucket[key], `${location}.${key}`);
      if (!choices[group].has(bucket.key)) invalid(`${location}.key`, 'is not defined');
      if (keys.has(bucket.key)) invalid(`${location}.key`, 'is duplicated');
      keys.add(bucket.key);
      if (bucket.family !== undefined && !choices.family.has(bucket.family)) invalid(`${location}.family`, 'is not defined');
      for (const key of COUNTS) count(bucket[key], `${location}.${key}`);
    }
    for (const key of COUNTS) {
      if (buckets.reduce((sum, bucket) => sum + bucket[key], 0) !== catalogue.totals[key]) invalid(`breakdowns.${group}.${key}`, `must sum to totals.${key}`);
    }
  }

  array(catalogue.cases, 'cases');
  if (catalogue.totals.cases !== catalogue.cases.length) invalid('totals.cases', 'must equal the number of case rows');
  const ids = new Set();
  for (const [i, row] of catalogue.cases.entries()) {
    const location = `cases[${i}]`;
    object(row, location);
    for (const key of ['id', 'title', 'focus', 'difficultyReason', 'inputReviewStatus', 'modelTrialStatus']) string(row[key], `${location}.${key}`, key === 'focus' || key === 'difficultyReason');
    if (ids.has(row.id)) invalid(`${location}.id`, 'is duplicated');
    ids.add(row.id);
    for (const key of GROUPS) {
      string(row[key], `${location}.${key}`);
      if (!choices[key].has(row[key])) invalid(`${location}.${key}`, 'is not defined');
    }
    if (!['zh', 'en'].includes(row.language)) invalid(`${location}.language`, 'must be zh or en');
    if (!['text', 'image', 'dxf'].includes(row.modality)) invalid(`${location}.modality`, 'must be text, image, or dxf');
    for (const key of ROW_COUNTS) count(row[key], `${location}.${key}`);
    for (const key of ['authored', 'referenceReady', 'nativeVerified', 'accepted']) {
      if (typeof row[key] !== 'boolean') invalid(`${location}.${key}`, 'must be a boolean');
    }
    if (!REVIEW_STATUSES.has(row.inputReviewStatus)) invalid(`${location}.inputReviewStatus`, 'must be pending, passed, failed, partial, or invalid');
    if (!TRIAL_STATUSES.has(row.modelTrialStatus)) invalid(`${location}.modelTrialStatus`, 'must be not-run or run');
  }
  for (const key of ROW_COUNTS) {
    if (catalogue.cases.reduce((sum, row) => sum + row[key], 0) !== catalogue.totals[key]) invalid(`totals.${key}`, 'must equal the sum of case rows');
  }
}

function safeDirectory(directory) {
  const parsed = path.parse(directory);
  let current = parsed.root;
  for (const part of directory.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    let stat;
    try {
      stat = fs.lstatSync(current);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      fs.mkdirSync(current);
      stat = fs.lstatSync(current);
    }
    if (stat.isSymbolicLink()) throw new Error(`Workbook parent must not contain a symlink: ${current}`);
    if (!stat.isDirectory()) throw new Error(`Workbook parent must be a directory: ${current}`);
  }
}

function safeTarget(target) {
  try {
    const stat = fs.lstatSync(target);
    if (stat.isSymbolicLink()) throw new Error(`Workbook target must not be a symlink: ${target}`);
    if (!stat.isFile()) throw new Error(`Workbook target must be a regular file: ${target}`);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}

/** Synchronously render one already-built catalogue and atomically replace target. */
function writeCatalogueWorkbook(catalogue, target) {
  validateCatalogue(catalogue);
  if (typeof target !== 'string' || !target.trim()) throw new TypeError('Workbook target must be a nonempty path');
  const destination = path.resolve(target);
  safeDirectory(path.dirname(destination));
  safeTarget(destination);
  const temporary = fs.mkdtempSync(path.join(path.dirname(destination), `.${path.basename(destination)}.tmp-`));
  try {
    const staged = path.join(temporary, 'catalogue.xlsx');
    const result = spawnSync('python3', ['-I', path.join(__dirname, 'research300', 'catalogue_workbook.py'), staged], {
      input: JSON.stringify(catalogue), encoding: 'utf8', maxBuffer: 8 * 1024 * 1024,
    });
    if (result.error || result.status !== 0) throw new Error(`Cannot generate catalogue workbook: ${result.error?.message || result.stderr.trim() || `Python exited with status ${result.status}`}`);
    safeTarget(destination);
    fs.renameSync(staged, destination);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
  return target;
}

if (require.main === module) {
  try {
    if (process.argv.length !== 4) throw new Error('Usage: node scripts/export-research300-catalogue-workbook.cjs catalogue.json catalogue.xlsx');
    let catalogue;
    try {
      catalogue = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
    } catch (error) {
      throw new Error(`Cannot read catalogue JSON: ${error.message}`);
    }
    console.log(writeCatalogueWorkbook(catalogue, process.argv[3]));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = { writeCatalogueWorkbook };
