# Copyright 2021 Google Inc. All Rights Reserved.
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

"""Unittest for OpenConfig rendering module."""

import json
from unittest import mock

from absl.testing import absltest, parameterized

from aerleon.lib import aclgenerator, nacaddr, naming, openconfig, policy
from tests.regression_utils import capture

GOOD_HEADER = """
header {
  comment:: "The general policy comment."
  target:: openconfig good-name-v4 inet
}
"""

GOOD_SADDR = """
term good-term-1 {
  comment:: "Allow source address."
  source-address:: CORP_EXTERNAL
  action:: accept
}
"""

GOOD_DADDR = """
term good-term-1 {
  comment:: "Allow destination address."
  destination-address:: CORP_EXTERNAL
  action:: accept
}
"""

GOOD_SPORT = """
term good-term-1 {
  comment:: "Allow TCP 53 source."
  source-port:: DNS
  protocol:: tcp
  action:: accept
}
"""

GOOD_DPORT = """
term good-term-1 {
  comment:: "Allow TCP 53 dest."
  destination-port:: DNS
  protocol:: tcp
  action:: accept
}
"""

GOOD_MULTI_PROTO_DPORT = """
term good-term-1 {
  comment:: "Allow TCP & UDP high."
  source-port:: HIGH_PORTS
  destination-port:: HIGH_PORTS
  protocol:: udp tcp
  action:: accept
}
"""
GOOD_TCP_EST = """
term good-tcp-est {
  protocol:: tcp
  destination-address:: CORP_EXTERNAL
  source-port:: HTTP
  option:: tcp-established
  action:: accept
}
"""
BAD_TCP_EST = """
term bad-tcp-est {
  protocol:: tcp udp
  source-port:: DNS
  option:: tcp-established
  action:: accept
}
"""
GOOD_EVERYTHING = """
term good-term-1 {
  comment:: "Allow TCP & UDP 53 with saddr/daddr."
  destination-address:: CORP_EXTERNAL
  source-address:: CORP_EXTERNAL
  destination-port:: DNS
  protocol:: udp tcp
  action:: accept
}
"""

GOOD_JSON_SADDR = """
[
  {
    "acl-entries": {
      "acl-entry": [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "source-address": "10.2.3.4/32"
            }
          },
          "sequence-id": 5
        }
      ]
    },
    "config": {
      "name": "good-name-v4",
      "type": "ACL_IPV4"
    },
    "name": "good-name-v4",
    "type": "ACL_IPV4"
  }
]
"""

GOOD_JSON_V6_SADDR = """
[
  {
    "acl-entries": {
      "acl-entry":  [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv6": {
            "config": {
              "source-address": "2001:4860:8000::5/128"
            }
          },
          "sequence-id": 5
        }
      ]
    },
    "config": {
      "name": "good-name-v6",
      "type": "ACL_IPV6"
    },
    "name": "good-name-v6",
    "type": "ACL_IPV6"
  }
]
"""

GOOD_JSON_DADDR = """
[
  {
    "acl-entries": {
      "acl-entry": [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "destination-address": "10.2.3.4/32"
            }
          },
          "sequence-id": 5
        }
      ]
    },
    "config": {
      "name": "good-name-v4",
      "type": "ACL_IPV4"
    },
    "name": "good-name-v4",
    "type": "ACL_IPV4"
  }
]
"""

GOOD_JSON_V6_DADDR = """
[
  {
    "acl-entries": {
      "acl-entry":  [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv6": {
            "config": {
              "destination-address": "2001:4860:8000::5/128"
            }
          },
          "sequence-id": 5
        }
      ]
    },
    "config": {
      "name": "good-name-v6",
      "type": "ACL_IPV6"
    },
    "name": "good-name-v6",
    "type": "ACL_IPV6"
  }
]
"""

