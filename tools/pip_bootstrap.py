# tools/pip_bootstrap.py — run pip under the STAGED windows runtime with
# the msys2 connect/select workaround.
#
# WHY: the msys2-cpython build's select() rejects socket handles whose
# value exceeds its fd limit ("Underlying socket too large for
# select()"), and every timeout-guarded IO a TLS client performs rides
# select: the non-blocking connect (WinError 10035), the SSL handshake
# wait, and timeout'd reads. Whether a given connection dies is a
# handle-value lottery — some sockets work, later ones fail, which made
# the failure look transient. Blocking sockets skip select entirely: the
# kernel honors connect/handshake/read completion itself, and the hosts
# pip talks to (pypi.org) are reachable and fast.
#
# This bootstrap forces FULLY blocking sockets for pip on windows (no
# timeouts anywhere on its sockets), then delegates to pip. Trade-off:
# a genuinely dead connection can hang a read instead of timing out —
# accepted for this CI-only workaround; the OS stack still fails a
# dead-peer connection on its own. It is a NO-OP on posix. The
# factory-level fix is tracked in tamatebako/tebako-runtime-python
# (the rootcause branch); drop this file when the runtime ships it.
#
# Usage (identical to `python -m pip …`, minus the -m):
#   <runtime.exe> tools/pip_bootstrap.py install --target …
#   <runtime.exe> tools/pip_bootstrap.py download --dest …
import socket
import sys

if sys.platform == "win32":
    _orig_connect = socket.socket.connect
    _orig_settimeout = socket.socket.settimeout

    def _settimeout(self, value):
        # Ignore every timeout request: a timeout puts the socket into
        # select-guarded mode, which is exactly what msys2 cannot do.
        # Keep the call cheap and silent — pip re-applies timeouts all
        # over its connection lifecycle.
        return None

    def _blocking_connect(self, address):
        return _orig_connect(self, address)

    socket.socket.settimeout = _settimeout
    socket.socket.connect = _blocking_connect

    import ssl

    _orig_wrap = ssl.SSLContext.wrap_socket

    def _wrap_socket(self, sock, *args, **kwargs):
        try:
            sock.settimeout(None)  # blocking handshake: no select wait
        except OSError:
            pass
        return _orig_wrap(self, sock, *args, **kwargs)

    ssl.SSLContext.wrap_socket = _wrap_socket
    print(
        "pip_bootstrap: fully-blocking-socket workaround active (msys2 select pathology)",
        file=sys.stderr,
    )

from pip._internal.cli.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
