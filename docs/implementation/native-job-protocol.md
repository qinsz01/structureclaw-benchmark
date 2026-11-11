# Isolated native numeric jobs, version 1

This broker is a transport and evidence boundary for the research-300 project.
It does not implement solver mappings, invoke the SUT runner, migrate a database,
build production code, control an existing solver session, or award native truth.
The implementation contains no enabled engine registry. All Windows deployment,
SDK mapping review, host configuration review, and actual jobs remain coordinated
by root. No remote job was needed to implement or test this protocol.

## Implemented entry points

- `lib/native-job.cjs`: `buildEnvelope`, `validateEnvelope`, `inspectEnvelope`,
  `manifestSha256`, `NativeJobClient`, `validateCollection`, and `collectEvidence`.
- `scripts/research300/native_worker.py`: `inspect` reads one envelope from stdin
  and prints a metadata-only dry-run summary. `serve --root ABS --registry ABS`
  accepts persistent JSON-lines requests for submit/status/collect/cancel/cleanup.
- `scripts/research300/native_process.py`: owned POSIX process groups and Windows
  Job Objects; only the broker creates and cancels these processes.

Python 3.10+ runs the worker without additional packages. The CommonJS client is
intended for the repository's Node 20+ runtime and was tested with Node 22.

```javascript
const {buildEnvelope, NativeJobClient, collectEvidence} = require('./lib/native-job.cjs');
// Demonstration of transport format only; table column semantics are not implied.
const envelope = buildEnvelope({engine: 'OpenSees', model: {
  format: 'native-numeric-v1',
  tables: {nodes: [[1, 0, 0, 0]], elements: [], settings: []}
}});
const dry = new NativeJobClient({transport: 'ssh'}); // dryRun defaults true
const inspection = await dry.submit(envelope);     // never starts SSH
```

For a locally deployed, reviewed driver, create a client with
`{transport:'local', dryRun:false, python:'python3', workerPath:ABS_WORKER,
root:ABS_JOB_ROOT, registry:ABS_HOST_REGISTRY}`. Keep the client session open
until collection or cancellation finishes. Shutdown sends EOF, then SIGTERM
after five seconds if needed; it reports a timeout after fifteen seconds
without force-killing a broker that may still own solver processes. `submit(envelope)` returns the
random `jobId` and bound hashes. Poll `status(jobId)`, then use
`collectEvidence({client,jobId,expected:{jobId,engine,modelSha256,manifestSha256},
destination:ABS_NEW_LOCAL_DIRECTORY,cleanup:false})`. The caller must bind
expected hashes to its original submitted envelope. Setting `cleanup:true`
performs cleanup only after local collection and revalidation. `close()` closes
the worker session and cancels any remaining owned jobs.

## Numeric envelope

The exact envelope keys are:

```json
{
  "schemaVersion": 1,
  "engine": "OpenSees",
  "modelSha256": "<lowercase SHA-256 of exact model.json bytes>",
  "files": [{
    "path": "model.json",
    "sha256": "<same lowercase SHA-256>",
    "size": 123,
    "contentBase64": "<canonical base64 of UTF-8 JSON>"
  }]
}
```

The only accepted input file is `model.json`, at most 8 MiB. Its exact shape is
`{format:"native-numeric-v1",tables:{...}}`. Table names are limited to `nodes`,
`elements`, `materials`, `sections`, `supports`, `loads`, `loadCases`,
`loadCombinations`, `settings`, and `outputRequests`; `nodes`, `elements`, and
`settings` are mandatory. Each table is an array containing only finite numbers
with absolute value at most 1e100, booleans, null, and nested arrays (depth at
most 32). Unknown keys, object-valued rows, textual labels, duplicate JSON keys,
noncanonical base64, and nonfinite numbers fail before job creation.

The independent author/compiler owns each engine's table column/code mapping.
This protocol deliberately specifies no unreviewed engineering mapping. Numeric
entity/selection IDs are assigned locally. Case IDs, prompts, attachments,
expected answers, tolerances, scoring instructions, author identity, and local
case paths stay in a caller-side association map on the authorized team NAS.
No Tcl, Python, executable bytes, arbitrary native binaries, command arguments,
working directories, or shell commands are accepted in the input envelope.
Numeric-only syntax is a transport guard, not proof that an author has preserved
engineering semantics or excluded every possible encoded side channel.

