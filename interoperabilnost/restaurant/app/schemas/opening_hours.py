"""Validacija radnog vremena pri registraciji lokala."""
from datetime import time


def _parse_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) < 2:
        raise ValueError("Očekivano vreme HH:MM")
    return time(int(parts[0]), int(parts[1]))


def ensure_close_after_open(open_str: str, close_str: str, period_label: str) -> None:
    open_t = _parse_hhmm(open_str)
    close_t = _parse_hhmm(close_str)
    if close_t <= open_t:
        raise ValueError(
            f"{period_label}: kraj radnog vremena mora biti posle početka "
            f"(npr. 10:00-22:00). Rad posle ponoći trenutno nije podržan."
        )
