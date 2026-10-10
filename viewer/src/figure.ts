import { dataUrl } from './data';
import type { Attachment, Locale } from './types';

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}
export async function exportFigure(
  reference: HTMLCanvasElement,
  name: string,
  locale: Locale,
  attachment?: Attachment,
) {
  const canvas = document.createElement('canvas');
  canvas.width = attachment ? 2800 : 1800;
  canvas.height = 1500;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#20304a';
  ctx.font = '32px Arial, Microsoft YaHei, sans-serif';
  ctx.fillText(name, 70, 65);
  const draw = (img: CanvasImageSource, x: number, width: number, iw: number, ih: number) => {
    const scale = Math.min(width / iw, 1140 / ih);
    ctx.drawImage(
      img,
      x + (width - iw * scale) / 2,
      170 + (1140 - ih * scale) / 2,
      iw * scale,
      ih * scale,
    );
  };
  const referenceX = attachment ? 1440 : 70,
    referenceWidth = attachment ? 1290 : 1660;
  if (attachment) {
    ctx.font = '25px Arial, Microsoft YaHei, sans-serif';
    ctx.fillText(locale === 'zh' ? '(a) 原始输入图纸' : '(a) Original input drawing', 70, 135);
    let image: HTMLImageElement;
    if (attachment.mimeType.startsWith('image/'))
      image = await loadImage(dataUrl(attachment.relPath));
    else {
      const svg = [...document.querySelectorAll<SVGSVGElement>('.dxf-svg')].find(
        (s) =>
          s.dataset.source === dataUrl(attachment.relPath).split('/data/')[1] ||
          s.dataset.source === attachment.relPath,
      );
      if (!svg) throw new Error('Drawing preview is not ready');
      const clone = svg.cloneNode(true) as SVGSVGElement;
      clone.setAttribute('width', '1400');
      clone.setAttribute('height', '1140');
      const url = URL.createObjectURL(
        new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml' }),
      );
      try {
        image = await loadImage(url);
      } finally {
        URL.revokeObjectURL(url);
      }
    }
    draw(image, 70, 1290, image.naturalWidth, image.naturalHeight);
  }
  ctx.font = '25px Arial, Microsoft YaHei, sans-serif';
  ctx.fillText(
    locale === 'zh'
      ? `${attachment ? '(b) ' : ''}参考结构`
      : `${attachment ? '(b) ' : ''}Reference structure`,
    referenceX,
    135,
  );
  draw(reference, referenceX, referenceWidth, reference.width, reference.height);
  ctx.fillStyle = '#748298';
  ctx.font = '21px Arial, Microsoft YaHei, sans-serif';
  ctx.fillText(
    locale === 'zh'
      ? 'StructureClaw Benchmark · 冻结参考模型；荷载箭头仅示意方向。'
      : 'StructureClaw Benchmark · Frozen reference model; load arrows are schematic.',
    70,
    1435,
  );
  const link = document.createElement('a');
  link.download = `${name}-figure.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}
