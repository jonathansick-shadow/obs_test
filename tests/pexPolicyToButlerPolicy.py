#!/usr/bin/env python

#
# LSST Data Management System
# Copyright 2015 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

import collections
import os
import unittest

from lsst.daf.persistence import Policy as dafPolicy
import lsst.pex.policy as pex_policy
import lsst.utils.tests as utilsTests


class PolicyTestCase(unittest.TestCase):
    """A test case for the butler policy to verify that it can load a pex policy properly."""

    def loadPolicy(self):
        pafPolicyPath = os.path.join(os.environ['OBS_TEST_DIR'], 'policy', 'testMapper.paf')
        self.assertTrue(os.path.exists(pafPolicyPath))
        pexPolicy = pex_policy.Policy.createPolicy(pafPolicyPath)
        policy = dafPolicy(filePath=pafPolicyPath)
        return (policy, pexPolicy)

    def test(self):
        policy, pexPolicy = self.loadPolicy()

        # go back through the newly created Butler Policy, and verify that values match the paf Policy
        for name in policy.names():
            if pexPolicy.isArray(name):
                pexVal = pexPolicy.getArray(name)
            else:
                pexVal = pexPolicy.get(name)
            val = policy[name]
            if isinstance(val, dafPolicy):
                self.assertTrue(pexPolicy.getValueType(name) == pexPolicy.POLICY)
            else:
                self.assertEqual(val, pexVal)

        for name in pexPolicy.names():
            if pexPolicy.getValueType(name) == pexPolicy.POLICY:
                self.assertTrue(isinstance(policy.get(name), dafPolicy))
            else:
                if pexPolicy.isArray(name):
                    pexVal = pexPolicy.getArray(name)
                else:
                    pexVal = pexPolicy.get(name)
                self.assertEqual(pexVal, policy.get(name))

        # verify a known value, just for sanity:
        self.assertEqual(policy.get('exposures.raw.template'), 'raw/raw_v%(visit)d_f%(filter)s.fits.gz')

    def testGetStringArray(self):
        policy, pexPolicy = self.loadPolicy()
        s = policy.asArray('exposures.raw.tables')
        self.assertEqual(s, ['raw', 'raw_skyTile'])

    def testDumpAndLoad(self):
        pafPolicyPath = os.path.join(os.environ['OBS_TEST_DIR'], 'policy', 'testMapper.paf')
        self.assertTrue(os.path.exists(pafPolicyPath))
        pexPolicy = pex_policy.Policy.createPolicy(pafPolicyPath)

        policy = dafPolicy(filePath=pafPolicyPath)
        policyPath = os.path.join(os.environ['OBS_TEST_DIR'], 'policy', 'tempTestMapper.yaml')
        if os.path.exists(policyPath):
            os.remove(policyPath)
        policyFile = open(policyPath, 'w')
        policy.dump(policyFile)
        self.assertTrue(os.path.exists(policyPath))

        pexPolicy = pex_policy.Policy.createPolicy(pafPolicyPath)

        # test that the data went through the entire wringer correctly - verify the
        # original pex data matches the dafPolicy data
        yamlPolicy = dafPolicy(filePath=policyPath)
        yamlNames = yamlPolicy.names()
        yamlNames.sort()
        pexNames = pexPolicy.names()
        pexNames.sort()
        self.assertEqual(yamlNames, pexNames)
        for name in yamlNames:
            if not isinstance(yamlPolicy[name], dafPolicy):
                yamlPolicyVal = yamlPolicy[name]
                if isinstance(yamlPolicyVal, collections.Iterable) and \
                        not isinstance(yamlPolicyVal, basestring):
                    self.assertEqual(yamlPolicyVal, pexPolicy.getArray(name))
                else:
                    self.assertEqual(yamlPolicyVal, pexPolicy.get(name))
        if os.path.exists(policyPath):
            os.remove(policyPath)


def suite():
    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(PolicyTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)


def run(shouldExit = False):
    utilsTests.run(suite(), shouldExit)

if __name__ == '__main__':
    run(True)