`modelSha256` hashes the exact transmitted bytes. `manifestSha256` hashes the
compact recursively key-sorted JSON envelope after dropping `contentBase64`
from file entries. Canonical metadata contains only strings, booleans, null,
and integer sizes/codes, avoiding cross-runtime float formatting ambiguity.
Hashes detect changes; they are not signatures against a compromised worker.

## Wire requests and lifecycle

A session request is one UTF-8 JSON line with exact keys:

- Submit: `{schemaVersion:1,requestId:1,op:"submit",payload:ENVELOPE}`.
- Status/collect/cancel: `{schemaVersion:1,requestId:2,op:"status",jobId:HEX32}`.
- Cleanup: `{schemaVersion:1,requestId:3,op:"cleanup",jobId:HEX32,receiptSha256:HEX64}`.

Request IDs are positive safe integers, unique within a session. There is no
automatic submit retry after a timeout. Every job ID is a new random UUID hex
value, never a case ID or a deterministic model hash. Responses carry
`{schemaVersion:1,requestId,ok:true,result}` or
`{schemaVersion:1,requestId,ok:false,error:{code,message}}`. Error messages do not
include raw payloads, credentials, or native process stderr. Framing is capped
at 48 MiB; artifact data is capped at 32 MiB total.

Admission validates all input bytes, the reviewed engine registry, the pinned
driver hash, and the host isolation lease. An atomic per-engine directory lock
then admits exactly one job across broker sessions sharing that root. Jobs use
`JOB_ROOT/<random jobId>` and fixed input/output names. A pinned driver receives
exactly `--input model.json --output result.json`, with `shell=False`, a private
working directory, and an explicit minimal environment. User profiles and temp
paths point inside the job; SSH/API credentials are not inherited. These path
settings alone do not sandbox arbitrary solver behavior: independent driver
review must establish that global configuration and shared live sessions are
untouched before enabling a registry entry.

States are `running`, `succeeded`, `failed`, and `cancelled`. `resource-busy`
means an unavailable/unreviewed engine, absent/expired isolation lease, held
engine lock, or an orphaned job whose process is not owned by the session.
A successfully launched driver sets `executed:true`; it does not independently
prove that the intended solver executed correctly. Driver exit zero plus a
`result.json` is transport success only. Missing results or failed sealing
cannot produce a successful collected receipt.

The launching session retains actual process ownership. Another session can
read terminal evidence but cannot cancel a running job by PID. Session EOF,
normal close, SIGTERM, and SIGINT cancel owned jobs. POSIX uses a new process
group and retains the initial process until descendants are cancelled, avoiding
PID/group reuse. POSIX drivers must not daemonize, call setsid, or deliberately
escape that group; this is not a hostile-executable sandbox. A force-killed
POSIX broker can leave an orphan, so its lock remains for operator inspection
and is never automatically reclaimed using a PID. Windows launches suspended,
assigns a kill-on-close Job Object before resume, and restricts inherited
handles to standard I/O. Unsupported containment fails closed. Windows code is
implemented but requires an authorized Windows validation run; Linux tests do
not establish Windows behavior.

## Host-owned registry and isolation lease

Registry files are installed by the coordinator, never supplied in a job.
Only three fixed executable basenames are recognized: `native-opensees-worker`,
`native-yjk-worker`, `native-pkpm-worker`, optionally with `.exe` on Windows.
These are independently reviewed standalone drivers, not the production runner
or an arbitrary interpreter. Their absolute paths and SHA-256 hashes are
host-owned. No such drivers are fabricated or deployed by this implementation.

Example registry shape, deliberately disabled:

```json
{
  "schemaVersion": 1,
  "engines": {
    "YJK": {
      "enabled": false,
      "executable": "G:/StructureClaw-NativeJobs/bin/native-yjk-worker.exe",
      "sha256": "<reviewed driver SHA-256>",
      "independentCompilerReviewed": false,
      "isolationVerified": false,
      "isolationLease": "G:/StructureClaw-NativeJobs/leases/yjk.json"
    }
  }
}
```

