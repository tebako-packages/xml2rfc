# xml2rfc feedstock

Feedstock for **xml2rfc** — the IETF RFC/XML authoring renderer, packaged
as a tebako `kind: app` payload. The first python payload of the v2
ecosystem (TODO.python/03); kills the host-python convention behind
metanorma's ietf flavor path (PROGRESS/25's chocolatey python313 saga).

**Status: build machinery proven locally end-to-end on aarch64-macos
(stage → closure → build → both spec-26 checks green → dispatcher proof:
file:// registry install + jailed shim render).** Not yet pushed; the org
repo `tebako-packages/xml2rfc` is created at first push (git+ssh — the
org blocks contents-API PUT).

## Locked design decisions (2026-09-05)

1. **Per-triplet, never universal.** The closure carries lxml (C
   extension; manylinux/musllinux/macOS wheels) plus markupsafe/pyyaml
   optional C speedups. The audit correction to TODO.python/03 item 1
   stands: universality was wrong for this payload.
2. **ABI-line runtime edge.** Every entrypoint's `runtime_requirement` is
   `engine: python, constraint: ~> 3.13.0, abi: <staging platform tag>` —
   spec 05 §5's native-extension law (wrong line = named error, never a
   segfault). The abi string flows VERBATIM from the runtime package's
   own `.abi` sidecar (e.g. `cpython-313-darwin.so` — suffix included,
   the factory is the single owner; tools/build fails named when the
   sidecar is absent/empty). Upstream's pure-language range
   (`requires_python >= 3.10`, tested through 3.13) is documented in
   `recipe.yml`, not used as the edge constraint. The staging/exec line
   is python **3.13.15** (the factory's `tidy` — "the xml2rfc driving
   line").
3. **pipstage build.** `tools/build` stages the pinned PyPI closure with
   `pip install --target` run by a tebako python runtime's OWN interpreter
   (dogfood) — never the runner's python, never the user's machine. The
   locked closure (`closure/<version>-<triplet>.txt`, hashes included) is
   generated per triplet (metanorma's gen_closure pattern). The imager is
   **`tfs mkimage`** (default limnifs — the format the runtime factory
   itself ships); tebako-pkg v2.2.0 is trailer surgery only, so the
   "press" step of the ruby feedstocks has no instance here.
4. **Release channel.** tebako-runtime-python **v0.1.0 is live** (the
   owner's publish decision landed 2026-09-06). Staging + CI test legs
   consume the pinned factory RELEASE — `tools/stage_runtime`'s release
   channel downloads the pinned tag's assets for the pinned python line
   (every staged byte verified four ways: per-asset `.sha256` sidecar ↔
   manifest shard ↔ monolith `manifest.json` ↔ `SHA256SUMS.txt`) and
   lays them into a `file://` runtime MIRROR (spec 05 §2's download-base
   shape); resolution rides `TEBAKO_RUNTIME_MIRROR` + the config.yaml
   `runtimes:` pin (spec 04 §2's `kind: runtime` registry entries remain
   PLANNED in v2.2.0 — TODO.v2-1/30). The pin is `recipe.yml`'s
   `build.runtime` block (`channel: release` + `release:` tag). The
   pre-publish `run-artifacts` channel remains selectable by env
   override for pre-publish factory proof builds ONLY — workflow run
   artifacts are NOT a durable registry (retention-days: 1) and no
   release line ever references them.
5. **Spec 32 spawn form.** The console script dispatches through the
   provider's own spec-17 dispatch (tebako v2.2.0, NORMATIVE) — no
   host-tier exe materialization, no POSIX-only shell shim. The in-image
   `/bin/xml2rfc` stub derives site-packages from its OWN location (the
   mount point is the dispatcher's choice), then installs the lxml VFS
   compat layer (deviation A below) before importing xml2rfc.
6. **Platforms = the factory's POSIX six.** x86_64/aarch64 ×
   linux-gnu/linux-musl/macos. Windows is TODO.python/05's descoped row;
   this feedstock gains `x86_64-windows-ucrt` with 05, and metanorma's
   ietf DEPENDS keeps windows on its current path until then (recorded
   in the DEPENDS PR body).
7. **Payload checks (spec 26).** `version` (exit 0) + `render-txt`
   (fixture mini.xml → mini.txt), carried in the manifest.

## Deviations (each with its owner and removal condition)

A. **lxml VFS compat layer (`templates/lib/python/site-packages/tebako_lxml_vfs.py`).**
   libxml2 ≥ 2.13 loads file-path sources through its fd-based input
   layer (`xmlIO.c xmlInputFromFd`), which `dup(2)`s the descriptor it
   was handed. libtfs-preload (tebako v2.2.0) interposes
   open/read/lseek/close but NOT `dup`, so a memfs fd (TEBAKO_FD_FLAG)
   fails `dup` with EBADF and every `lxml.etree.{parse,ElementTree,
   RelaxNG,XMLSchema}` of an in-image path died "Bad file descriptor"
   before any read (pinned by disassembly of the wheel's
   `xmlInputFromFd`: `dup` → -1 → `_xmlIOErr(errno)`; dyld's interpose
   log proves `read`/`open`/`fopen` WERE interposed in the dlopen'd
   wheel). The layer routes file-path loads through python's own
   (interposed) IO — parse/ElementTree get streams with base_url
   preserved; RelaxNG/XMLSchema grammars are materialized WITH their
   transitive `<include>`/`<externalRef>` closure to a host temp dir and
   compiled from there, because libxml2 resolves schema includes through
   its own global input callbacks (no lxml hook). Authored payload
   content, not an upstream patch. **Owner: the product —
   libtfs-preload needs a `dup`/`dup2` interpose + a tfs-engine fd clone
   (tebako repo). Remove this layer when the runtime line carrying that
   fix is the feedstock's floor.**

## Layout (tebako-packages/index `templates/feedstock/` + conventions)

- `recipe.yml` — upstream pin, pipstage runtime block, native members,
  platforms, the tools sha256 pin block, the ci host/container pins.
- `manifests/payload.yaml` — the spec 03 manifest template (`@@…@@`
  filled by tools/build).
- `fixtures/check/render-txt/mini.xml` — the render check's document.
- `closure/` — generated locked closures per (version × triplet).
- `templates/` — the payload's own authored content: `bin/xml2rfc` (the
  spec-32 console stub) + `lib/python/site-packages/tebako_lxml_vfs.py`
  (deviation A).
- `tools/` — pins.rb (recipe → CI env/matrix/payload-args) /
  stage_runtime / gen_closure / build / boot_smoke.
- `.github/workflows/build-payload.yml` — plan (matrix from the recipe)
  → six per-triplet legs (musl legs docker-run the digest-pinned
  tpkg-builder image per step; gnu legs host-native; macos runner-native)
  → the release job (gated: owner dispatch with `publish: true` on a tag
  ref — NEVER automatic).
- `tpkg-registry.yaml` — this package's registry, published at the
  default-branch root per the conventions; filled at first release.
