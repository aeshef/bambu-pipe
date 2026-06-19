# Security Policy

`bambu-pipe` controls local printer transport and handles secrets such as printer
access codes and provider API keys. Please report security issues privately.

## Supported Versions

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Older releases | Best effort |

Security fixes target the latest release on `main`.

## Reporting A Vulnerability

Please do not open a public issue for vulnerabilities.

Use GitHub's private vulnerability reporting if available, or contact the
maintainer through the repository owner profile. Include:

- affected version or commit;
- operating system;
- whether the issue touches printer LAN access, FTPS/MQTT, file uploads, or API keys;
- minimal reproduction steps;
- impact and any known workaround.

## Security Boundaries

- The REST adapter is local-first and should not be exposed directly to the public internet.
- Set `BAMBU_PIPE_API_TOKEN` before binding the REST adapter beyond loopback.
- `.env`, printer access codes, generated files, databases, and caches must stay out of git.
- REST uploads intentionally reject arbitrary server-local file paths.
- Printer control is LAN / Developer Mode only.
- Printer FTPS/MQTT uses the printer's LAN certificate behavior and treats the local network as
  the trust boundary. Do not run this on an untrusted network.

## Response Expectations

The maintainer will try to acknowledge private vulnerability reports within a
reasonable best-effort window. Please include enough detail to reproduce the
issue without exposing printer access codes or provider API keys.
