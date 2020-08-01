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
import unittest
import os
import cv2
import numpy as np
import pandas as pd

from src.parser.parser import Parser
from src.optimizer.statement_to_opr_convertor import StatementToPlanConvertor
from src.optimizer.plan_generator import PlanGenerator
from src.executor.plan_executor import PlanExecutor
from src.catalog.catalog_manager import CatalogManager
from src.storage import StorageEngine
from src.models.storage.batch import Batch


NUM_FRAMES = 10


class LoadExecutorTest(unittest.TestCase):

    def create_sample_video(self):
        try:
            os.remove('dummy.avi')
        except FileNotFoundError:
            pass

        out = cv2.VideoWriter('dummy.avi',
                              cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 10,
                              (2, 2))
        for i in range(NUM_FRAMES):
            frame = np.array(np.ones((2, 2, 3)) * 0.1 * float(i + 1) * 255,
                             dtype=np.uint8)
            out.write(frame)

    def create_dummy_frames(self, num_frames=NUM_FRAMES, filters=[]):
        if not filters:
            filters = range(num_frames)
        for i in filters:
            yield {'id': i,
                   'data': np.array(np.ones((2, 2, 3))
                                    * 0.1 * float(i + 1) * 255,
                                    dtype=np.uint8)}

    def setUp(self):
        self.create_sample_video()

    def tearDown(self):
        os.remove('dummy.avi')

    # integration test
    @unittest.skip("we need drop functionality before we can enable")
    def test_should_load_video_in_table(self):
        query = """LOAD DATA INFILE 'dummy.avi' INTO MyVideo;"""

        stmt = Parser().parse(query)[0]
        l_plan = StatementToPlanConvertor().visit(stmt)
        p_plan = PlanGenerator().build(l_plan)
        PlanExecutor(p_plan).execute_plan()

        # Do we have select command now?
        metadata = CatalogManager().get_dataset_metadata("", "MyVideo")
        actual_batch = list(StorageEngine.read(metadata))[0]
        expected_batch = Batch(pd.DataFrame(list(self.create_dummy_frames())))
        self.assertEqual(actual_batch, expected_batch)
