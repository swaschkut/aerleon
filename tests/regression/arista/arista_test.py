# Copyright 2016 Google Inc. All Rights Reserved.
# Modifications Copyright 2022-2023 Aerleon Project Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for arista acl rendering module."""

from unittest import mock

from absl.testing import absltest

from aerleon.lib import arista, nacaddr, naming, policy
from tests.regression_utils import capture

GOOD_HEADER = """
header {
  comment:: "this is a test extended acl"
  target:: arista test-filter extended
}
"""

GOOD_HEADER_2 = """
header {
  comment:: "this is a test acl"
  target:: arista test-filter
}
"""

GOOD_HEADER_3 = """
header {
  comment:: "this is a test standard acl"
  target:: arista test-filter standard
}
"""

GOOD_HEADER_IPV6 = """
header {
  comment:: "this is a test inet6 acl"
  target:: arista test-filter inet6
}
"""

GOOD_TERM = """
term good-term {
  protocol:: tcp
  option:: tcp-established
  action:: accept
}
"""

GOOD_TERM_1 = """
term good-term-1 {
  protocol:: tcp
  option:: tcp-established
  policer:: batman
  action:: accept
}
"""

GOOD_TERM_2 = """
term good-term-2 {
  source-address:: SOME_HOST
  destination-port:: SSH
  protocol:: tcp
  action:: accept
}
"""

GOOD_TERM_3 = """
term good-term-3 {
  source-address:: SOME_HOST2
  destination-port:: GOPENFLOW
  protocol:: tcp
  action:: accept
}
"""

GOOD_TERM_4 = """
term good-term-4 {
  comment:: "Accept SNMP from internal sources."
  address:: SOME_HOST
  action:: accept
}
"""

GOOD_TERM_5 = """
term good-term-5 {
  comment:: "Accept ESP from internal sources."
  address:: SOME_HOST
  protocol:: esp
  action:: accept
}
"""

GOOD_TERM_6 = """
term good-term-6 {
  comment:: "Accept AH from internal sources."
  address:: SOME_HOST
  protocol:: ah
  action:: accept
}
"""

GOOD_TERM_7 = """
term good-term-6 {
  comment:: "Accept AH from internal sources."
  address:: SOME_HOST
  protocol:: ah esp tcp
  action:: accept
}
"""
GOOD_TERM_8 = """
term good-term-2 {
  destination-port:: SIP
  protocol:: udp
  action:: accept
}
"""

SUPPORTED_TOKENS = {
    'action',
    'address',
    'comment',
    'destination_address',
    'destination_address_exclude',
    'destination_port',
    'dscp_match',
    'expiration',
    'icmp_code',
    'icmp_type',
    'stateless_reply',
    'logging',
    'name',
    'option',
    'owner',
    'platform',
    'platform_exclude',
    'protocol',
    'restrict_address_family',
    'source_address',
    'source_address_exclude',
    'source_port',
    'translated',
    'verbatim',
}

SUPPORTED_SUB_TOKENS = {
    'action': {'accept', 'deny', 'reject', 'next', 'reject-with-tcp-rst'},
    'icmp_type': {
        'alternate-address',
        'certification-path-advertisement',
        'certification-path-solicitation',
        'conversion-error',
        'destination-unreachable',
        'echo-reply',
        'echo-request',
        'mobile-redirect',
        'home-agent-address-discovery-reply',
        'home-agent-address-discovery-request',
        'icmp-node-information-query',
        'icmp-node-information-response',
        'information-request',
        'inverse-neighbor-discovery-advertisement',
        'inverse-neighbor-discovery-solicitation',
        'mask-reply',
        'mask-request',
        'information-reply',
        'mobile-prefix-advertisement',
        'mobile-prefix-solicitation',
        'multicast-listener-done',
        'multicast-listener-query',
        'multicast-listener-report',
        'multicast-router-advertisement',
        'multicast-router-solicitation',
        'multicast-router-termination',
        'neighbor-advertisement',
        'neighbor-solicit',
        'packet-too-big',
        'parameter-problem',
        'redirect',
        'redirect-message',
        'router-advertisement',
        'router-renumbering',
        'router-solicit',
        'router-solicitation',
        'source-quench',
        'time-exceeded',
        'timestamp-reply',
        'timestamp-request',
        'unreachable',
        'version-2-multicast-listener-report',
    },
    'option': {'established', 'tcp-established', 'is-fragment', 'fragments'},
}

# Print a info message when a term is set to expire in that many weeks.
# This is normally passed from command line.
EXP_INFO = 2


