# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path


class EvaluatorResult(Enum):
    """
    Evaluator result
    """

    BUILD_CRASHED = 0
    BUILD_PASSED = 1
    BUILD_FAILED = 2


class Evaluator(ABC):
    """
    Base evaluator class
    """

    @property
    @abstractmethod
    def target(self) -> str:
        """The corresponding Fetcher target"""

    @abstractmethod
    def evaluate_testcase(self, build_path: Path) -> EvaluatorResult:
        """
        Method for evaluating testcase

        :returns: Evaluation result
        :rtype: EvaluatorResult
        """
