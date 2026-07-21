const INDEPENDENT_SOLVER_VERSION = "direct-stiffness-2d-v1";

function finite(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${label} must be finite`);
  return number;
}

function zeros(rows, columns = rows) {
  return Array.from({ length: rows }, () => Array(columns).fill(0));
}

function transpose(matrix) {
  return matrix[0].map((_, column) => matrix.map((row) => row[column]));
}

function multiply(left, right) {
  const output = zeros(left.length, right[0].length);
  for (let row = 0; row < left.length; row += 1) {
    for (let inner = 0; inner < right.length; inner += 1) {
      if (left[row][inner] === 0) continue;
      for (let column = 0; column < right[0].length; column += 1) {
        output[row][column] += left[row][inner] * right[inner][column];
      }
    }
  }
  return output;
}

function multiplyVector(matrix, vector) {
  return matrix.map((row) => row.reduce((sum, value, index) => sum + value * vector[index], 0));
}

function addVector(left, right, factor = 1) {
  return left.map((value, index) => value + factor * right[index]);
}

function solveDense(matrix, vector) {
  const size = matrix.length;
  const augmented = matrix.map((row, index) => [...row, vector[index]]);
  const scale = Math.max(...matrix.flat().map(Math.abs), 1);
  for (let pivot = 0; pivot < size; pivot += 1) {
    let selected = pivot;
    for (let row = pivot + 1; row < size; row += 1) {
      if (Math.abs(augmented[row][pivot]) > Math.abs(augmented[selected][pivot])) selected = row;
    }
    if (Math.abs(augmented[selected][pivot]) <= scale * 1e-14) {
      throw new Error(`Independent stiffness matrix is singular at degree of freedom ${pivot}`);
    }
    [augmented[pivot], augmented[selected]] = [augmented[selected], augmented[pivot]];
    for (let row = pivot + 1; row < size; row += 1) {
      const factor = augmented[row][pivot] / augmented[pivot][pivot];
      if (factor === 0) continue;
      for (let column = pivot; column <= size; column += 1) {
        augmented[row][column] -= factor * augmented[pivot][column];
      }
    }
  }
  const solution = Array(size).fill(0);
  for (let row = size - 1; row >= 0; row -= 1) {
    const known = augmented[row][size]
      - augmented[row].slice(row + 1, size)
        .reduce((sum, value, offset) => sum + value * solution[row + 1 + offset], 0);
    solution[row] = known / augmented[row][row];
  }
  return solution;
}

function entities(items) {
  return new Map((items || []).map((item) => [String(item.id), item]));
}

function selectedLoads(model) {
  if ((model.load_combinations || []).length !== 1) {
    throw new Error("Independent linear solver requires exactly one load combination");
  }
  const loadCases = entities(model.load_cases);
  const combination = model.load_combinations[0];
  return Object.entries(combination.factors || {}).flatMap(([caseId, rawFactor]) => {
    const loadCase = loadCases.get(String(caseId));
    if (!loadCase) throw new Error(`Unknown load case '${caseId}'`);
    const factor = finite(rawFactor, `load combination factor '${caseId}'`);
    return (loadCase.loads || []).map((load) => ({
      ...load,
      type: load.type || (load.node !== undefined ? "nodal" : "distributed"),
      factor,
    }));
  });
}

function frameLocalStiffness(elasticModulus, area, inertia, length) {
  const axial = elasticModulus * area / length;
  const bending = elasticModulus * inertia;
  const a = 12 * bending / length ** 3;
  const b = 6 * bending / length ** 2;
  const c = 4 * bending / length;
  const d = 2 * bending / length;
  return [
    [axial, 0, 0, -axial, 0, 0],
    [0, a, b, 0, -a, b],
    [0, b, c, 0, -b, d],
    [-axial, 0, 0, axial, 0, 0],
    [0, -a, -b, 0, a, -b],
    [0, b, d, 0, -b, c],
  ];
}

function frameTransformation(cosine, sine) {
  return [
    [cosine, sine, 0, 0, 0, 0],
    [-sine, cosine, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0],
    [0, 0, 0, cosine, sine, 0],
    [0, 0, 0, -sine, cosine, 0],
    [0, 0, 0, 0, 0, 1],
  ];
}

function frameElementData(element, nodes, materials, sections) {
  const start = nodes.get(String(element.nodes[0]));
  const end = nodes.get(String(element.nodes[1]));
  if (!start || !end) throw new Error(`Element '${element.id}' references an unknown node`);
  const dx = finite(end.x, `${element.id}.end.x`) - finite(start.x, `${element.id}.start.x`);
  const dz = finite(end.z, `${element.id}.end.z`) - finite(start.z, `${element.id}.start.z`);
  const length = Math.hypot(dx, dz);
  if (!(length > 0)) throw new Error(`Element '${element.id}' has zero length`);
  const material = materials.get(String(element.material));
  const section = sections.get(String(element.section));
  const elasticModulus = finite(material?.E, `${element.id}.E`) * 1000;
  const area = finite(section?.properties?.A, `${element.id}.A`);
  const inertia = finite(section?.properties?.Iy, `${element.id}.Iy`);
  const transformation = frameTransformation(dx / length, dz / length);
  const localStiffness = frameLocalStiffness(elasticModulus, area, inertia, length);
  return {
    length,
    cosine: dx / length,
    sine: dz / length,
    transformation,
    localStiffness,
    globalStiffness: multiply(transpose(transformation), multiply(localStiffness, transformation)),
  };
}

function frameUniformLoad(load, data) {
  if (String(load.reference_frame || "global") !== "global") {
    throw new Error("Independent frame solver supports global distributed loads only");
  }
  const globalX = finite(load.wx || 0, "distributed wx") * load.factor;
  const globalZ = finite(load.wz || 0, "distributed wz") * load.factor;
  const axial = data.cosine * globalX + data.sine * globalZ;
  const transverse = -data.sine * globalX + data.cosine * globalZ;
  const length = data.length;
  return [
    axial * length / 2,
    transverse * length / 2,
    transverse * length ** 2 / 12,
    axial * length / 2,
    transverse * length / 2,
    -transverse * length ** 2 / 12,
  ];
}

function assemble(matrix, indices, values) {
  for (let row = 0; row < indices.length; row += 1) {
    for (let column = 0; column < indices.length; column += 1) {
      matrix[indices[row]][indices[column]] += values[row][column];
    }
  }
}

function solveFrame(model, loads) {
  const nodes = entities(model.nodes);
  const materials = entities(model.materials);
  const sections = entities(model.sections);
  const nodeIds = [...nodes.keys()];
  const nodeIndex = new Map(nodeIds.map((id, index) => [id, index]));
  const size = nodeIds.length * 3;
  const stiffness = zeros(size);
  const loadVector = Array(size).fill(0);
  const elementData = new Map();
  const elementLoads = new Map((model.elements || []).map((element) => [String(element.id), Array(6).fill(0)]));

  for (const element of model.elements || []) {
    if (!["beam", "column"].includes(element.type)) throw new Error("Mixed frame/truss models are unsupported");
    const data = frameElementData(element, nodes, materials, sections);
    elementData.set(String(element.id), data);
    const indices = element.nodes.flatMap((id) => {
      const offset = nodeIndex.get(String(id)) * 3;
      return [offset, offset + 1, offset + 2];
    });
    assemble(stiffness, indices, data.globalStiffness);
  }

  for (const load of loads) {
    if (load.type === "nodal") {
      const offset = nodeIndex.get(String(load.node)) * 3;
      loadVector[offset] += finite(load.fx || 0, "nodal fx") * load.factor;
      loadVector[offset + 1] += finite(load.fz || 0, "nodal fz") * load.factor;
      loadVector[offset + 2] += finite(load.my || 0, "nodal my") * load.factor;
      continue;
    }
    const elementId = String(load.element);
    const data = elementData.get(elementId);
    const local = frameUniformLoad(load, data);
    elementLoads.set(elementId, addVector(elementLoads.get(elementId), local));
    const global = multiplyVector(transpose(data.transformation), local);
    const element = model.elements.find((candidate) => String(candidate.id) === elementId);
    const indices = element.nodes.flatMap((id) => {
      const offset = nodeIndex.get(String(id)) * 3;
      return [offset, offset + 1, offset + 2];
    });
    indices.forEach((index, position) => { loadVector[index] += global[position]; });
  }

  const fixed = new Set();
  for (const [id, node] of nodes) {
    const offset = nodeIndex.get(id) * 3;
    const restraints = node.restraints || [];
    if (restraints[0]) fixed.add(offset);
    if (restraints[2]) fixed.add(offset + 1);
    if (restraints[4]) fixed.add(offset + 2);
  }
  const free = Array.from({ length: size }, (_, index) => index).filter((index) => !fixed.has(index));
  const reduced = free.map((row) => free.map((column) => stiffness[row][column]));
  const reducedLoad = free.map((index) => loadVector[index]);
  const displacement = Array(size).fill(0);
  solveDense(reduced, reducedLoad).forEach((value, index) => { displacement[free[index]] = value; });
  const residual = addVector(multiplyVector(stiffness, displacement), loadVector, -1);

  const displacements = {};
  const reactions = {};
  for (const [id, node] of nodes) {
    const offset = nodeIndex.get(id) * 3;
    displacements[id] = {
      ux: displacement[offset], uy: 0, uz: displacement[offset + 1],
      rx: 0, ry: -displacement[offset + 2], rz: 0,
    };
    if ((node.restraints || []).some(Boolean)) {
      reactions[id] = { fx: residual[offset], fz: residual[offset + 1], my: -residual[offset + 2] };
    }
  }
  const forces = {};
  for (const element of model.elements || []) {
    const data = elementData.get(String(element.id));
    const indices = element.nodes.flatMap((id) => {
      const offset = nodeIndex.get(String(id)) * 3;
      return [offset, offset + 1, offset + 2];
    });
    const localDisplacement = multiplyVector(data.transformation, indices.map((index) => displacement[index]));
    const localForce = addVector(
      multiplyVector(data.localStiffness, localDisplacement),
      elementLoads.get(String(element.id)),
      -1,
    );
    const area = finite(sections.get(String(element.section))?.properties?.A, `${element.id}.A`);
    forces[String(element.id)] = {
      referenceFrame: "element-local",
      n1: { N: localForce[0], V: localForce[1], M: localForce[2] },
      n2: { N: localForce[3], V: localForce[4], M: localForce[5] },
      axial: localForce[0],
      stress: localForce[0] / area,
    };
  }
  return { status: "success", analysisMode: "independent_2d_frame", displacements, reactions, forces };
}

function solveTruss(model, loads) {
  const nodes = entities(model.nodes);
  const materials = entities(model.materials);
  const sections = entities(model.sections);
  const nodeIds = [...nodes.keys()];
  const nodeIndex = new Map(nodeIds.map((id, index) => [id, index]));
  const size = nodeIds.length * 2;
  const stiffness = zeros(size);
  const loadVector = Array(size).fill(0);
  const elementData = new Map();
  for (const element of model.elements || []) {
    if (element.type !== "truss") throw new Error("Mixed frame/truss models are unsupported");
    const start = nodes.get(String(element.nodes[0]));
    const end = nodes.get(String(element.nodes[1]));
    const dx = finite(end.x, `${element.id}.end.x`) - finite(start.x, `${element.id}.start.x`);
    const dz = finite(end.z, `${element.id}.end.z`) - finite(start.z, `${element.id}.start.z`);
    const length = Math.hypot(dx, dz);
    const cosine = dx / length;
    const sine = dz / length;
    const modulus = finite(materials.get(String(element.material))?.E, `${element.id}.E`) * 1000;
    const area = finite(sections.get(String(element.section))?.properties?.A, `${element.id}.A`);
    const coefficient = modulus * area / length;
    const values = [
      [cosine ** 2, cosine * sine, -(cosine ** 2), -cosine * sine],
      [cosine * sine, sine ** 2, -cosine * sine, -(sine ** 2)],
      [-(cosine ** 2), -cosine * sine, cosine ** 2, cosine * sine],
      [-cosine * sine, -(sine ** 2), cosine * sine, sine ** 2],
    ].map((row) => row.map((value) => value * coefficient));
    const indices = element.nodes.flatMap((id) => {
      const offset = nodeIndex.get(String(id)) * 2;
      return [offset, offset + 1];
    });
    assemble(stiffness, indices, values);
    elementData.set(String(element.id), { length, cosine, sine, modulus, area, indices });
  }
  for (const load of loads) {
    if (load.type !== "nodal") throw new Error("Independent truss solver supports nodal loads only");
    const offset = nodeIndex.get(String(load.node)) * 2;
    loadVector[offset] += finite(load.fx || 0, "nodal fx") * load.factor;
    loadVector[offset + 1] += finite(load.fz || 0, "nodal fz") * load.factor;
  }
  const fixed = new Set();
  for (const [id, node] of nodes) {
    const offset = nodeIndex.get(id) * 2;
    if (node.restraints?.[0]) fixed.add(offset);
    if (node.restraints?.[2]) fixed.add(offset + 1);
  }
  const free = Array.from({ length: size }, (_, index) => index).filter((index) => !fixed.has(index));
  const reduced = free.map((row) => free.map((column) => stiffness[row][column]));
  const displacement = Array(size).fill(0);
  solveDense(reduced, free.map((index) => loadVector[index]))
    .forEach((value, index) => { displacement[free[index]] = value; });
  const residual = addVector(multiplyVector(stiffness, displacement), loadVector, -1);
  const displacements = {};
  const reactions = {};
  for (const [id, node] of nodes) {
    const offset = nodeIndex.get(id) * 2;
    displacements[id] = { ux: displacement[offset], uy: 0, uz: displacement[offset + 1], rx: 0, ry: 0, rz: 0 };
    if ((node.restraints || []).some(Boolean)) reactions[id] = { fx: residual[offset], fz: residual[offset + 1] };
  }
  const forces = {};
  for (const element of model.elements || []) {
    const data = elementData.get(String(element.id));
    const values = data.indices.map((index) => displacement[index]);
    const extension = -data.cosine * values[0] - data.sine * values[1]
      + data.cosine * values[2] + data.sine * values[3];
    const axial = data.modulus * data.area / data.length * extension;
    forces[String(element.id)] = { axial, stress: axial / data.area };
  }
  return { status: "success", analysisMode: "independent_2d_truss", displacements, reactions, forces };
}

function solveIndependentLinearModel(model) {
  if (model?.coordinate_system?.dimension !== "2d" || model.coordinate_system?.plane !== "xz") {
    throw new Error("Independent linear solver supports canonical 2-D X-Z models only");
  }
  const loads = selectedLoads(model);
  const elements = model.elements || [];
  if (elements.every((element) => element.type === "truss")) return solveTruss(model, loads);
  if (elements.every((element) => ["beam", "column"].includes(element.type))) return solveFrame(model, loads);
  throw new Error("Independent linear solver requires a pure frame or pure truss model");
}

module.exports = { INDEPENDENT_SOLVER_VERSION, solveIndependentLinearModel };
