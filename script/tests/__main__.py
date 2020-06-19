import re
import unittest

from script.checkmk_lurk import *


class TestApiMethods(unittest.TestCase):
    def test_getOauth(self):
        # Response is JWT
        token = get_oath_token()

        output = bool(re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_.+/]*$", token))

        self.assertTrue(output)

    def test_sendEvents(self):
        path = "/checkmk-events"
        data = {
            'events': [{
                'id': 'unitTest',
                'name': 'unitTest',
                'timestamp': 0,
                'type': 'unitTest',
                'hostname': 'unitTest',
                'service_description': 'unitTest',
                'state_type': 'unitTest',
                'output': 'unitTest',
                'long_output': 'unitTest',
                'event_state': 0
            }]
        }
        token = get_oath_token()

        self.assertTrue(send_data(path, data, token))

    def test_sendPerformance(self):
        path = "/checkmk-performances"
        data = {
            'services': [{
                'id': 'unitTest',
                'name': 'unitTest',
                'timestamp': 0,
                'host_groups': ['unitTest', 'unitTest'],
                'hostname': 'unitTest',
                'service_description': 'unitTest',
                'perf_data': [{
                    'var_name': 'unitTest',
                    'actual': 0,
                    'warning': 0,
                    'critical': 0,
                    'min': 0,
                    'max': 0
                }],
                'service_state': 0
            }]
        }
        token = get_oath_token()

        self.assertTrue(send_data(path, data, token))


class TestCheckmkMethods(unittest.TestCase):
    def test_getData(self):
        output = get_data("GET columns\nColumns: name\nFilter: table = columns\nOutputFormat: json\n\n",
                          config.SITES[0]["address"], config.SITES[0]["certificate"])

        if output:
            output = json.loads(output)

        data = [
            ["description"],
            ["name"],
            ["table"],
            ["type"]
        ]

        self.assertEqual(data, output)

    def test_parsePerformanceData(self):
        data = "load1=0.23;10;20;0;2"
        output = [{'var_name': 'load1', 'actual': 0.23, 'warning': 10, 'critical': 20, 'min': 0, 'max': 2}]

        self.assertEqual(parse_perf_data(data), output)

    def test_parsePerformanceData2(self):
        data = "execution_time=0.657 user_time=0.020"
        output = [{'var_name': 'execution_time', 'actual': 0.657}, {'var_name': 'user_time', 'actual': 0.02}]

        self.assertEqual(parse_perf_data(data), output)


if __name__ == '__main__':
    unittest.main()
