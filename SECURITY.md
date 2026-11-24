# Security Policy

## Scope and intended use
EmojiLens analyses adversarial Unicode and emoji transformations for **defensive** research.
It runs locally. It does not attack public AI services, extract credentials, or generate
real-world harmful payloads, and demonstrations use synthetic policies and harmless
surrogate tasks.

## Handling untrusted content
All user input, dataset content, research documents and model outputs are treated as
untrusted data. EmojiLens displays and analyses them but never executes them, and it never
follows instructions embedded in them. API error responses never echo submitted input.

## Reporting a vulnerability
Please report suspected vulnerabilities privately through GitHub's
"Report a vulnerability" (Security Advisories) on this repository rather than in a public
issue. Include reproduction steps and the affected version.

## Supported versions
Only the latest commit on `main` is supported during pre-release development.
