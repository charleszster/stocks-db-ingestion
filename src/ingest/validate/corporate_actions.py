from src.ingest.validate_base import ValidationResult, run_sql_check


def validate_corporate_actions(conn) -> ValidationResult:
    """
    Phase-3 invariants for corporate_actions.
    This validator must pass before the job is allowed to run.
    """

    results = []

    # 1) Orphan check (should be impossible, but we verify)
    results.append(
        run_sql_check(
            conn,
            name="no orphan corporate actions",
            sql="""
                SELECT COUNT(*) AS orphan_rows
                FROM stocks_research.corporate_actions ca
                LEFT JOIN stocks_research.securities s
                  ON s.security_id = ca.security_id
                WHERE s.security_id IS NULL
            """,
            expect_zero=True,
        )
    )

    # 2) Missing provider_action_id (event identity must exist)
    results.append(
        run_sql_check(
            conn,
            name="all corporate actions have provider_action_id",
            sql="""
                SELECT COUNT(*) AS missing_provider_ids
                FROM stocks_research.corporate_actions
                WHERE provider_action_id IS NULL
            """,
            expect_zero=True,
        )
    )

    # 3) Duplicate provider_action_id (idempotency guarantee)
    results.append(
        run_sql_check(
            conn,
            name="no duplicate corporate action provider ids",
            sql="""
                SELECT COUNT(*) FROM (
                    SELECT provider, provider_action_id, COUNT(*) AS n
                    FROM stocks_research.corporate_actions
                    GROUP BY 1,2
                    HAVING COUNT(*) > 1
                ) t
            """,
            expect_zero=True,
        )
    )

    return ValidationResult.combine(results)