GOOD_JSON_MIXED_DADDR = """
[
  {
    "acl-entries": {
      "acl-entry": [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "destination-address": "10.2.3.4/32"
            }
          },
          "sequence-id": 5
        },
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv6": {
            "config": {
              "destination-address": "2001:4860:8000::5/128"
            }
          },
          "sequence-id": 10
        }
      ]
    },
    "config": {
      "name": "good-name-mixed",
      "type": "ACL_MIXED"
    },
    "name": "good-name-mixed",
    "type": "ACL_MIXED"
  }
]
"""

GOOD_JSON_SPORT = """
[
  {
    "acl-entries": {
      "acl-entry": [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "protocol": 6
            }
          },
          "sequence-id": 5,
          "transport": {
            "config": {
              "source-port": 53
            }
          }
        }
      ]
    },
    "config": {
      "name": "good-name-v4",
      "type": "ACL_IPV4"
    },
    "name": "good-name-v4",
    "type": "ACL_IPV4"
  }
]
"""

GOOD_JSON_DPORT = """
[
  {
    "acl-entries": {
      "acl-entry": [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "protocol": 6
            }
          },
          "sequence-id": 5,
          "transport": {
            "config": {
              "destination-port": 53
            }
          }
        }
      ]
    },
    "config": {
      "name": "good-name-v4",
      "type": "ACL_IPV4"
    },
    "name": "good-name-v4",
    "type": "ACL_IPV4"
  }
]
"""

GOOD_JSON_MULTI_PROTO_DPORT = """
[
  {
    "acl-entries": {
      "acl-entry": [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "protocol": 17
            }
          },
          "sequence-id": 5,
          "transport": {
            "config": {
              "destination-port": "1024..65535",
              "source-port": "1024..65535"
            }
          }
        },
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "protocol": 6
            }
          },
          "sequence-id": 10,
          "transport": {
            "config": {
              "destination-port": "1024..65535",
              "source-port": "1024..65535"
            }
          }
        }
      ]
    },
    "config": {
      "name": "good-name-v4",
      "type": "ACL_IPV4"
    },
    "name": "good-name-v4",
    "type": "ACL_IPV4"
  }
]
"""

GOOD_JSON_EVERYTHING = """
[
  {
    "acl-entries": {
      "acl-entry":  [
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "destination-address": "10.2.3.4/32",
              "protocol": 17,
              "source-address": "10.2.3.4/32"
            }
          },
          "sequence-id": 5,
          "transport": {
            "config": {
              "destination-port": 53
            }
          }
        },
        {
          "actions": {
            "config": {
              "forwarding-action": "ACCEPT"
            }
          },
          "ipv4": {
            "config": {
              "destination-address": "10.2.3.4/32",
              "protocol": 6,
              "source-address": "10.2.3.4/32"
            }
          },
          "sequence-id": 10,
          "transport": {
            "config": {
              "destination-port": 53
            }
          }
        }
      ]
    },
    "config": {
      "name": "good-name-v4",
      "type": "ACL_IPV4"
    },
    "name": "good-name-v4",
    "type": "ACL_IPV4"
  }
]
"""
GOOD_HEADER_INET6 = """
header {
  comment:: "The general policy comment."
  target:: openconfig good-name-v6 inet6
}
"""

GOOD_HEADER_MIXED = """
header {
  comment:: "The general policy comment."
  target:: openconfig good-name-mixed mixed
}
"""

# Print a info message when a term is set to expire in that many weeks.
# This is normally passed from command line.
EXP_INFO = 2

TEST_IPS = [nacaddr.IP('10.2.3.4/32'), nacaddr.IP('2001:4860:8000::5/128')]


_TERM_SOURCE_TAGS_LIMIT = 30
_TERM_TARGET_TAGS_LIMIT = 70
_TERM_PORTS_LIMIT = 256


