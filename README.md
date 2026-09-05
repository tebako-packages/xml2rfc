# xml2rfc feedstock

Feedstock for **xml2rfc** — the IETF RFC/XML authoring renderer, packaged
as a tebako `kind: app` payload. The first python payload of the v2
ecosystem (TODO.python/03); kills the host-python convention behind
metanorma's ietf flavor path (PROGRESS/25's chocolatey python313 saga).

**Status: SKELETON — authored shape locked, build machinery (tools/,
workflows) lands next.** Not yet pushed; the org repo
`tebako-packages/xml2rfc` is created at first push (git+ssh — the org
blocks contents-API PUT).

## Locked design decisions (2026-09-05)

1. **Per-triplet, never universal.** The closure carries lxml (C
   extension; manylinux/musllinux/macOS wheels) plus markupsafe/pyyaml
   optional C speedups. The audit correction to TODO.python/03 item 1
   stands: universality was wrong for this payload.
2. **ABI-line runtime edge.** Every entrypoint's `runtime_requirement` is
   `engine: python, constraint: ~> 3.13.0, abi: <staging platform tag>` —
   spec 05 §5's native-extension law (wrong line = named error, never a
   segfault). Upstream's pure-language range (`requires_python >= 3.10`,
   tested through 3.13) is documented in `recipe.yml`, not used as the
   edge constraint. The staging/exec line is python **3.13.15** (the
   factory's `tidy` — "the xml2rfc driving line").
3. **pipstage build.** `tools/build` stages the pinned PyPI closure with
   `pip install --target` run by a tebako python runtime's OWN interpreter
   (dogfood) — never the runner's python, never the user's machine. The
   locked closure (`closure/<version>-<triplet>.txt`, hashes included) is
   generated per triplet (metanorma's gen_closure pattern).
4. **Pre-publish channel.** tebako-runtime-python publishes nothing until
   this chain proves (its AGENTS.md; the first publish is the owner's
   explicit act). Staging + CI test legs therefore consume a same-day
   factory build — `publish.yml` with `publish=false` leaves
   `runtime-packages-*` run artifacts (retention-days: 1) — laid into a
   `file://` registry (spec 04 §2) by `tools/stage_runtime`. The
   `channel: run-artifacts` block in `recipe.yml` becomes a release pin
   at the owner's publish decision; the file:// path stays as the
   offline-test mode. Workflow run artifacts are NOT a durable registry
   — no release line ever references them.
5. **Spec 32 spawn form.** The console script dispatches through the
   provider's own spec-17 dispatch (tebako v2.2.0, NORMATIVE) — no
   host-tier exe materialization, no POSIX-only shell shim.
6. **Platforms = the factory's POSIX six.** x86_64/aarch64 ×
   linux-gnu/linux-musl/macos. Windows is TODO.python/05's descoped row;
   this feedstock gains `x86_64-windows-ucrt` with 05, and metanorma's
   ietf DEPENDS keeps windows on its current path until then (recorded
   in the DEPENDS PR body).
7. **Payload checks (spec 26).** `version` (exit 0) + `render-txt`
   (fixture mini.xml → mini.txt), carried in the manifest.

## Layout (tebako-packages/index `templates/feedstock/` + conventions)

- `recipe.yml` — upstream pin, pipstage runtime block, native members,
  platforms.
- `manifests/payload.yaml` — the spec 03 manifest template (`@@…@@`
  filled by tools/build).
- `fixtures/check/render-txt/mini.xml` — the render check's document.
- `closure/` — generated locked closures per (version × triplet).
- `tools/` — build / stage_runtime / gen_closure / boot_smoke / publish
  (land with the CI PR).
- `.github/workflows/build-payload.yml` — per-triplet legs + the payload
  check + release (lands with the CI PR).
- `tpkg-registry.yaml` — this package's registry, published at the
  default-branch root per the conventions; filled at first release.
