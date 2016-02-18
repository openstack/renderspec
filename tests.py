#!/usr/bin/python
# Copyright (c) 2016 SUSE Linux GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


try:
    import unittest2 as unittest
except ImportError:
    import unittest

import renderspec


class RenderspecTests(unittest.TestCase):
    def test_filter_noop(self):
        self.assertEqual(renderspec._filter_noop("foobar"), "foobar")


if __name__ == '__main__':
    unittest.main()
