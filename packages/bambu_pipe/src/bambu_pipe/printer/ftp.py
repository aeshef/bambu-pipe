"""FTPS upload transport for Bambu LAN printers."""

from __future__ import annotations

import ftplib
import ssl
from pathlib import Path


class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """Implicit FTPS client with TLS session reuse for Bambu printers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wrapped_sock = None

    @property
    def sock(self):  # noqa: ANN201
        return self._wrapped_sock

    @sock.setter
    def sock(self, value):  # noqa: ANN001
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._wrapped_sock = value

    def ntransfercmd(self, cmd: str, rest: int | None = None):  # noqa: ANN201
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn,
                server_hostname=self.host,
                session=self.sock.session,
            )
        return conn, size

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):  # noqa: ANN001, ANN201
        """Store a binary file without waiting on SSL unwrap, which can hang on Bambu."""
        self.voidcmd("TYPE I")
        conn = self.transfercmd(cmd, rest)
        try:
            while True:
                buf = fp.read(blocksize)
                if not buf:
                    break
                conn.sendall(buf)
                if callback:
                    callback(buf)
        finally:
            conn.close()
        return self.voidresp()


def upload_ftps(printer_ip: str, access_code: str, local_path: Path) -> str:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    ftp = ImplicitFTP_TLS(context=context)
    ftp.connect(printer_ip, 990, timeout=30)
    ftp.login("bblp", access_code)
    ftp.prot_p()

    filename = local_path.name
    remote_path = f"/{filename}"

    with local_path.open("rb") as handle:
        ftp.storbinary(f"STOR {remote_path}", handle)
    ftp.quit()
    return filename
