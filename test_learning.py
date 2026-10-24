import tempfile
import unittest
from pathlib import Path
from learning import domain_for, record, report, guidance

class LearningTests(unittest.TestCase):
 def test_explicit_feedback_and_domains(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.db'
   self.assertEqual(domain_for('Bitcoin token research'), 'crypto')
   self.assertEqual(domain_for('stock market research'), 'stocks')
   self.assertEqual(report('crypto',p), [])
   record('Critic','crypto',5,'Found unsupported return claim',p)
   self.assertEqual(report('crypto',p), [('Critic',1,5.0)])
   self.assertIn('not verified accuracy',guidance('crypto',p))
   self.assertEqual(report('stocks',p), [])
   with self.assertRaises(ValueError): record('Critic','crypto',6,'invalid',p)
