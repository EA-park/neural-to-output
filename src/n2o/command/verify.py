from __future__ import annotations

from dataclasses import dataclass

from .config import CommandConfig


@dataclass(slots=True)
class BoundaryCheck:
    upstream: str
    upstream_spec: dict | None
    downstream: str
    downstream_spec: dict | None
    status: str  # "match" | "mismatch" | "unknown"


_STATUS_LABEL = {"match": "OK", "mismatch": "MISMATCH", "unknown": "미정"}


def _compare(upstream_spec: dict | None, downstream_spec: dict | None) -> str:
    if upstream_spec is None or downstream_spec is None:
        return "unknown"
    return "match" if upstream_spec == downstream_spec else "mismatch"


def _spec_text(spec: dict | None) -> str:
    return "(미정)" if spec is None else ", ".join(f"{k}={v}" for k, v in spec.items())


def _check(
    upstream: str, upstream_spec, downstream: str, downstream_spec
) -> BoundaryCheck:
    return BoundaryCheck(
        upstream,
        upstream_spec,
        downstream,
        downstream_spec,
        _compare(upstream_spec, downstream_spec),
    )


@dataclass(slots=True)
class VerificationReport:
    checks: list[BoundaryCheck]

    @property
    def ok(self) -> bool:
        """True only if every boundary is a confirmed match — "미정" does not count as ok."""
        return all(check.status == "match" for check in self.checks)

    @property
    def has_mismatch(self) -> bool:
        return any(check.status == "mismatch" for check in self.checks)

    def __str__(self) -> str:
        return format_table(self.checks)

    def _repr_html_(self) -> str:
        return format_html(self.checks)


def format_table(checks: list[BoundaryCheck]) -> str:
    headers = ["단계", "출력 스펙", "", "단계", "입력 스펙", "상태"]
    rows = [
        [
            c.upstream,
            _spec_text(c.upstream_spec),
            "->",
            c.downstream,
            _spec_text(c.downstream_spec),
            _STATUS_LABEL[c.status],
        ]
        for c in checks
    ]
    widths = (
        [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
        if rows
        else [len(h) for h in headers]
    )

    def fmt_row(cols: list[str]) -> str:
        return " | ".join(col.ljust(width) for col, width in zip(cols, widths))

    lines = [fmt_row(headers), "-+-".join("-" * width for width in widths)]
    lines.extend(fmt_row(row) for row in rows)
    return "\n".join(lines)


def format_html(checks: list[BoundaryCheck]) -> str:
    color = {"match": "#2e7d32", "mismatch": "#c62828", "unknown": "#9e9e9e"}
    rows_html = "".join(
        f"<tr><td>{c.upstream}</td><td><code>{_spec_text(c.upstream_spec)}</code></td>"
        f"<td>&rarr;</td><td>{c.downstream}</td><td><code>{_spec_text(c.downstream_spec)}</code></td>"
        f"<td style='color:{color[c.status]};font-weight:600'>{_STATUS_LABEL[c.status]}</td></tr>"
        for c in checks
    )
    header = "<tr><th>단계</th><th>출력 스펙</th><th></th><th>단계</th><th>입력 스펙</th><th>상태</th></tr>"
    return f"<table><thead>{header}</thead><tbody>{rows_html}</tbody></table>"


def verify(n2o, *, command_config: CommandConfig | None = None) -> VerificationReport:
    """Check the declared input/output specs across every pipeline boundary before `n2o.run()`.

    Walks signal -> decoder -> command -> robot.arm/hand. `command_config` is optional
    since the command stage has no dedicated class of its own; pass a `CommandConfig`
    once you've decided its contract, or leave it out to see both neighboring boundaries
    reported as "미정".
    """
    cfg = command_config or CommandConfig()
    checks = [
        _check(
            "signal",
            getattr(n2o.signal, "output_spec", None),
            "decoder",
            getattr(n2o.decoder, "input_spec", None),
        ),
        _check(
            "decoder",
            getattr(n2o.decoder, "output_spec", None),
            "command",
            cfg.input_feature,
        ),
        _check(
            "command",
            cfg.output_feature,
            "robot.arm",
            getattr(n2o.robot.arm, "input_spec", None),
        ),
        _check(
            "command",
            cfg.output_feature,
            "robot.hand",
            getattr(n2o.robot.hand, "input_spec", None),
        ),
    ]
    return VerificationReport(checks)
