const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

async function exportToolContracts(sutRoot, outputPath, enabledToolIds) {
  const modulePath = path.join(sutRoot, 'backend', 'dist', 'agent-langgraph', 'public-tool-contracts.js');
  const {getPublicToolDefinitions} = await import(pathToFileURL(modulePath).href);
  const all = getPublicToolDefinitions();
  const definitions = enabledToolIds.map(name => {
    const definition = all.find(item => item.name === name);
    if (!definition) throw new Error(`Current backend does not expose ${name}`);
    return {name, label: definition.label, description: definition.description, parameters: definition.parameters};
  });
  fs.mkdirSync(path.dirname(outputPath), {recursive: true});
  fs.writeFileSync(outputPath, `${JSON.stringify(definitions, null, 2)}\n`);
  return outputPath;
}
module.exports = {exportToolContracts};
