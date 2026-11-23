"""Fixture-only admission harness. No encoder, state finalization, or takeover."""
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .job_claim import claim_fixture
from .job_store import Job
from .render_lock import render_lock_fd


class FixtureNotClaimed(RuntimeError):
    """The ledger did not admit the requested job."""


@contextmanager
def fixture_slot_with_fd(workspace: Path, job_id: int) -> Iterator[tuple[Job, int]]:
    """Hold the stable workspace lock before using its dedicated jobs.sqlite ledger.

    Enter the body only after the named fixture is atomically marked running.
    Exit closes the parent's fd. A trusted child given that fd via pass_fds
    holds the same lock until its last copy closes. Exit does not authorize replay.
    The caller must supply a trusted workspace with an existing fixture ledger.
    """
    with render_lock_fd(workspace) as fd:
        job = claim_fixture(workspace / 'jobs.sqlite', job_id)
        if job is None:
            raise FixtureNotClaimed('No eligible fixture slot for the requested job')
        yield job, fd


@contextmanager
def fixture_slot(workspace: Path, job_id: int) -> Iterator[Job]:
    with fixture_slot_with_fd(workspace, job_id) as (job, _):
        yield job
