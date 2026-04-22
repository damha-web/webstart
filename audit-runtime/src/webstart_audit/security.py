from __future__ import annotations

import re


def mask_pii(value: str) -> str:
    """이메일, 전화번호, 주민번호, 카드번호, API 키/Bearer 토큰을 마스킹한다."""
    masked = re.sub(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "***@***.***",
        value,
    )
    masked = re.sub(r"01[0-9]-?[0-9]{3,4}-?[0-9]{4}", "***-****-****", masked)
    masked = re.sub(r"\b\d{6}-?[1-4]\d{6}\b", "******-*******", masked)
    masked = re.sub(r"\b(?:\d[ -]?){13,19}\b", "****-****-****-****", masked)
    masked = re.sub(
        r'(?i)("?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|authorization)"?\s*[:=]\s*)"[^"]+"',
        r'\1"***REDACTED***"',
        masked,
    )
    return re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+\b", "Bearer ***REDACTED***", masked)
