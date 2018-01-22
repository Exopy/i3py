# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the InstrJob.

"""
import pytest

from i3py.core.job import InstrJob


def test_normal_wait():
    """Test that we can wait for a job terminating within the expected time.

    """
    def cond():
        return True
    job = InstrJob(cond, 0)
    assert job.wait_for_completion()


def test_wait_within_timeout():
    """Test that we can wait for a job terminating before timeout.

    """
    i = 0

    def cond():
        nonlocal i
        j = i
        i += 1
        return j
    job = InstrJob(cond, 0)
    assert job.wait_for_completion(refresh_time=0.01)
    assert i == 2


def test_interrupted_early_wait():
    """Test we can interrupt the wait before the expected operation length.

    """
    called = False

    def cond():
        nonlocal called
        called = True
        return True
    job = InstrJob(cond, 1)
    assert not job.wait_for_completion(lambda: True, refresh_time=0.1)
    assert not called


def test_interrupted_late_wait():
    """Test we can interrupt the wait during the timeout period.

    """
    called = 0

    def cond():
        nonlocal called
        called += 1
        if called == 3:
            return True
    job = InstrJob(cond, 0)
    assert not job.wait_for_completion(lambda: True, refresh_time=0.1)
    assert called == 2


def test_wait_timeout():
    """Test the wait is interrupted by a timeout.

    """
    def cond():
        return False
    job = InstrJob(cond, 0)
    assert not job.wait_for_completion(timeout=0.01)


def test_cancel():
    """Test that cancelling a job work as expected.

    """
    job = InstrJob(lambda: True, 0)
    with pytest.raises(RuntimeError):
        job.cancel()

    job = InstrJob(lambda: True, 0, lambda *args, **kwargs: (args, kwargs))
    assert job.cancel(1, 2, a=3) == ((1, 2), {'a': 3})
