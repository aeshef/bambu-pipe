# Security Policy

`bambu-pipe` controls local printer transport and handles secrets such as printer
access codes and provider API keys. Please report security issues privately.

## Supported Versions

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
- `.env`, printer access codes, generated files, databases, and caches must stay out of git.
- REST uploads intentionally reject arbitrary server-local file paths.
- Printer control is LAN / Developer Mode only.
