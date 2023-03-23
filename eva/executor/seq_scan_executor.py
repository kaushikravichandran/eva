# coding=utf-8
# Copyright 2018-2022 EVA
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
from typing import Iterator

from eva.executor.abstract_executor import AbstractExecutor
from eva.executor.executor_utils import apply_predicate, apply_project
from eva.models.storage.batch import Batch
from eva.plan_nodes.seq_scan_plan import SeqScanPlan


class SequentialScanExecutor(AbstractExecutor):
    """
    Applies predicates to filter the frames which satisfy the condition
    Arguments:
        node (AbstractPlan): The SequentialScanPlan

    """

    def __init__(self, node: SeqScanPlan):
        super().__init__(node)
        self.predicate = node.predicate
        self.project_expr = node.columns
        self.alias = node.alias

    def exec(self, *args, **kwargs) -> Iterator[Batch]:
        child_executor = self.children[0]
        for batch in child_executor.exec(**kwargs):
            # apply alias to the batch
            # id, data -> myvideo.id, myvideo.data
            if self.alias:
                batch.modify_column_alias(self.alias)

            # We do the predicate first
            batch = apply_predicate(batch, self.predicate)
            # Then do project
            batch = apply_project(batch, self.project_expr)

            if not batch.empty():
                yield batch
