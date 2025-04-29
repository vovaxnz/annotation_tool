from typing import NamedTuple


class CheckResult(NamedTuple):
    ready_to_complete: bool = True
    message: str = "No check required"
