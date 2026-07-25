const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const sharp = require("sharp");

const {
  attachVisionSummariesToMessage,
  buildTurnContext,
  buildVisionPrompt,
} = require("../runner.cjs");
const {
  validateDeclaredAnalysisSettings,
  validateDeclaredMaterialProperties,
  validateDeclaredSectionProperties,
} = require("../lib/validate-scenarios.cjs");

test("vision prompt receives neither the user task nor attachment identity", () => {
  const prompt = buildVisionPrompt("en");

  assert.match(prompt, /Extract only information visible in the image/);
  assert.match(prompt, /every visible structural node or joint/i);
  assert.match(prompt, /member connectivity/i);
  assert.match(prompt, /constrained and free degrees of freedom/i);
  assert.match(prompt, /supports from analysis nodes/i);
  assert.doesNotMatch(prompt, /User task|Attachment|5m|drawing-001/i);
});

test("agent input keeps image evidence, engineering specification, and task in separate sections", () => {
  const message = attachVisionSummariesToMessage(
    "Build and analyze the model.",
    [{
      imageIndex: 1,
      model: "vision-model-not-for-agent",
      attachmentName: "semantic-file-name.png",
      summary: '{"geometry":["5 m + 6 m"]}',
    }],
    "en",
    "Material Q345; section B1.",
  );

  assert.match(message, /\[Benchmark vision attachment summaries\]/);
  assert.match(message, /Preserve explicit node coordinates and member connectivity exactly/);
  assert.match(message, /do not introduce conflicting story or bay counts/);
  assert.match(message, /\[Engineering specification\]\nMaterial Q345; section B1\./);
  assert.match(message, /\[User task\]\nBuild and analyze the model\./);
  assert.ok(
    message.indexOf("[User task]") < message.indexOf("[Engineering specification]"),
    "the structural task must lead the engineering properties for robust routing",
  );
  assert.doesNotMatch(message, /vision-model-not-for-agent|semantic-file-name/);
});

test("non-image tasks retain their original message", () => {
  assert.equal(
    attachVisionSummariesToMessage("Original task", [], "en", ""),
    "Original task",
  );
});

test("scenario-level image attachments are parsed only on the first turn", () => {
  const scenario = { locale: "en", attachments: [{ fileId: "drawing" }] };
  const benchmarkContext = { enabledToolIds: [] };
  const first = buildTurnContext({
    scenario,
    turn: {},
    turnIndex: 0,
    benchmarkContext,
    skillIds: [],
  });
  const second = buildTurnContext({
    scenario,
    turn: {},
    turnIndex: 1,
    benchmarkContext,
    skillIds: [],
  });
  const explicitSecond = buildTurnContext({
    scenario,
    turn: { attachments: [{ fileId: "new-drawing" }] },
    turnIndex: 1,
    benchmarkContext,
    skillIds: [],
  });

  assert.deepEqual(first.attachments, scenario.attachments);
  assert.equal(first.restrictFileAccessToAttachments, true);
  assert.equal(second.attachments, undefined);
  assert.equal(second.restrictFileAccessToAttachments, true);
  assert.deepEqual(explicitSecond.attachments, [{ fileId: "new-drawing" }]);
  assert.equal(explicitSecond.restrictFileAccessToAttachments, true);
});

test("all multimodal attachment names are neutral and globally unique", () => {
  const scenarioDir = path.join(__dirname, "..", "scenarios", "multimodal_reverse_engineering");
  const names = [];
  for (const file of fs.readdirSync(scenarioDir).filter((name) => name.endsWith(".json"))) {
    const scenario = JSON.parse(fs.readFileSync(path.join(scenarioDir, file), "utf8"));
    const attachments = [
      ...(scenario.attachments || []),
      ...(scenario.turns || []).flatMap((turn) => turn.attachments || []),
    ];
    for (const attachment of attachments) {
      assert.match(
        attachment.originalName,
        /^drawing-\d{3}\.(?:png|dxf)$/,
        `${scenario.id}: semantic attachment name leaks task information`,
      );
      names.push(attachment.originalName);
    }
  }
  assert.equal(names.length, 50);
  assert.equal(new Set(names).size, names.length);
});

