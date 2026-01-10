from dataclasses import dataclass
from typing import List


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    details: str | None = None


@dataclass
class ValidationResult:
    checks: List[ValidationCheck]

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    @staticmethod
    def combine(results: List["ValidationResult"]) -> "ValidationResult":
        checks: List[ValidationCheck] = []
        for r in results:
            checks.extend(r.checks)
        return ValidationResult(checks)


def run_sql_check(conn, *, name: str, sql: str, expect_zero: bool) -> ValidationResult:
    with conn.cursor() as cur:
        cur.execute(sql)
        val = cur.fetchone()[0]

    passed = (val == 0) if expect_zero else (val > 0)

    return ValidationResult(
        checks=[
            ValidationCheck(
                name=name,
                passed=passed,
                details=None if passed else f"Query returned {val}",
            )
        ]
    )
