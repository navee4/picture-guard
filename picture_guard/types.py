from __future__ import annotations

from dataclasses import dataclass, field

OK = "ok"
NOT_SURE = "not_sure"


@dataclass
class StageResult:
    status: str  # OK or NOT_SURE; anything else is treated as an error
    answer: dict = field(default_factory=dict)
    why: str = ""


@dataclass
class Context:
    """What a stage may look at. `results` holds the answers of the stages that ran before it."""
    loaded: object  # imaging.Loaded
    in_path: str
    out_path: str
    results: dict = field(default_factory=dict)
    fail_safe: bool = False
    safe_image: object = None  # PIL image produced by black_out; checked by check_safe; written by the pipeline
    boxes: list = field(default_factory=list)  # [x0, y0, x1, y1] to fill, from locate and faces when they are sure
