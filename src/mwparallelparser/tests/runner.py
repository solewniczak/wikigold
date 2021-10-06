import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))  # add tested module to path

import test_doublebraces
import test_header
import test_list

loader = unittest.TestLoader()
suite  = unittest.TestSuite()

suite.addTests(loader.loadTestsFromModule(test_doublebraces))
suite.addTests(loader.loadTestsFromModule(test_header))
suite.addTests(loader.loadTestsFromModule(test_list))

runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)