test("all multimodal image fixtures are decodable and keep visible evidence inside the canvas", async () => {
  const scenarioDir = path.join(__dirname, "..", "scenarios", "multimodal_reverse_engineering");
  const imagePaths = new Set();
  for (const file of fs.readdirSync(scenarioDir).filter((name) => name.endsWith(".json"))) {
    const scenario = JSON.parse(fs.readFileSync(path.join(scenarioDir, file), "utf8"));
    const attachments = [
      ...(scenario.attachments || []),
      ...(scenario.turns || []).flatMap((turn) => turn.attachments || []),
    ];
    for (const attachment of attachments) {
      if (String(attachment.mimeType || "").startsWith("image/")) {
        imagePaths.add(path.join(__dirname, "..", attachment.relPath));
      }
    }
  }

  for (const imagePath of imagePaths) {
    const { data, info } = await sharp(imagePath).removeAlpha().raw().toBuffer({ resolveWithObject: true });
    assert.ok(info.width >= 640 && info.height >= 400, `${path.basename(imagePath)}: image resolution is too small`);
    let minX = info.width;
    let minY = info.height;
    let maxX = -1;
    let maxY = -1;
    let visiblePixels = 0;
    for (let y = 0; y < info.height; y += 1) {
      for (let x = 0; x < info.width; x += 1) {
        const offset = (y * info.width + x) * info.channels;
        if (data[offset] >= 245 && data[offset + 1] >= 245 && data[offset + 2] >= 245) continue;
        visiblePixels += 1;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
    assert.ok(visiblePixels >= 500, `${path.basename(imagePath)}: fixture contains too little visible evidence`);
    assert.ok(
      minX >= 4 && minY >= 4 && maxX <= info.width - 5 && maxY <= info.height - 5,
      `${path.basename(imagePath)}: visible evidence touches the canvas edge and may be clipped`,
    );
  }
});

test("DXF tasks separate drawing evidence from engineering specifications without prompt leakage", () => {
  const scenarioDir = path.join(__dirname, "..", "scenarios", "multimodal_reverse_engineering");
  const scenarios = fs.readdirSync(scenarioDir)
    .filter((name) => name.endsWith(".json"))
    .map((name) => JSON.parse(fs.readFileSync(path.join(scenarioDir, name), "utf8")))
    .filter((scenario) => scenario.inputModality === "dxf");

  assert.equal(scenarios.length, 15);
  for (const scenario of scenarios) {
    assert.doesNotMatch(
      scenario.message,
      /\d/,
      `${scenario.id}: task text duplicates numeric DXF evidence`,
    );
    assert.equal(scenario.inputContract?.completeness, "complete");
    const attachment = scenario.attachments?.[0];
    const dxf = fs.readFileSync(path.join(__dirname, "..", attachment.relPath), "utf8");
    assert.match(dxf, /\n9\n\$INSUNITS\n70\n6\n/);

    if (scenario.tags.includes("architectural")) {
      assert.deepEqual(scenario.inputContract.dxfProvides, ["topology", "dimensions"]);
      assert.equal(typeof scenario.engineeringSpecification, "string");
    } else {
      assert.deepEqual(
        scenario.inputContract.dxfProvides,
        ["topology", "dimensions", "supports", "loads"],
      );
      assert.match(dxf, /\n8\nSUPPORT\n/);
      assert.match(dxf, /(?:FIXED|PIN|ROLLER FREE X)/);
      assert.match(dxf, /(?:global [XYZ]|global F[XYZ]|global -Z)/);
      assert.doesNotMatch(dxf, /\|\s*(?:steel|concrete)\b/i);
      assert.doesNotMatch(dxf, /\b3D Frame\b/i);
    }
  }

  const multiCaseDxf = fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "drawings", "frame-complex-2s2b.dxf"),
    "utf8",
  );
  assert.match(multiCaseDxf, /D: global Z q=-10 kN\/m \+ L: global Z q=-8 kN\/m/);
});

test("complete multimodal specifications cannot omit analysis properties", () => {
  const groundTruth = {
    model: {
      materials: [{ name: "Q345", E: 206000, nu: 0.3, rho: 7850, fy: 345 }],
      sections: [{
        name: "H600",
        properties: { A: 0.01368, Iy: 0.000835, Iz: 0.0000417, J: 8.72e-7, G: 79000 },
      }],
    },
  };
  const incomplete = "Material Q345: E=206000 MPa. Section H600: A=0.01368 m2. Use SI units.";
  const errors = [];

  validateDeclaredMaterialProperties(incomplete, groundTruth, 0.05, "scenario", errors);
  validateDeclaredSectionProperties(incomplete, groundTruth, 0.05, "scenario", errors);
  validateDeclaredAnalysisSettings(incomplete, "scenario", errors);

  assert.ok(errors.some((error) => error.includes("Q345.nu")));
  assert.ok(errors.some((error) => error.includes("H600.Iy")));
  assert.ok(errors.some((error) => error.includes("global-Z-up coordinates")));
  assert.ok(errors.some((error) => error.includes("member self-weight policy")));
  assert.ok(errors.some((error) => error.includes("analysis load combination")));
});
