# Superseded commercial diagnostic evidence

These are the original bytes from commit `0be6a26`, before the uniform
`commercial-linear-static-v2` authoring revision. They are historical diagnostics,
not current scoring answers or independently accepted commercial-engine truth.

The archive contains all 33 cases' old matrix/OpenSees diagnostic outputs and
receipts, plus every existing contract, prompt or public appendix that the
revision changes. The manifest records each original active path, SHA-256 and
byte count, and maps the old source hash to its replacement. No old result was
relabeled as a finite-shear result.

Unchanged numerical model states, requests, tolerances, drawings and other
public inputs stay in the corresponding active case. Their hashes appear in
each archived source manifest. To reconstruct an old case in a scratch directory,
copy the files named by that manifest from the active case, overlay the archived
case files, then verify every source-manifest hash. Alternatively extract the
case directly from the recorded Git revision. Never run a historical diagnostic
against the revised public contract and call it current validation.

The 22 original STD/INT authored contracts chose Euler–Bernoulli bending; the
11 MM contracts left bending theory unspecified. Their matrix and OpenSees
diagnostics all used Euler–Bernoulli. The source plan itself did not prescribe
that choice. The new revision explicitly prescribes finite shear in public,
before any candidate-agent trial, without changing the numeric input files or
frozen output tolerances. See the current commercial-calibration documentation
and the revision manifest for the replacement's scope and remaining gates.
