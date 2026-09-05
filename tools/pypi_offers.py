# tools/pypi_offers.py <member...> <xml2rfc-version> — the fail-closed
# half of tools/gen_closure: when pip's foreign-platform resolution finds
# no installable wheel, report what PyPI actually OFFERS for each native
# member (every release file of the newest release: filename + tags), so
# the missing-tag class is diagnosed, not guessed.
#
# Runs under the STAGED tebako python runtime's own interpreter (never
# the runner's python). stdlib only; trust roots ride pip's vendored
# certifi (the env image carries no CA bundle — POSIX ssl rides the
# host's /etc/ssl, which a bare musl container lacks).
import json
import ssl
import sys
import urllib.request

try:
    from pip._vendor import certifi  # the staged pip's vendored CA bundle
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover — the host bundle fallback
    CTX = ssl.create_default_context()


def offers(project):
    url = f"https://pypi.org/pypi/{project}/json"
    with urllib.request.urlopen(url, context=CTX) as r:
        doc = json.load(r)
    version = doc["info"]["version"]
    files = doc["releases"].get(version, [])
    lines = [f"  {project} {version} (newest) offers:"]
    for f in files:
        lines.append(f"    {f['filename']}")
    if not files:
        lines.append("    (no files)")
    return lines


def main():
    *members, _version = sys.argv[1:]
    out = ["PyPI native-member offers (the wheel-tag audit):"]
    for m in members:
        out += offers(m)
    print("\n".join(out), file=sys.stderr)


if __name__ == "__main__":
    main()
