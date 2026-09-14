# xml2rfc feedstock

Feedstock for **xml2rfc** — the IETF RFC/XML authoring renderer, packaged
as a tebako `kind: app` payload. The first python payload of the v2
ecosystem, and the hermetic answer for metanorma's ietf flavor path: no
host python needed anywhere.

**Status: live.** Releases (`3.34.0` and up) publish the per-triplet
payload images with `SHA256SUMS`, and this repo's `tpkg-registry.yaml`
serves resolution.

## Design decisions

1. **Per-triplet, never universal.** The closure carries lxml (C
   extension; manylinux/musllinux/macOS wheels) plus markupsafe/pyyaml
   optional C speedups — a universal image cannot serve that matrix.
2. **ABI-line runtime edge.** Every entrypoint's `runtime_requirement` is
   `engine: python, constraint: ~> 3.14.0, abi: <staging platform tag>` —
   spec 05 §5's native-extension law (wrong line = named error, never a
   segfault). The abi string flows VERBATIM from the runtime package's
   own `.abi` sidecar (e.g. `cpython-314-darwin.so` — suffix included,
   the factory is the single owner; tools/build fails named when the
   sidecar is absent/empty). Upstream's pure-language range
   (`requires_python >= 3.10`, classifiers covering 3.14) is documented
   in `recipe.yml`, not used as the edge constraint. The staging/exec
   line is python **3.14.7** — the one line every leg rides, so the ABI
   edge stays uniform when the windows leg lands (the factory's
   windows-ucrt64 runtime exists only on the 3.14 line; the source
   factory ships no 3.13 windows-msys asset).
3. **pipstage build.** `tools/build` stages the pinned PyPI closure with
   `pip install --target` run by a tebako python runtime's OWN interpreter
   (dogfood) — never the runner's python, never the user's machine. The
   locked closure (`closure/<version>-<triplet>.txt`, hashes included) is
   generated per triplet (metanorma's gen_closure pattern). The imager is
   **`tfs mkimage`** (default limnifs — the format the runtime factory
   itself ships); tebako-pkg v2.2.0 is trailer surgery only, so the
   "press" step of the ruby feedstocks has no instance here.
4. **Release channel (the factory's shard model).** Staging + CI test
   legs consume the pinned tebako-runtime-python RELEASE —
   `tools/stage_runtime`'s release channel enumerates the pinned tag's
   per-package manifest shards (`gh release view --json assets`), fetches
   the assets each shard names (exe + env image + the windows `.dll`
   facet, each with its `.sha256` sidecar), verifies every staged byte
   three ways (sidecar ↔ staged bytes ↔ the shard's own digest fields +
   the filename identity), and derives the TRIMMED `manifest.json` +
   `SHA256SUMS.txt` consumer-side into a `file://` runtime MIRROR (spec
   05 §2's download-base shape) — a partial mirror never advertises bytes
   it does not carry. Resolution rides `TEBAKO_RUNTIME_MIRROR` + the
   config.yaml `runtimes:` pin (spec 04 §2's `kind: runtime` registry
   entries remain planned). The pin is `recipe.yml`'s `build.runtime`
   block (`channel: release` + `release:` tag). The `run-artifacts`
   channel remains selectable by env override for pre-publish factory
   proof builds ONLY — workflow run artifacts are NOT a durable registry
   (retention-days: 1) and no release line ever references them.
5. **Spec 32 spawn form.** The console script dispatches through the
   provider's own spec-17 dispatch (tebako v2.2.0, NORMATIVE) — no
   host-tier exe materialization, no POSIX-only shell shim. The in-image
   `/bin/xml2rfc` stub derives site-packages from its OWN location (the
   mount point is the dispatcher's choice), then installs the lxml VFS
   compat layer (deviation A below) before importing xml2rfc.
6. **Platforms = the factory's POSIX six.** x86_64/aarch64 ×
   linux-gnu/linux-musl/macos. The windows-ucrt leg waits on the
   factory: the windows python runtime has no mount tier yet (its fs TU
   answers any mount with a named exit 69 — the factory README's windows
   boundary), so a windows payload could not execute on its own platform
   until then. Metanorma's ietf DEPENDS keeps windows on its current path
   in the meantime.
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
