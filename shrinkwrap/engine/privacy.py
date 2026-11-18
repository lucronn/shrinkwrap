"""Best-effort credential redaction for tool output and buffered payloads."""

import re
from typing import Any


_SECRET_HINTS = (
    "api_key", "apikey", "secret_key", "secretkey", "access_token",
    "accesstoken", "auth_token", "authtoken", "refresh_token",
    "refreshtoken", "client_secret", "clientsecret", "private_key",
    "privatekey", "password", "authorization", "credential", "token", "bearer", "sk-",
    "ghp_", "glpat-", "akia", "-----begin",
)
_SENSITIVE_KEYS = {
    "apikey", "secretkey", "accesstoken", "authtoken", "refreshtoken",
    "clientsecret", "privatekey", "password", "authorization", "bearer",
    "credential", "credentials", "token",
}
_KEY_NORMALIZER = re.compile(r"[-_\s]")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN\s+(?:(?:RSA|EC|PGP|OPENSSH|ENCRYPTED)\s+)?PRIVATE\s+KEY-----"
    r"[\s\S]*?-----END\s+(?:(?:RSA|EC|PGP|OPENSSH|ENCRYPTED)\s+)?PRIVATE\s+KEY-----"
)
_ASSIGNMENT = re.compile(
    r"(?i)\b((?:api[_-]?key|secret[_-]?key|access[_-]?token|"
    r"auth[_-]?token|refresh[_-]?token|client[_-]?secret|"
    r"private[_-]?key|password|authorization|bearer|token)"
    r"[\"']?\s*[:=]\s*)(?:(['\"])([^'\"\n]*)\2|([A-Za-z0-9_./+=-]{8,}))"
)
_BEARER = re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+/-]{12,}")
_ASSIGNMENT_HINTS = (
    "api_key", "apikey", "secret_key", "secretkey", "access_token",
    "accesstoken", "auth_token", "authtoken", "refresh_token",
    "refreshtoken", "client_secret", "clientsecret", "private_key",
    "privatekey", "password", "authorization", "bearer", "token",
)
_KNOWN_TOKENS = (
    ("sk-", re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "[REDACTED_OPENAI_KEY]"),
    ("ghp_", re.compile(r"ghp_[A-Za-z0-9]{36,}"), "[REDACTED_GITHUB_TOKEN]"),
    ("glpat-", re.compile(r"glpat-[A-Za-z0-9_-]{20,}"), "[REDACTED_GITLAB_TOKEN]"),
    ("akia", re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
)


class SecretRedactor:
    def may_contain_secret(self, text: str) -> bool:
        lowered = text.lower()
        return any(hint in lowered for hint in _SECRET_HINTS)

    def sanitize(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        lowered = text.lower()
        if not any(hint in lowered for hint in _SECRET_HINTS):
            return text
        sanitized = _PRIVATE_KEY.sub("[REDACTED_PRIVATE_KEY]", text) if "-----begin" in lowered else text
        for marker, pattern, replacement in _KNOWN_TOKENS:
            if marker in lowered:
                sanitized = pattern.sub(replacement, sanitized)
        if "bearer" in lowered:
            sanitized = _BEARER.sub(r"\1[REDACTED_SECRET]", sanitized)

        def redact_assignment(match: re.Match) -> str:
            quote = match.group(2)
            replacement = f"{quote}[REDACTED_SECRET]{quote}" if quote else "[REDACTED_SECRET]"
            return match.group(1) + replacement

        return _ASSIGNMENT.sub(redact_assignment, sanitized) if any(hint in lowered for hint in _ASSIGNMENT_HINTS) else sanitized

    def sanitize_data(self, data: Any) -> Any:
        """Redact nested JSON values without changing unaffected data."""
        if isinstance(data, str):
            return self.sanitize(data)
        if isinstance(data, list):
            values = [self.sanitize_data(value) for value in data]
            return data if all(a is b for a, b in zip(values, data)) else values
        if isinstance(data, dict):
            values = {}
            changed = False
            for key, value in data.items():
                if isinstance(key, str) and _KEY_NORMALIZER.sub("", key).lower() in _SENSITIVE_KEYS:
                    new_value = None if value is None else "[REDACTED_SECRET]"
                else:
                    new_value = self.sanitize_data(value)
                values[key] = new_value
                changed |= new_value is not value
            return values if changed else data
        return data