class OpenConfigTest(absltest.TestCase):
    def setUp(self):
        super().setUp()
        self.naming = mock.create_autospec(naming.Naming)

    @capture.stdout
    def testSaddr(self):
        self.naming.GetNetAddr.return_value = TEST_IPS

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER + GOOD_SADDR, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_SADDR)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetNetAddr.assert_called_once_with('CORP_EXTERNAL')
        print(acl)

    @capture.stdout
    def testDaddr(self):
        self.naming.GetNetAddr.return_value = TEST_IPS

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER + GOOD_DADDR, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_DADDR)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetNetAddr.assert_called_once_with('CORP_EXTERNAL')
        print(acl)

    @capture.stdout
    def testSport(self):
        self.naming.GetNetAddr.return_value = TEST_IPS
        self.naming.GetServiceByProto.side_effect = [['53'], ['53']]

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER + GOOD_SPORT, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_SPORT)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetServiceByProto.assert_has_calls([mock.call('DNS', 'tcp')])
        print(acl)

    @capture.stdout
    def testDport(self):
        self.naming.GetServiceByProto.side_effect = [['53'], ['53']]

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER + GOOD_DPORT, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_DPORT)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetServiceByProto.assert_has_calls([mock.call('DNS', 'tcp')])
        print(acl)

    @capture.stdout
    def testMultiDport(self):
        self.naming.GetServiceByProto.return_value = ['1024-65535']

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER + GOOD_MULTI_PROTO_DPORT, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_MULTI_PROTO_DPORT)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetServiceByProto.assert_has_calls(
            [mock.call('HIGH_PORTS', 'tcp'), mock.call('HIGH_PORTS', 'udp')], any_order=True
        )
        print(acl)

    @capture.stdout
    def testEverything(self):
        self.naming.GetServiceByProto.side_effect = [['53'], ['53']]
        self.naming.GetNetAddr.return_value = TEST_IPS

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER + GOOD_EVERYTHING, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_EVERYTHING)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetServiceByProto.assert_has_calls(
            [mock.call('DNS', 'udp'), mock.call('DNS', 'tcp')]
        )
        print(acl)

    @capture.stdout
    def testV6Saddr(self):
        self.naming.GetNetAddr.return_value = TEST_IPS

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER_INET6 + GOOD_SADDR, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_V6_SADDR)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetNetAddr.assert_called_once_with('CORP_EXTERNAL')
        print(acl)

    @capture.stdout
    def testV6Daddr(self):
        self.naming.GetNetAddr.return_value = TEST_IPS

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER_INET6 + GOOD_DADDR, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_V6_DADDR)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetNetAddr.assert_called_once_with('CORP_EXTERNAL')
        print(acl)

    @capture.stdout
    def testMixedDaddr(self):
        self.naming.GetNetAddr.return_value = TEST_IPS

        acl = openconfig.OpenConfig(
            policy.ParsePolicy(GOOD_HEADER_MIXED + GOOD_DADDR, self.naming), EXP_INFO
        )
        expected = json.loads(GOOD_JSON_MIXED_DADDR)
        self.assertEqual(expected, json.loads(str(acl)))

        self.naming.GetNetAddr.assert_called_once_with('CORP_EXTERNAL')
        print(acl)

    @capture.stdout
    def testTcpEstablished(self):
        self.naming.GetServiceByProto.return_value = ['80']
        self.naming.GetNetAddr.return_value = TEST_IPS

        policy_text = GOOD_HEADER + GOOD_TCP_EST
        acl = openconfig.OpenConfig(policy.ParsePolicy(policy_text, self.naming), EXP_INFO)
        output = str(acl)
        self.assertIn('TCP_ESTABLISHED', output, output)
        self.assertIn('BUILTIN', output, output)

        self.naming.GetNetAddr.assert_called_once_with('CORP_EXTERNAL')
        self.naming.GetServiceByProto.assert_called_once_with('HTTP', 'tcp')
        print(acl)

    def testNonTcpWithTcpEstablished(self):
        self.naming.GetServiceByProto.return_value = ['53']

        policy_text = GOOD_HEADER + BAD_TCP_EST
        pol = policy.ParsePolicy(policy_text, self.naming)
        self.assertRaises(
            openconfig.TcpEstablishedWithNonTcpError, openconfig.OpenConfig, pol, EXP_INFO
        )
        self.naming.GetServiceByProto.assert_has_calls(
            [mock.call('DNS', 'tcp'), mock.call('DNS', 'udp')]
        )


if __name__ == '__main__':
    absltest.main()
