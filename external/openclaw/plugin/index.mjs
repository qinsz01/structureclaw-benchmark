import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);

function readToolDefinitions() {
  const filePath = requireEnvironmentPath("SCLAW_OPENCLAW_TOOL_CONTRACTS");
  const definitions = readJson(filePath);
  if (!Array.isArray(definitions) || !definitions.length) throw new Error("Public tool contracts are missing");
  return definitions;
}

let runtimePromise;
let toolQueue = Promise.resolve();

function requireEnvironmentPath(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required by the StructureClaw benchmark plugin`);
  return path.resolve(value);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporaryPath = `${filePath}.${process.pid}.${randomUUID()}.tmp`;
  fs.writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`);
  fs.renameSync(temporaryPath, filePath);
}

function plainMessage(message) {
  if (!message || typeof message !== "object") return message;
  const source = typeof message.toDict === "function"
    ? message.toDict()?.data || message
    : message;
  return {
    role: source.role || source.type || (source.name ? "tool" : undefined),
    type: source.type || source.role || (source.name ? "tool" : undefined),
    name: source.name,
    content: source.content ?? "",
    tool_call_id: source.tool_call_id,
    response_metadata: source.response_metadata,
    usage_metadata: source.usage_metadata,
    additional_kwargs: source.additional_kwargs,
  };
}

function commandUpdate(result) {
  return result && typeof result === "object" && result.update && typeof result.update === "object"
    ? result.update
    : null;
}

function toolContent(result, update) {
  const messages = Array.isArray(update?.messages) ? update.messages : [];
  const last = messages.at(-1);
  const content = last?.content ?? last?.kwargs?.content;
  if (typeof content === "string") return content;
  if (content !== undefined) return JSON.stringify(content);
  if (typeof result === "string") return result;
  return JSON.stringify(result ?? null);
}

function applyStateUpdate(state, update, applyPublicToolStateUpdate) {
  if (!update) return;
  Object.assign(state, applyPublicToolStateUpdate(state, update));
  if (Array.isArray(update.messages)) {
    state.messages.push(...update.messages.map(plainMessage));
  }
}

function constrainSelectedSkills(state, allowedSkillIds) {
  const allowed = new Set(allowedSkillIds);
  const requested = Array.isArray(state.selectedSkillIds) ? state.selectedSkillIds : [];
  state.selectedSkillIds = [...new Set(requested.filter((skillId) => allowed.has(skillId)))];
  if (state.selectedSkillIds.length === 0) {
    state.selectedSkillIds = [...allowedSkillIds];
  }
}

function appendAssistantToolCall(state, name, toolCallId, params) {
  state.messages.push({
    role: "assistant",
    type: "ai",
    content: "",
    tool_calls: [{
      id: toolCallId,
      name,
      args: params,
      type: "tool_call",
    }],
  });
}

function appendToolResult(state, name, toolCallId, content, responseMetadata = undefined) {
  state.messages.push({
    role: "tool",
    type: "tool",
    name,
    tool_call_id: toolCallId,
    content,
    response_metadata: responseMetadata,
  });
}

function parseClarificationOptions(optionsJson) {
  if (!optionsJson) return undefined;
  try {
    const parsed = JSON.parse(optionsJson);
    return Array.isArray(parsed) ? parsed.map(String) : undefined;
  } catch {
    return undefined;
  }
}

async function initializeRuntime() {
  const runConfigPath = requireEnvironmentPath("SCLAW_OPENCLAW_RUN_CONFIG");
  const sutRoot = requireEnvironmentPath("SCLAW_ROOT");
  const benchmarkRoot = requireEnvironmentPath("SCLAW_BENCHMARK_ROOT");
  const runConfig = readJson(runConfigPath);
  const runtimeModulePath = path.join(sutRoot, "backend", "dist", "agent-runtime", "index.js");
  const serviceModulePath = path.join(
    sutRoot,
    "backend",
    "dist",
    "agent-langgraph",
    "agent-service.js",
  );
  const registryModulePath = path.join(
    sutRoot,
    "backend",
    "dist",
    "agent-langgraph",
    "tool-registry.js",
  );
  const [{ AgentSkillRuntime }, { LangGraphAgentService }, { createRegisteredTools }, { summarizeFileImages }, { applyPublicToolStateUpdate }] =
    await Promise.all([
      import(pathToFileURL(runtimeModulePath).href),
      import(pathToFileURL(serviceModulePath).href),
      import(pathToFileURL(registryModulePath).href),
      import(pathToFileURL(path.join(sutRoot, "backend", "dist", "agent-langgraph", "attachment-vision.js")).href),
      import(pathToFileURL(path.join(sutRoot, "backend", "dist", "agent-langgraph", "public-tool-contracts.js")).href),
    ]);

  const skillRuntime = new AgentSkillRuntime();
  const service = new LangGraphAgentService(skillRuntime);
  const { installSolverGate } = require(path.join(benchmarkRoot, "lib", "solver-gate.cjs"));
  const solverGate = installSolverGate(service);
  const registeredTools = createRegisteredTools({
    skillRuntime,
    workspaceRoot: runConfig.workspaceRoot,
  });
  const toolByName = new Map(registeredTools.map((tool) => [tool.name, tool]));
  const enabledToolIds = Array.isArray(runConfig.enabledToolIds)
    ? runConfig.enabledToolIds
    : readToolDefinitions().map((definition) => definition.name);
  for (const toolId of enabledToolIds) {
    if (toolId !== "ask_user_clarification" && !toolByName.has(toolId)) {
      throw new Error(`StructureClaw tool is unavailable: ${toolId}`);
    }
  }
  return {
    runConfig,
    service,
    skillRuntime,
    solverGate,
    toolByName,
    enabledToolIds,
    summarizeFileImages,
    applyPublicToolStateUpdate,
  };
}

