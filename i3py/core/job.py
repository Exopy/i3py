# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Object used to handle operation that takes a long time to complete.

"""
import time
from typing import Callable, Optional


class InstrJob(object):
    """Object returned by instrument starting a long running job.

    This object can also be used inside a method to handle the waiting of a
    condition.

    Parameters
    ----------
    condition_callable : Callable
        Callable taking no argument and indicating if the job is complete.

    expected_waiting_time : float
        Expected waiting time for the task to complete in seconds.

    cancel : Callable, optional
        Function to cancel the task. The job will pass it all the argument it
        is called with and the function return value will be returned.

    """
    def __init__(self,
                 condition_callable: Callable[[], bool],
                 expected_waiting_time: float,
                 cancel: Optional[Callable]=None) -> None:
        self.condition_callable = condition_callable
        self.expected_waiting_time = expected_waiting_time
        self._cancel = cancel
        self._start_time = time.time()

    def wait_for_completion(self,
                            break_condition_callable:
                                Optional[Callable[[], bool]]=None,
                            timeout: float=15,
                            refresh_time: float=1) -> bool:
        """Wait for the task to complete.

        Parameters
        ----------
        break_condition_callable : Callable, optional
            Callable indicating that we should stop waiting.

        timeout : float, optional
            Time to wait in seconds in addition to the expected condition time
            before breaking.

        refresh_time : float, optional
            Time interval at which to check the break condition.

        Returns
        -------
        result : bool
            Boolean indicating if the wait succeeded of was interrupted.

        """
        if break_condition_callable is None:
            def no_check():
                pass
            break_condition_callable = no_check

        while True:
            remaining_time = (self.expected_waiting_time -
                              (time.time() - self._start_time))
            if remaining_time <= 0:
                break
            time.sleep(min(refresh_time, remaining_time))
            if break_condition_callable():
                return False

        if self.condition_callable():
            return True

        timeout_start = time.time()
        while True:
            remaining_time = (timeout -
                              (time.time() - timeout_start))
            if remaining_time < 0:
                return False
            time.sleep(min(refresh_time, remaining_time))
            if self.condition_callable():
                return True
            if break_condition_callable():
                return False

    def cancel(self, *args, **kwargs):
        """Cancel the long running job.

        """
        if not self._cancel:
            raise RuntimeError('No callable was provided to cancel the task.')
        return self._cancel(*args, **kwargs)
