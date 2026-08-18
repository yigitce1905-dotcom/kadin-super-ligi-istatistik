# -*- coding: utf-8 -*-
"""entegre_islenmis'i DNS IPv4 yedeğiyle çalıştırır (VPN DNS tuhaflığı)."""
import socket, sys
sys.stdout.reconfigure(encoding="utf-8")
_gai = socket.getaddrinfo
def _y(host, port, *a, **k):
    try: return _gai(host, port, *a, **k)
    except socket.gaierror:
        if isinstance(host,str) and ("google" in host):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.251.127.95", port))]
        raise
socket.getaddrinfo = _y
sys.argv=[sys.argv[0]]
import entegre_islenmis
entegre_islenmis.main()