function getRuntime() {
  runtimePromise ??= initializeRuntime();
  return runtimePromise;
}

async function executeTool(name, params) {
  const runtime = await getRuntime();
  if (!runtime.enabledToolIds.includes(name)) {
    throw new Error(`Tool is not enabled in this benchmark run: ${name}`);
  }
  const state = readJson(runtime.runConfig.statePath);
  state.messages = Array.isArray(state.messages) ? state.messages : [];
  const toolCallId = `openclaw-${randomUUID()}`;
  appendAssistantToolCall(state, name, toolCallId, params);

  if (name === "ask_user_clarification") {
    const payload = {
      type: "clarification_needed",
      question: params.question,
      options: parseClarificationOptions(params.optionsJson),
    };
    const content = JSON.stringify(payload);
    appendToolResult(state, name, toolCallId, content);
    writeJsonAtomic(runtime.runConfig.statePath, state);
    return { content: [{ type: "text", text: content }], details: payload };
  }

  const tool = runtime.toolByName.get(name);
  if (!tool) throw new Error(`StructureClaw tool is unavailable: ${name}`);
  try {
    const result = await tool.invoke(params, {
      configurable: {
        skillRuntime: runtime.skillRuntime,
        engineClient: runtime.service.engineClient,
        codeCheckClient: runtime.service.codeCheckClient,
        structureProtocolClient: runtime.service.structureProtocolClient,
        workspaceRoot: runtime.runConfig.workspaceRoot,
        fileAccessAllowlist: runtime.runConfig.attachmentPaths,
        enabledToolIds: runtime.enabledToolIds,
        disabledToolIds: [],
        allowShell: false,
        maxToolCallsPerTurn: runtime.runConfig.maxToolCallsPerTurn || 32,
        skillScope: runtime.runConfig.skillIds,
        agentState: state,
        summarizeFileImages: (analysis, filePath, signal) => runtime.summarizeFileImages(
          analysis, filePath, state.locale || "zh", state.lastUserMessage || "", signal,
        ),
      },
      toolCall: { id: toolCallId },
    });
    const update = commandUpdate(result);
    applyStateUpdate(state, update, runtime.applyPublicToolStateUpdate);
    constrainSelectedSkills(state, runtime.runConfig.skillIds);
    const content = toolContent(result, update);
    if (!update?.messages) {
      appendToolResult(state, name, toolCallId, content);
    }
    const solverEvents = runtime.solverGate.snapshot();
    if (solverEvents.length > 0) {
      state._solverEvents = [
        ...(Array.isArray(state._solverEvents) ? state._solverEvents : []),
        ...solverEvents,
      ];
    }
    writeJsonAtomic(runtime.runConfig.statePath, state);
    let details;
    try {
      details = JSON.parse(content);
    } catch {
      details = { result: content };
    }
    return { content: [{ type: "text", text: content }], details };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    appendToolResult(state, name, toolCallId, JSON.stringify({ error: message }));
    const solverEvents = runtime.solverGate.snapshot();
    if (solverEvents.length > 0) {
      state._solverEvents = [
        ...(Array.isArray(state._solverEvents) ? state._solverEvents : []),
        ...solverEvents,
      ];
    }
    writeJsonAtomic(runtime.runConfig.statePath, state);
    throw error;
  }
}

function queuedToolExecution(name, params) {
  const run = toolQueue.then(
    () => executeTool(name, params),
    () => executeTool(name, params),
  );
  toolQueue = run.catch(() => undefined);
  return run;
}

export default {
  id: "structureclaw-benchmark",
  name: "StructureClaw Benchmark Tools",
  description: "Current StructureClaw engineering tools for the OpenClaw benchmark.",
  register(api) {
    for (const definition of readToolDefinitions()) {
      api.registerTool({
        ...definition,
        execute(_toolCallId, params) {
          return queuedToolExecution(definition.name, params);
        },
      });
    }
  },
};
