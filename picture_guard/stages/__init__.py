"""One small module per stage of the one-page design. Each has NAME and run(ctx) -> StageResult.

Day 1: read, decide, locate, faces, count_check and check_safe are stubs that answer "not sure".
black_out and send are real (send records what it would send and makes no network call).
"""
from picture_guard.stages import black_out, check_safe, count_check, decide, faces, locate, read, send  # noqa: F401
