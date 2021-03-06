#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from nova.scheduler.filters import ram_filter
from nova import test
from nova.tests.unit.scheduler import fakes


class TestRamFilter(test.NoDBTestCase):

    def setUp(self):
        super(TestRamFilter, self).setUp()
        self.filt_cls = ram_filter.RamFilter()

    def test_ram_filter_fails_on_memory(self):
        self.flags(ram_allocation_ratio=1.0)
        filter_properties = {'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1',
                {'free_ram_mb': 1023, 'total_usable_ram_mb': 1024})
        self.assertFalse(self.filt_cls.host_passes(host, filter_properties))

    def test_ram_filter_passes(self):
        self.flags(ram_allocation_ratio=1.0)
        filter_properties = {'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1',
                {'free_ram_mb': 1024, 'total_usable_ram_mb': 1024})
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))

    def test_ram_filter_oversubscribe(self):
        self.flags(ram_allocation_ratio=2.0)
        filter_properties = {'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1',
                {'free_ram_mb': -1024, 'total_usable_ram_mb': 2048})
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        self.assertEqual(2048 * 2.0, host.limits['memory_mb'])


@mock.patch('nova.scheduler.filters.utils.aggregate_values_from_key')
class TestAggregateRamFilter(test.NoDBTestCase):

    def setUp(self):
        super(TestAggregateRamFilter, self).setUp()
        self.filt_cls = ram_filter.AggregateRamFilter()

    def test_aggregate_ram_filter_value_error(self, agg_mock):
        self.flags(ram_allocation_ratio=1.0)
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1',
                {'free_ram_mb': 1024, 'total_usable_ram_mb': 1024})
        agg_mock.return_value = set(['XXX'])
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        self.assertEqual(1024 * 1.0, host.limits['memory_mb'])

    def test_aggregate_ram_filter_default_value(self, agg_mock):
        self.flags(ram_allocation_ratio=1.0)
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1',
                {'free_ram_mb': 1023, 'total_usable_ram_mb': 1024})
        # False: fallback to default flag w/o aggregates
        agg_mock.return_value = set()
        self.assertFalse(self.filt_cls.host_passes(host, filter_properties))
        agg_mock.return_value = set(['2.0'])
        # True: use ratio from aggregates
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        self.assertEqual(1024 * 2.0, host.limits['memory_mb'])

    def test_aggregate_ram_filter_conflict_values(self, agg_mock):
        self.flags(ram_allocation_ratio=1.0)
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1',
                {'free_ram_mb': 1023, 'total_usable_ram_mb': 1024})
        agg_mock.return_value = set(['1.5', '2.0'])
        # use the minimum ratio from aggregates
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        self.assertEqual(1024 * 1.5, host.limits['memory_mb'])
