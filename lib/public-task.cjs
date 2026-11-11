'use strict';

const CASE_ID = /^(STD|INT|MM)-(00[1-9]|0[1-9][0-9]|100)$/;
const MIME_TYPES = Object.freeze({
  '.png': 'image/png', '.dxf': 'image/vnd.dxf', '.svg': 'image/svg+xml',
  '.md': 'text/markdown', '.txt': 'text/plain', '.csv': 'text/csv', '.json': 'application/json',
});
const PRIVATE_NAME = /^(?:contract|manifest|task|model-state|reference|independent-reference|native|receipt|input-blind-review|acceptance|source-plan|author-audit|ground-truth)(?:[.-]|$)/i;

function deliveryName(name) {
  if (typeof name !== 'string' || !name || name.startsWith('.')
      || /[\\/:%\x00-\x1f\x7f]/.test(name) || name.trim() !== name
      || PRIVATE_NAME.test(name) || /[a-f0-9]{64}/i.test(name)) {
    throw new Error('Unsafe or private attachment delivery name');
  }
  const extension = name.slice(name.lastIndexOf('.')).toLowerCase();
  if (!Object.hasOwn(MIME_TYPES, extension)) throw new Error('Unsupported public attachment delivery name');
  return { name, path: name, mimeType: MIME_TYPES[extension] };
}

// Provider envelopes bind authoring and evaluation records internally. This is
// the separate, closed projection suitable for a model or a public task viewer.
function toPublicTask(input) {
  if (!input || !CASE_ID.test(input.id)) throw new Error('Invalid public task id');
  if (typeof input.turnId !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(input.turnId)) throw new Error('Invalid public task turn id');
  if (typeof input.instruction !== 'string' || !input.instruction.trim()) throw new Error('Missing public task instruction');
  if (!Array.isArray(input.attachments)) throw new Error('Public task attachments must be an array');
  const attachments = input.attachments.map(attachment => deliveryName(attachment?.name));
  if (new Set(attachments.map(attachment => attachment.name)).size !== attachments.length) throw new Error('Duplicate public attachment delivery name');
  return { id: input.id, turnId: input.turnId, instruction: input.instruction, attachments };
}

module.exports = { toPublicTask };
