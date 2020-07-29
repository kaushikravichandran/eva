# coding=utf-8
# Copyright 2018-2020 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pandas as pd
from enum import Enum, unique
from typing import Callable

from src.constants import NO_GPU
from src.executor.execution_context import Context
from src.expression.abstract_expression import AbstractExpression, \
    ExpressionType
from src.models.storage.batch import Batch
from src.udfs.gpu_compatible import GPUCompatible


@unique
class ExecutionMode(Enum):
    # EXEC means the executed function mutates the batch frame and returns
    # it back. The frame batch is mutated.
    EXEC = 1
    # EVAL function with return values
    EVAL = 2


class FunctionExpression(AbstractExpression):
    """
    Expression used for function evaluation
    Arguments:
        func (Callable): UDF or EVA built in function for performing
        operations on the

        mode (ExecutionMode): The mode in which execution needs to happen.
        Will just return the output in EVAL mode. EXEC mode updates the
        BatchFrame with output.

        is_temp (bool, default:False): In case of EXEC type, decides if the
        outcome needs to be stored in BatchFrame temporarily.

    """

    def __init__(self, func: Callable,
                 mode: ExecutionMode = ExecutionMode.EVAL, name=None,
                 is_temp: bool = False,
                 **kwargs):
        if mode == ExecutionMode.EXEC:
            assert name is not None

        super().__init__(ExpressionType.FUNCTION_EXPRESSION, **kwargs)
        self._context = Context()
        self.mode = mode
        self.name = name
        self.function = func
        self.is_temp = is_temp

    def _batch_to_args(self, batch: Batch):
        for ind in range(len(batch.frames)):
            yield batch.frames.iloc[ind].tolist()

    def evaluate(self, batch: Batch):
        args_gen = []
        if self.get_children_count() > 0:
            child = self.get_child(0)
            args_gen.append(self._batch_to_args(child.evaluate(batch)))
        else:
            args_gen.append(self._batch_to_args(batch))
        func = self._gpu_enabled_function()

        called_once = False
        frames = pd.DataFrame()
        for args in zip(*args_gen):
            flat_args = [item for arg in args for item in arg]
            outcomes = func(*flat_args)
            called_once = True
            # We only consider outcomes size 1 here
            frames = frames.append(outcomes[0].data, ignore_index=True)
        # Even when batch.frames is empty, the generator will still be returned
        if not called_once:
            outcomes = func()
            frames = outcomes[0].data
        new_batch = Batch(frames=frames)

        # This is not used now
        # if self.mode == ExecutionMode.EXEC:
        #    batch.set_outcomes(self.name, outcomes, is_temp=self.is_temp)
        return new_batch

    def _gpu_enabled_function(self):
        if isinstance(self.function, GPUCompatible):
            device = self._context.gpu_device()
            if device != NO_GPU:
                return self.function.to_device(device)
        return self.function
