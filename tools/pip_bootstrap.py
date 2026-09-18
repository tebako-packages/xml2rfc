# tools/pip_bootstrap.py — run pip under the STAGED windows runtime with
# the msys2 connect workaround.
#
# WHY: the msys2-cpython build breaks urllib3's NON-BLOCKING connect
# (settimeout puts the socket in non-blocking mode; connect surfaces
# WinError 10035 / WSAEWOULDBLOCK unhandled, and every pip fetch dies).
# Blocking sockets in the same interpreter reach the same hosts fine —
# the kernel honors connect timeouts itself. This bootstrap forces
# blocking connects for pip's sockets on windows, then delegates to pip.
# It is a NO-OP on posix. The factory-level fix is tracked in
# tamatebako/tebako-runtime-python (the rootcause branch); drop this
# file when the runtime ships the fix.
#
# Usage (identical to `python -m pip …`, minus the -m):
#   <runtime.exe> tools/pip_bootstrap.py install --target …
#   <runtime.exe> tools/pip_bootstrap.py download --dest …
import socket
import sys

if sys.platform == "win32":
    _orig_connect = socket.socket.connect

    def _blocking_connect(self, address):
        try:
            self.setblocking(True)
        except OSError:
            pass
        return _orig_connect(self, address)

    socket.socket.connect = _blocking_connect
    print("pip_bootstrap: blocking-connect workaround active", file=sys.stderr)

from pip._internal.cli.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
