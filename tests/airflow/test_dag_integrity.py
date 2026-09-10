"""
Standard Airflow DAG integrity test suite, using DagBag -- the same
mechanism Airflow itself uses to load DAGs, so these tests fail exactly
when a real deployment would fail to load a DAG (import error, cycle,
missing default_args, etc.), not on some looser proxy check.

Uses dagbag.dags[dag_id] (the in-memory dict built during parsing), NOT
dagbag.get_dag(dag_id) -- the latter queries Airflow's metadata database,
which doesn't exist in this throwaway test container (no `airflow db
migrate` has run here, deliberately, since these are static checks that
shouldn't need a database at all).
"""

from __future__ import annotations

import pytest
from airflow.models import DagBag


# ============================================================================
# STATELESS DAGBAG FIXTURE
# ============================================================================
@pytest.fixture(scope="session")
def dagbag() -> DagBag:
    """
    Session-scoped Pytest fixture that parses all DAG files inside the container's
    '/opt/airflow/dags' directory once per test run.
    
    Using dagbag.dags accesses the in-memory parsed DAG objects directly without 
    requiring a running metadata database or database migration.
    """
    return DagBag(dag_folder="/opt/airflow/dags", include_examples=False)


# ============================================================================
# PARSING & IMPORT TESTS
# ============================================================================
def test_no_import_errors(dagbag: DagBag) -> None:
    """
    The single most important test: every DAG file must actually parse without 
    raising Python syntax errors, import errors, or missing library exceptions.
    
    Catches broken code prior to merging, preventing silent parsing failures 
    on the production scheduler.
    """
    assert not dagbag.import_errors, (
        f"DAG import failures: {dagbag.import_errors}"
    )


def test_expected_dags_are_present(dagbag: DagBag) -> None:
    """
    Validates that both expected production DAGs are parsed and present in the 
    in-memory dagbag.dags dictionary keys.
    """
    expected_dag_ids = {"travel_platform_daily_pipeline", "ml_training_pipeline"}
    actual_dag_ids = set(dagbag.dags.keys())
    missing = expected_dag_ids - actual_dag_ids
    assert not missing, f"Expected DAGs not found: {missing}"


# ============================================================================
# DAG STRUCTURE & CONFIGURATION TESTS
# ============================================================================
@pytest.mark.parametrize("dag_id", ["travel_platform_daily_pipeline", "ml_training_pipeline"])
def test_dag_has_no_cycles(dagbag: DagBag, dag_id: str) -> None:
    """
    Verifies that the target DAG was loaded into memory without cyclic dependency loops.
    
    Note: DagBag cycle checking executes automatically during file parsing—if a DAG 
    exists in dagbag.dags, it is guaranteed to be acyclic.
    """
    dag = dagbag.dags.get(dag_id)
    assert dag is not None, f"{dag_id} did not load"


@pytest.mark.parametrize("dag_id", ["travel_platform_daily_pipeline", "ml_training_pipeline"])
def test_dag_has_retries_configured(dagbag: DagBag, dag_id: str) -> None:
    """
    Iterates through all tasks within each DAG to ensure every task inherits or 
    defines at least 1 retry attempt.
    
    Guards against tasks crashing permanently during temporary database or network glitches.
    """
    dag = dagbag.dags[dag_id]
    for task in dag.tasks:
        assert task.retries is not None and task.retries >= 1, (
            f"{dag_id}.{task.task_id} has no retries configured"
        )


@pytest.mark.parametrize("dag_id", ["travel_platform_daily_pipeline", "ml_training_pipeline"])
def test_dag_has_tags(dagbag: DagBag, dag_id: str) -> None:
    """
    Ensures every DAG has at least one tag configured for organization and UI filtering.
    """
    dag = dagbag.dags[dag_id]
    assert dag.tags, f"{dag_id} has no tags set"


# ============================================================================
# PROJECT-SPECIFIC SCHEDULE & BACKFILL POLICIES
# ============================================================================
def test_daily_dag_has_catchup_enabled(dagbag: DagBag) -> None:
    """
    Verifies that catchup=True remains enabled on the daily ingestion DAG.
    
    Ensures Airflow automatically backfills missing daily data intervals in sequence.
    """
    dag = dagbag.dags["travel_platform_daily_pipeline"]
    assert dag.catchup is True


def test_weekly_dag_has_catchup_disabled(dagbag: DagBag) -> None:
    """
    Verifies that catchup=False is set on the weekly ML retraining DAG.
    
    Prevents triggering multiple historical retraining runs if the scheduler was offline.
    """
    dag = dagbag.dags["ml_training_pipeline"]
    assert dag.catchup is False