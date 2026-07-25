const fs = require("node:fs");
const path = require("node:path");

const {
  engineeringSpecificationForAssertions,
  isGeneratedEngineeringSpecification,
} = require("../lib/engineering-specification-fixture.cjs");

const SCENARIO_ROOT = path.resolve(__dirname, "..", "scenarios");

function materializeScenario(scenario) {
  let changed = false;
  const topLevelSpecification = engineeringSpecificationForAssertions(
    scenario.expect?.assertions,
    scenario.locale || "zh",
  );
  if (
    topLevelSpecification
    && (
      typeof scenario.engineeringSpecification !== "string"
      || !scenario.engineeringSpecification.trim()
      || isGeneratedEngineeringSpecification(scenario.engineeringSpecification)
    )
    && scenario.engineeringSpecification !== topLevelSpecification
  ) {
    scenario.engineeringSpecification = topLevelSpecification;
    changed = true;
  }
  for (const turn of scenario.turns || []) {
    const specification = engineeringSpecificationForAssertions(
      turn.assertions,
      scenario.locale || "zh",
    );
    if (
      specification
      && (
        typeof turn.engineeringSpecification !== "string"
        || !turn.engineeringSpecification.trim()
        || isGeneratedEngineeringSpecification(turn.engineeringSpecification)
      )
      && turn.engineeringSpecification !== specification
    ) {
      turn.engineeringSpecification = specification;
      changed = true;
    }
  }
  return changed;
}

function main() {
  let changedCount = 0;
  for (const family of fs.readdirSync(SCENARIO_ROOT, { withFileTypes: true })) {
    if (!family.isDirectory()) continue;
    const familyPath = path.join(SCENARIO_ROOT, family.name);
    for (const name of fs.readdirSync(familyPath)) {
      if (!name.endsWith(".json")) continue;
      const scenarioPath = path.join(familyPath, name);
      const scenario = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
      if (!materializeScenario(scenario)) continue;
      fs.writeFileSync(scenarioPath, `${JSON.stringify(scenario, null, 2)}\n`, "utf8");
      changedCount += 1;
    }
  }
  console.log(`Materialized engineering specifications in ${changedCount} scenario files.`);
}

module.exports = {
  materializeScenario,
};

if (require.main === module) {
  main();
}
