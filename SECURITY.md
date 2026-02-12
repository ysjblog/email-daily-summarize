# Security Policy

## Supported Security Baseline
- Secrets must be stored outside the repository at `~/.config/daily-summarize/secrets.env`.
- Secrets file permission must be `600`.
- External channels (Slack/LINE) should use redacted digest (`digest.redaction_mode: strict`).

## Token Rotation Recommendations
- Rotate Gmail refresh tokens, Slack bot token, and LINE channel token every 90 days.
- Rotate immediately after any suspected exposure.

## Incident Response (within 30 minutes)
1. Revoke exposed tokens from provider consoles.
2. Issue fresh tokens and update `~/.config/daily-summarize/secrets.env`.
3. Re-run `bash scripts/quickstart.sh` to verify configuration.
4. Review recent report and notifier logs for suspicious delivery.

## Reporting a Vulnerability
Please open a private security report with:
- Impact summary
- Reproduction steps
- Suggested fix
