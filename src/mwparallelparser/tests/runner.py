import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))  # add tested module to path

import test_doublebraces
import test_formatting
import test_header
import test_list
import test_paragraph
import test_ref
import test_simple_tags
import test_wikilink

loader = unittest.TestLoader()
suite  = unittest.TestSuite()

suite.addTests(loader.loadTestsFromModule(test_doublebraces))
suite.addTests(loader.loadTestsFromModule(test_formatting))
suite.addTests(loader.loadTestsFromModule(test_header))
suite.addTests(loader.loadTestsFromModule(test_list))
suite.addTests(loader.loadTestsFromModule(test_paragraph))
suite.addTests(loader.loadTestsFromModule(test_ref))
suite.addTests(loader.loadTestsFromModule(test_simple_tags))
suite.addTests(loader.loadTestsFromModule(test_wikilink))

runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)