class AristaTest(absltest.TestCase):
    def setUp(self):
        super().setUp()
        self.naming = mock.create_autospec(naming.Naming)

    @capture.stdout
    def testRemark(self):
        self.naming.GetNetAddr.return_value = [nacaddr.IP('10.1.1.1/32')]

        pol = policy.ParsePolicy(GOOD_HEADER_3 + GOOD_TERM_4, self.naming)
        acl = arista.Arista(pol, EXP_INFO)
        expected = 'remark this is a test standard acl'
        self.assertIn(expected, str(acl), '[%s]' % str(acl))
        expected = 'remark good-term-4'
        self.assertIn(expected, str(acl), str(acl))
        expected = 'test-filter remark'
        self.assertNotIn(expected, str(acl), str(acl))

        self.naming.GetNetAddr.assert_called_once_with('SOME_HOST')
        print(acl)

    @capture.stdout
    def testExtendedEosSyntax(self):
        # Extended access-lists should not use the "extended" argument to ip
        # access-list.
        acl = arista.Arista(policy.ParsePolicy(GOOD_HEADER + GOOD_TERM, self.naming), EXP_INFO)
        self.assertIn('ip access-list test-filter', str(acl))
        print(acl)

    @capture.stdout
    def testESPIsAnInteger(self):
        acl = arista.Arista(policy.ParsePolicy(GOOD_HEADER + GOOD_TERM_5, self.naming), EXP_INFO)
        self.assertIn('permit 50', str(acl))
        print(acl)

    @capture.stdout
    def testAHIsAnInteger(self):
        acl = arista.Arista(policy.ParsePolicy(GOOD_HEADER + GOOD_TERM_6, self.naming), EXP_INFO)
        self.assertIn('permit 51', str(acl))
        print(acl)

    @capture.stdout
    def testAHAndESPAreIntegers(self):
        acl = arista.Arista(policy.ParsePolicy(GOOD_HEADER + GOOD_TERM_7, self.naming), EXP_INFO)
        self.assertIn('permit 50', str(acl))
        self.assertIn('permit 51', str(acl))
        print(acl)

    @capture.stdout
    def testBuildTokens(self):
        pol1 = arista.Arista(policy.ParsePolicy(GOOD_HEADER + GOOD_TERM, self.naming), EXP_INFO)
        st, sst = pol1._BuildTokens()
        self.assertEqual(st, SUPPORTED_TOKENS)
        self.assertEqual(sst, SUPPORTED_SUB_TOKENS)
        print(pol1)

    @capture.stdout
    def testBuildWarningTokens(self):
        pol1 = arista.Arista(policy.ParsePolicy(GOOD_HEADER + GOOD_TERM_1, self.naming), EXP_INFO)
        st, sst = pol1._BuildTokens()
        self.assertEqual(st, SUPPORTED_TOKENS)
        self.assertEqual(sst, SUPPORTED_SUB_TOKENS)
        print(pol1)

    @capture.stdout
    def testStandardTermHost(self):
        self.naming.GetNetAddr.return_value = [nacaddr.IP('10.1.1.0/24')]
        self.naming.GetServiceByProto.return_value = ['22', '6537']

        pol = policy.ParsePolicy(GOOD_HEADER_2 + GOOD_TERM_2 + GOOD_TERM_3, self.naming)
        acl = arista.Arista(pol, EXP_INFO)
        print(acl)
        expected = 'ip access-list test-filter'
        self.assertIn(expected, str(acl), '[%s]' % str(acl))
        expected = ' permit tcp 10.1.1.0/24 any eq ssh'
        self.assertIn(expected, str(acl), str(acl))
        expected = ' permit tcp 10.1.1.0/24 any eq 6537'
        self.assertIn(expected, str(acl), str(acl))

        self.naming.GetNetAddr.assert_has_calls([mock.call('SOME_HOST'), mock.call('SOME_HOST2')])
        self.naming.GetServiceByProto.assert_has_calls(
            [mock.call('SSH', 'tcp'), mock.call('GOPENFLOW', 'tcp')]
        )

    @capture.stdout
    def testStandardTermHostV6(self):
        self.naming.GetNetAddr.return_value = [nacaddr.IP('2620:1::/64')]
        self.naming.GetServiceByProto.return_value = ['22']

        pol = policy.ParsePolicy(GOOD_HEADER_IPV6 + GOOD_TERM_2, self.naming)
        acl = arista.Arista(pol, EXP_INFO)
        print(acl)
        expected = 'ipv6 access-list test-filter'
        self.assertIn(expected, str(acl), '[%s]' % str(acl))
        expected = ' permit tcp 2620:1::/64 any eq ssh'
        self.assertIn(expected, str(acl), str(acl))

        self.naming.GetNetAddr.assert_has_calls([mock.call('SOME_HOST')])
        self.naming.GetServiceByProto.assert_has_calls([mock.call('SSH', 'tcp')])

    @capture.stdout
    def testStandardTermV4(self):
        self.naming.GetNetAddr.return_value = [nacaddr.IP('10.1.1.0/24')]

        pol = policy.ParsePolicy(GOOD_HEADER_3 + GOOD_TERM_4, self.naming)
        acl = arista.Arista(pol, EXP_INFO)
        print(acl)
        expected = 'ip access-list standard test-filter'
        self.assertIn(expected, str(acl), '[%s]' % str(acl))
        expected = ' permit 10.1.1.0/24\n'
        self.assertIn(expected, str(acl), str(acl))

        self.naming.GetNetAddr.assert_has_calls([mock.call('SOME_HOST')])

    @capture.stdout
    def testSIPUsesInt(self):
        self.naming.GetServiceByProto.return_value = ['5060']
        pol = policy.ParsePolicy(GOOD_HEADER + GOOD_TERM_8, self.naming)
        acl = arista.Arista(pol, EXP_INFO)
        print(acl)
        self.assertIn('5060', str(acl))
        self.assertNotIn('sip', str(acl))


if __name__ == '__main__':
    absltest.main()
