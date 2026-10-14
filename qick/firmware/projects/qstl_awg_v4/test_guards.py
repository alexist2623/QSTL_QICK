"""Negative tests for the v4 prebuild/publication evidence gate."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v4_scope_test',HERE/'validate_scope.py')
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)


class EvidenceGuard(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        scope.OUT=self.path
        scope.validate=lambda:{'passed':True}
        self.source=self.path/'source.sv';self.source.write_text('production source')
        self.result=self.path/'result.json';self.result.write_text('{"passed":true}')
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.gate=dict(complete=True,cases=['a','b','c','d','e'],selected_area_bits=48,
                       source_hashes={str(self.source):digest(self.source)},
                       evidence_hashes={str(self.result):digest(self.result)})

    def save(self):
        (self.path/'prebuild_gate.json').write_text(json.dumps(self.gate))

    def test_valid_bound_evidence(self):
        self.save();self.assertTrue(scope.validate_functional()['passed'])

    def test_incomplete_rejected(self):
        self.gate['complete']=False;self.save()
        with self.assertRaises(RuntimeError):scope.validate_functional()

    def test_changed_source_rejected(self):
        self.save();self.source.write_text('changed after test')
        with self.assertRaises(RuntimeError):scope.validate_functional()

    def test_changed_result_rejected(self):
        self.save();self.result.write_text('{"passed":false}')
        with self.assertRaises(RuntimeError):scope.validate_functional()

    def test_missing_case_rejected(self):
        self.gate['cases'].pop();self.save()
        with self.assertRaises(RuntimeError):scope.validate_functional()

    def test_unbound_evidence_rejected(self):
        self.gate['evidence_hashes']={};self.save()
        with self.assertRaises(RuntimeError):scope.validate_functional()


if __name__=='__main__':unittest.main(verbosity=2)