All three flags must be true. The host-only lease must contain exactly
`{schemaVersion:1,engine,executableSha256,isolated:true,expiresAt:UNIX_SECONDS}`;
expiry must be in the future and no more than 300 seconds away at admission.
The coordinator must issue a lease only after determining that the configured
driver, per-job paths, global settings, and active native applications permit
isolation. The broker does not itself detect every commercial SDK singleton or
shared global database. There is no automatic lease issuer or bypass. A live
YJK session precludes a YJK lease unless independent isolation is demonstrated.
A lease is an admission decision; the per-engine lock lasts through termination
and sealing. All cooperating brokers for an engine must use the same job root.

The job root must be outside `G:/StructureClaw-All/structureclaw` and
`G:/StructureClaw-All/sclaw_data`; these protected roots are explicitly rejected.
Other read-only data may be used only by a separately reviewed driver with a
known contract. Existing development modifications are never inspected or
changed by the broker.

## SSH transport and dry-run boundary

The client builds this fixed transport argument vector without a shell:

```text
ssh -o BatchMode=yes -T -J codex_qsz <native-worker>
  "python G:/StructureClaw-NativeJobs/native_worker.py serve --root G:/StructureClaw-NativeJobs/jobs --registry G:/StructureClaw-NativeJobs/registry.json"
```

This encodes `codex_qsz` as an SSH jump alias. Root must confirm that alias is the
approved route (rather than an identity/account requiring different routing)
and confirm Python/deployment paths before actual use. No host configuration
or credential material is copied or logged. SSH runs only with explicit
`dryRun:false, allowRemote:true`; dry-run inspection never opens a process.
This implementation does not authorize deployment or actual Windows jobs.
There is no remote LLM/OpenClaw transport or production-runner fallback.

## Receipts, collection, and cleanup

After the driver and owned descendants have stopped, the worker seals a receipt:
`{schemaVersion:1,jobId,engine,manifestSha256,modelSha256,state,executed,exitCode,
executableSha256,artifacts:[{path,sha256,size}],
nativeTruthStatus:"pending-independent-review"}`. `receiptSha256` hashes its
canonical bytes. Required artifacts are `model.json`, `stdout.log`, and
`stderr.log`, plus `result.json` for successful jobs. Optional fixed evidence
names are `native-input.dat`, `native-output.dat`, `settings.json`, and
`solver-version.json`. Drivers should preserve runnable native input, raw native
output, settings/readback, and exact solver version under these names, and may
pack additional native files into the opaque `.dat` artifacts without asking
the broker to unpack them. Extra generated files block cleanup and require
operator inspection. The broker does not parse raw result bytes as truth.

Collect returns the receipt, its hash, and the exact artifact set with base64
bytes. Worker collection rechecks the sealed input/manifest/artifact hashes.
The local collector binds the receipt to the caller's original job, model,
manifest, and engine, checks the exact artifact set, sizes, hashes, and numeric
input again, and writes a new private evidence directory atomically. It rereads
local bytes before requesting cleanup. Traversal, absolute artifact names,
duplicates, symlinks/reparse points, and replaced artifacts fail. Cleanup
requires the verified receipt hash and removes only the exact known job files;
it never searches other roots or deletes another process's working directory.
No cleanup happens automatically on collect or on failed validation.

Native references still require an independent author/compiler, source and
engineering review, requested selection/station/unit coverage, solver version
and settings verification, and an independent correctness check. A raw receipt
alone never grants native acceptance or changes the reference truth status.

## Tests and remaining integration limits

```text
python3 scripts/research300/native_worker_test.py -v
python3 scripts/research300/native_process_test.py -v
node --test lib/native-job.test.cjs
# In a sandbox that blocks Node test-worker spawning (Node 22):
node --experimental-test-isolation=none --test lib/native-job.test.cjs
```

Tests use temporary local numeric fixtures and harmless fake drivers. They cover
strict input rejection, random identities, per-engine exclusion, owned process
tree cancellation, unrelated-process survival, orphan handling, hash changes,
replaced paths, stale evidence, metadata-only inspection, and local transport.
Windows-only tests explicitly skip on Linux. No actual OpenSees, YJK, or PKPM
result is claimed, no SDK mapping is inferred, and no paid evaluation occurs.
Root must supply the reviewed compiler/driver and host isolation evidence,
validate the SSH route/deployment and Windows process behavior, then coordinate
actual numerical jobs separately.
