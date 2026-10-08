"""
Secret Redactor module for ShrinkWrap.
Ensures zero credential leaks in model context, logs, or telemetry.
"""

import re

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{12,})['\"]?", r"\1: [REDACTED_SECRET]"),
    (r"sk-[a-zA-Z0-9]{20,T}", "[REDACTED_OPENAI_KEY]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"glpat-[a-zA-Z0-9\-]{20}", "[REDACTED_GITLAB_TOKEN]"),
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (r"-----BEGIN\s+(RSA|EC|PGP|OPENSSH)\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+\1\s+PRIVATE\s+KEY-----", "[REDACTED_PRIVATE_KEY]"),
]

class SecretRedactor:
    def sanitize(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized
