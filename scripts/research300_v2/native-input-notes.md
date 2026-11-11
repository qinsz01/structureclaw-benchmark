# Native building input conventions

These generic conventions describe the pinned building adapters. They supply
no task-specific geometry or expected results. Use the issued task facts and
the public schema to build your own model; the numeric broker does not repair it.

For YJK, declare `stories` explicitly. Each natural story has a unique `id`, a
base `elevation` in metres, a positive `height` in metres and the issued
`rigid_diaphragm` setting. Stories are contiguous from global Z=0. With a bare
frame and `rigid_floor:false`, bookkeeping must not introduce a diaphragm,
floor loads or any new member/restraint.

A sloping roof may belong to one natural story while its nodes have different
physical Z coordinates. Do not invent a new floor at every roof-node elevation.
The native compiler preserves each node's actual Z as an offset from its
assigned natural-story top. One natural story can assign all elevated nodes
without individual `node.story` fields. In multiple stories, use explicit
membership where elevation alone is ambiguous. Base nodes at Z=0 have no
elevated-story membership. Beams join nodes on the same natural floor;
columns connect adjacent natural floors from bottom to top.

Choosing a nominal story top does not authorize moving the actual nodes.
For a bare roof frame, nominal grouping that leaves all coordinates, members,
supports, active properties, loads and controls unchanged is inactive
bookkeeping. The evaluator checks the actual executed physics. It also accepts
qualified continuous member subdivisions; adding a joint must not add a support,
release, rigid arm or duplicated load.

Native building geometry is represented on an integer millimetre grid. Provide
physical coordinates that are exactly representable at that resolution. This
does not change the schema's metre units for node coordinates. Schema shape
dimensions such as rectangular `B`/`H` use their declared millimetre units;
numerical elastic properties use their schema units. Do not infer units from
the magnitude of a number.

The interface supports the declared bare beam/column building subset, not
every feature available in the commercial products. Read structured capability
errors and correct an equivalent input representation when appropriate; do not
change the problem's mechanics to get a successful status. A failed attempt
does not supply a reference answer or make an unsupported physical change valid.
