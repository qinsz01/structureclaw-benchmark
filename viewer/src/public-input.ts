import type { ResearchTurn } from './research-types';

export function publicInputForDownload(
  caseId: string,
  turn: Pick<ResearchTurn, 'id' | 'instruction' | 'attachments'>,
) {
  return {
    caseId,
    turnId: turn.id,
    instruction: turn.instruction,
    attachments: turn.attachments.map(({ name, mimeType }) => ({
      name,
      path: name,
      mimeType,
    })),
  };
}
