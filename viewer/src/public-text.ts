export type PublicTextBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'heading'; level: number; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] };

function cells(line: string): string[] | null {
  const text = line.trim();
  if (!text.startsWith('|') || !text.endsWith('|')) return null;
  const result: string[] = [];
  let cell = '';
  for (let i = 1; i < text.length - 1; i++) {
    const ch = text[i];
    if (ch === '\\' && ['|', '\\'].includes(text[i + 1])) cell += text[++i];
    else if (ch === '|') {
      result.push(cell.trim());
      cell = '';
    } else cell += ch;
  }
  result.push(cell.trim());
  const entities: Record<string, string> = {
    '&#124;': '|',
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
  };
  return result.map((value) =>
    value.replace(/&#124;|&amp;|&lt;|&gt;/g, (entity) => entities[entity]),
  );
}

/** A deliberately small display format. Every cell remains text, never HTML. */
export function parsePublicText(text: string): PublicTextBlock[] {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const blocks: PublicTextBlock[] = [];
  const tableHeader = (index: number) => {
    const headers = cells(lines[index] || '');
    const separator = cells(lines[index + 1] || '');
    return headers &&
      separator &&
      headers.length === separator.length &&
      separator.every((cell) => /^:?-{3,}:?$/.test(cell))
      ? headers
      : null;
  };
  for (let i = 0; i < lines.length;) {
    if (!lines[i].trim()) {
      i++;
      continue;
    }
    const heading = lines[i].match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] });
      i++;
      continue;
    }
    const headers = tableHeader(i);
    if (headers) {
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length) {
        const row = cells(lines[i]);
        if (!row || row.length !== headers.length) break;
        rows.push(row);
        i++;
      }
      blocks.push({ type: 'table', headers, rows });
      continue;
    }
    if (/^[-*]\s+/.test(lines[i])) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i]))
        items.push(lines[i++].replace(/^[-*]\s+/, ''));
      blocks.push({ type: 'list', items });
      continue;
    }
    const paragraph: string[] = [lines[i++]];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^#{1,6}\s+|^[-*]\s+/.test(lines[i]) &&
      !tableHeader(i)
    )
      paragraph.push(lines[i++]);
    blocks.push({ type: 'paragraph', text: paragraph.join('\n') });
  }
  return blocks;
}
