import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Locale, Model, Raw } from './types';
import { words } from './i18n';
import { Thumbnail } from './thumbnail';

export default function Scene({
  model,
  locale,
  name,
}: {
  model: Model;
  locale: Locale;
  name: string;
}) {
  const t = words[locale];
  const host = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [labels, setLabels] = useState(false),
    [loads, setLoads] = useState(true);
  const [loadCase, setLoadCase] = useState(model.load_cases[0]?.id || '');
  const [iso, setIso] = useState(model.coordinate_system.dimension === '3d');
  const [reset, setReset] = useState(0),
    [fallback, setFallback] = useState(false);
  const [selected, setSelected] = useState<Raw | null>(null);
  const [full, setFull] = useState(false);
  const activeLoadType = model.load_cases.find((c) => c.id === loadCase)?.type;
  const floorLoads = (model.stories || []).flatMap((story) =>
    (story.floor_loads || [])
      .filter((load) => load.type === activeLoadType)
      .map((load) => ({
        id: story.id,
        value: load.value,
        elevation: story.elevation == null ? null : story.elevation + story.height,
      })),
  );
  const exporter = useRef<() => void>(() => {});
  useEffect(() => {
    const fn = () => setFull(document.fullscreenElement === panel.current);
    document.addEventListener('fullscreenchange', fn);
    return () => document.removeEventListener('fullscreenchange', fn);
  }, []);
  useEffect(() => {
    const container = host.current;
    if (!container) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    } catch {
      setFallback(true);
      return;
    }
    setFallback(false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor('#f6f9fd');
    container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', t.reference);
    const scene = new THREE.Scene();
    const positions = Object.fromEntries(
      model.nodes.map((n) => [n.id, new THREE.Vector3(n.x, n.y, n.z)]),
    );
    const box = new THREE.Box3().setFromPoints(Object.values(positions));
    const center = box.getCenter(new THREE.Vector3()),
      size = box.getSize(new THREE.Vector3());
    const span = Math.max(size.x, size.y, size.z, 1);
    const camera = new THREE.OrthographicCamera(-span, span, span, -span, span / 1000, span * 100);
    camera.up.set(0, 0, 1);
    const plane = model.coordinate_system.plane || 'xz';
    const direction = iso
      ? new THREE.Vector3(1.4, -2, 1.25)
      : plane === 'xy'
        ? new THREE.Vector3(0, 0, 1)
        : plane === 'yz'
          ? new THREE.Vector3(1, 0, 0)
          : new THREE.Vector3(0, -1, 0);
    if (!iso && plane === 'xy') camera.up.set(0, 1, 0);
    camera.position.copy(center).add(direction.multiplyScalar(span * 3));
    camera.lookAt(center);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(center);
    controls.enableRotate = iso;
    controls.enableDamping = false;
    controls.minZoom = 0.15;
    controls.maxZoom = 15;
    scene.add(new THREE.AmbientLight(0xffffff, 2.4));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(span, -span, span * 3);
    scene.add(light);
    const pickable: THREE.Object3D[] = [];
    const material = (color: string) =>
      new THREE.MeshStandardMaterial({ color, roughness: 0.7, metalness: 0.05 });
    const line = (a: THREE.Vector3, b: THREE.Vector3, radius: number, color: string) => {
      const d = b.clone().sub(a);
      const mesh = new THREE.Mesh(
        new THREE.CylinderGeometry(radius, radius, d.length(), 10),
        material(color),
      );
      mesh.position.copy(a).add(b).multiplyScalar(0.5);
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
      scene.add(mesh);
      return mesh;
    };
    const text = (value: string, at: THREE.Vector3, color = '#415a80', scale = 1) => {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 64;
      const ctx = canvas.getContext('2d')!;
      ctx.font = '28px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillStyle = color;
      ctx.fillText(value, 256, 43);
      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false }));
      sprite.position.copy(at);
      sprite.scale.set(span * 0.55 * scale, span * 0.069 * scale, 1);
      scene.add(sprite);
    };
    for (const e of model.elements) {
      const a = positions[e.nodes[0]],
        b = positions[e.nodes[1]];
      if (!a || !b) continue;
      const mesh = line(a, b, span * 0.0045, '#4775b9');
      mesh.userData.details = {
        [t.elements]: e.id,
        ...e,
        [t.length]: a.distanceTo(b),
        [t.materials]: model.materials.find((m) => m.id === e.material),
        [t.sections]: model.sections.find((s) => s.id === e.section),
      };
      pickable.push(mesh);
      if (labels)
        text(
          e.id,
          a
            .clone()
            .add(b)
            .multiplyScalar(0.5)
            .add(new THREE.Vector3(0, 0, span * 0.025)),
        );
    }
    for (const n of model.nodes) {
      const p = positions[n.id];
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(span * 0.009, 14, 10),
        material('#2358df'),
      );
      mesh.position.copy(p);
      scene.add(mesh);
      mesh.userData.details = {
        [t.nodes]: n.id,
        x: n.x,
        y: n.y,
        z: n.z,
        [t.restraint]:
          (n.restraints || [])
            .map((r, i) => (r ? model.coordinate_system.dof_order[i] : null))
            .filter(Boolean)
            .join(', ') || t.free,
      };
      pickable.push(mesh);
      if (labels) text(n.id, p.clone().add(new THREE.Vector3(0, 0, span * 0.035)), '#203858');
      if (n.restraints?.some(Boolean)) {
        const fixed = n.restraints.every(Boolean);
        const support = new THREE.Mesh(
          fixed
            ? new THREE.BoxGeometry(span * 0.036, span * 0.036, span * 0.022)
            : new THREE.ConeGeometry(span * 0.025, span * 0.033, 4),
          material('#a3b5cc'),
        );
        if (!fixed) support.rotation.x = Math.PI / 2;
        support.position.copy(p).add(new THREE.Vector3(0, 0, -span * 0.021));
        support.userData.details = mesh.userData.details;
        scene.add(support);
        pickable.push(support);
        if (!fixed && n.restraints.slice(0, 3).some((r) => !r)) {
          for (const offset of [-0.011, 0.011]) {
            const roller = new THREE.Mesh(
              new THREE.SphereGeometry(span * 0.006, 10, 8),
              material('#8098b8'),
            );
            roller.position.copy(p).add(new THREE.Vector3(span * offset, 0, -span * 0.044));
            roller.userData.details = mesh.userData.details;
            scene.add(roller);
            pickable.push(roller);
          }
        }
        // Axis ticks expose exact translational constraints; detailed DOFs remain selectable.
        n.restraints.slice(0, 3).forEach((restrained, i) => {
          if (restrained) {
            const v = new THREE.Vector3().setComponent(i, span * 0.033);
            line(p.clone().sub(v), p.clone().add(v), span * 0.002, '#859ab7');
          }
        });
      }
    }
    if (loads)
      for (const load of model.load_cases.find((c) => c.id === loadCase)?.loads || []) {
        const distributed = load.type === 'distributed';
        const force = new THREE.Vector3(
          distributed ? load.wx || 0 : load.fx || 0,
          distributed ? load.wy || 0 : load.fy || 0,
          distributed ? load.wz || 0 : load.fz || 0,
        );
        if (!force.length()) continue;
        const dir = force.clone().normalize();
        const length = span * 0.12;
        const e = model.elements.find((e) => e.id === load.element);
        const points =
          distributed && e
            ? [0, 0.25, 0.5, 0.75, 1].map((u) =>
                positions[e.nodes[0]].clone().lerp(positions[e.nodes[1]], u),
              )
            : load.node && positions[load.node]
              ? [positions[load.node]]
              : [];
        for (const tip of points) {
          const start = tip.clone().addScaledVector(dir, -length);
          scene.add(
            new THREE.ArrowHelper(dir, start, length, '#d98b36', span * 0.025, span * 0.014),
          );
        }
        if (points.length) {
          if (distributed)
            line(
              points[0].clone().addScaledVector(dir, -length),
              points.at(-1)!.clone().addScaledVector(dir, -length),
              span * 0.0014,
              '#d98b36',
            );
          if (labels) {
            const components = Object.entries(load)
              .filter(([key, value]) => /^[fw][xyz]$/.test(key) && value !== 0)
              .map(([key, value]) => `${key}=${value}`)
              .join(' ');
            text(
              components,
              points[Math.floor(points.length / 2)].clone().addScaledVector(dir, -length * 1.25),
              '#a56824',
            );
          }
        }
      }
    if (loads)
      for (const floor of floorLoads) {
        if (floor.elevation == null || !floor.value) continue;
        const nodes = model.nodes.filter((n) => Math.abs(n.z - floor.elevation!) < 1e-6);
        if (!nodes.length) continue;
        // A labeled area-load marker, not a conversion to a fictitious nodal load.
        const point = new THREE.Vector3(
          nodes.reduce((sum, n) => sum + n.x, 0) / nodes.length,
          nodes.reduce((sum, n) => sum + n.y, 0) / nodes.length,
          floor.elevation,
        );
        const direction = new THREE.Vector3(0, 0, -Math.sign(floor.value));
        scene.add(
          new THREE.ArrowHelper(
            direction,
            point.clone().addScaledVector(direction, -span * 0.1),
            span * 0.1,
            '#d98b36',
            span * 0.025,
            span * 0.014,
          ),
        );
        text(
          `${floor.id} · q=${floor.value}${model.unit_system === 'SI' ? ' kN/m²' : ''}`,
          point.clone().add(new THREE.Vector3(0, 0, span * 0.15)),
          '#a56824',
          1.2,
        );
      }
    const grid = new THREE.GridHelper(span * 2.2, 20, '#dbe4ef', '#e9eef5');
    grid.rotation.x = Math.PI / 2;
    grid.position.set(center.x, center.y, box.min.z - span * 0.06);
    scene.add(grid);
    const axisOrigin = new THREE.Vector3(
      box.min.x - span * 0.14,
      box.min.y,
      box.min.z - span * 0.035,
    );
    [
      ['X', 0, '#c15e68'],
      ['Y', 1, '#5c9b87'],
      ['Z', 2, '#5c80c0'],
    ].forEach(([name, axis, color]) => {
      const direction = new THREE.Vector3().setComponent(Number(axis), 1);
      scene.add(
        new THREE.ArrowHelper(
          direction,
          axisOrigin,
          span * 0.1,
          String(color),
          span * 0.015,
          span * 0.007,
        ),
      );
      text(
        String(name),
        axisOrigin.clone().addScaledVector(direction, span * 0.13),
        String(color),
        0.8,
      );
    });
    camera.updateMatrixWorld();
    const projected = Object.values(positions).map((p) =>
      p.clone().applyMatrix4(camera.matrixWorldInverse),
    );
    const fitWidth = Math.max(...projected.map((p) => Math.abs(p.x))) + span * 0.18;
    const fitHeight = Math.max(...projected.map((p) => Math.abs(p.y))) + span * 0.18;
    const resize = () => {
      const w = container.clientWidth,
        h = container.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h);
      const aspect = w / h;
      const half = Math.max(fitHeight, fitWidth / aspect);
      camera.left = -half * aspect;
      camera.right = -camera.left;
      camera.top = half;
      camera.bottom = -half;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    const raycaster = new THREE.Raycaster();
    let down = { x: 0, y: 0 };
    const pointerDown = (e: PointerEvent) => {
      down = { x: e.clientX, y: e.clientY };
    };
    const pointerUp = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      const rect = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          (-(e.clientY - rect.top) / rect.height) * 2 + 1,
        ),
        camera,
      );
      const hit = raycaster.intersectObjects(pickable)[0];
      setSelected(hit?.object.userData.details || null);
    };
    renderer.domElement.addEventListener('pointerdown', pointerDown);
    renderer.domElement.addEventListener('pointerup', pointerUp);
    const render = () => {
      renderer.render(scene, camera);
    };
    controls.addEventListener('change', render);
    controls.update();
    render();
    exporter.current = () => {
      renderer.render(scene, camera);
      const a = document.createElement('a');
      a.download = `${name}-reference.png`;
      a.href = renderer.domElement.toDataURL('image/png');
      a.click();
    };
    return () => {
      observer.disconnect();
      controls.dispose();
      scene.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        mesh.geometry?.dispose();
        const materials = mesh.material
          ? Array.isArray(mesh.material)
            ? mesh.material
            : [mesh.material]
          : [];
        materials.forEach((m) => {
          (m as THREE.MeshBasicMaterial).map?.dispose();
          m.dispose();
        });
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [model, locale, labels, loads, loadCase, iso, reset, name, t]);
  return (
    <div className="scene-panel" ref={panel}>
      <div className="scene-toolbar">
        <div className="segmented">
          <button aria-pressed={!iso} onClick={() => setIso(false)}>
            {t.view2d}
          </button>
          <button aria-pressed={iso} onClick={() => setIso(true)}>
            {t.view3d}
          </button>
        </div>
        <div className="scene-options">
          <button aria-pressed={loads} onClick={() => setLoads(!loads)}>
            {t.loads}
          </button>
          <button aria-pressed={labels} onClick={() => setLabels(!labels)}>
            {t.labels}
          </button>
          <button
            onClick={() => {
              setSelected(null);
              setReset(reset + 1);
            }}
          >
            {t.resetView}
          </button>
          <button
            onClick={() => {
              if (document.fullscreenElement) void document.exitFullscreen();
              else void panel.current?.requestFullscreen();
            }}
          >
            {full ? t.exitFullscreen : t.fullscreen}
          </button>
        </div>
      </div>
      <div className="scene-canvas" ref={host}>
        {fallback && (
          <div className="fallback">
            <Thumbnail model={model} decorative={false} />
            <p>{t.noWebgl}</p>
          </div>
        )}
      </div>
      <div className="scene-caption">
        <span>
          <i className="dot blue" />
          {t.elements}
          <i className="dot gray" />
          {t.supports}
          <i className="dot amber" />
          {t.loads}
        </span>
        <button onClick={() => exporter.current()} disabled={fallback}>
          {t.export} ↗
        </button>
      </div>
      <div className="scene-bottom">
        <label>
          {t.loadCase}{' '}
          <select value={loadCase} onChange={(e) => setLoadCase(e.target.value)}>
            {model.load_cases.map((c) => (
              <option key={c.id}>{c.id}</option>
            ))}
          </select>
        </label>
        <span>{iso ? t.viewGuide : t.select}</span>
      </div>
      {loads && (
        <div className="load-note">
          {floorLoads.length > 0 && (
            <div className="floor-loads">
              <strong>{t.floorLoads}</strong>
              {floorLoads.map((f) => (
                <span key={f.id}>
                  {f.id}: {f.value} {model.unit_system === 'SI' ? 'kN/m²' : ''}
                </span>
              ))}
            </div>
          )}
          <span>{t.loadSchematic}</span>
        </div>
      )}
      {selected && (
        <div className="selection">
          <button
            className="selection-close"
            onClick={() => setSelected(null)}
            aria-label={t.modalClose}
          >
            ×
          </button>
          <pre>{JSON.stringify(selected, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
