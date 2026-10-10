// Read-only renderer adapter for the entity types present in the frozen corpus.
export function parseDxf(text) {
  const lines = text.replace(/^\uFEFF/, '').split(/\r?\n/);
  const pairs = [];
  for (let i = 0; i + 1 < lines.length; i += 2)
    pairs.push([Number(lines[i].trim()), lines[i + 1].trim()]);
  let section = '',
    current = null;
  const entities = [],
    unsupported = new Set();
  const supported = new Set(['LINE', 'TEXT', 'ARC', 'CIRCLE']);
  const finish = () => {
    if (!current) return;
    if (!supported.has(current.type)) {
      unsupported.add(current.type);
      return;
    }
    const get = (code, fallback = 0) => Number(current.values[code] ?? fallback);
    const point = (code) => [get(code), get(code + 10), get(code + 20)];
    const entity = {
      type: current.type,
      layer: current.values[8] || '0',
      start: point(10),
      end: point(11),
      radius: get(40),
      height: get(40, 1),
      angle: get(50),
      endAngle: get(51),
      text: current.values[1] || '',
      align: get(72),
      verticalAlign: get(73),
    };
    entity.text = entity.text
      .replace(/\\U\+([0-9a-f]{4})/gi, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
      .replace(/%%d/gi, '°')
      .replace(/%%p/gi, '±')
      .replace(/%%c/gi, 'Ø');
    if (
      ![
        ...entity.start,
        ...entity.end,
        entity.radius,
        entity.height,
        entity.angle,
        entity.endAngle,
      ].every(Number.isFinite)
    )
      throw new Error('Invalid DXF coordinates');
    entities.push(entity);
  };
  for (let i = 0; i < pairs.length; i++) {
    const [code, value] = pairs[i];
    if (code === 0 && value === 'SECTION') {
      section = pairs[++i]?.[1] || '';
      continue;
    }
    if (code === 0 && value === 'ENDSEC') {
      if (section === 'ENTITIES') finish();
      current = null;
      section = '';
      continue;
    }
    if (section !== 'ENTITIES') continue;
    if (code === 0) {
      finish();
      current = { type: value, values: {} };
    } else if (current) current.values[code] = value;
  }
  return {
    entities,
    unsupported: [...unsupported],
    layers: [...new Set(entities.map((e) => e.layer))].sort(),
  };
}
