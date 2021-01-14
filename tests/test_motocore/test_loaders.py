import copy
import os
import unittest

import mock
from botocore import BOTOCORE_ROOT

from moto import MOTO_ROOT
from moto.motocore.loaders import Loader


class TestMergeMotoExtras(unittest.TestCase):
    def setUp(self):
        super(TestMergeMotoExtras, self).setUp()
        self.file_loader = mock.Mock()
        self.data_loader = Loader(file_loader=self.file_loader)
        self.data_loader.determine_latest_version = mock.Mock(return_value="2015-03-01")
        self.data_loader.list_available_services = mock.Mock(return_value=["myservice"])

        isdir_mock = mock.Mock(return_value=True)
        self.isdir_patch = mock.patch("os.path.isdir", isdir_mock)
        self.isdir_patch.start()

    def tearDown(self):
        super(TestMergeMotoExtras, self).tearDown()
        self.isdir_patch.stop()

    def test_merge_moto_extras_with_botocore_service_model(self):
        service_data = {"foo": "service", "bar": "service"}
        moto_extras = {"merge": {"foo": "moto"}}
        self.file_loader.load_file.side_effect = [
            None,  # moto path
            service_data,  # botocore path
            moto_extras,  # moto path
            None,
        ]

        loaded = self.data_loader.load_service_model("myservice", "service-2")
        expected = {"foo": "moto", "bar": "service"}
        self.assertEqual(loaded, expected)

        call_args = self.file_loader.load_file.call_args_list
        call_args = [c[0][0] for c in call_args]
        botocore_path = os.path.join(BOTOCORE_ROOT, "data", "myservice", "2015-03-01")
        moto_path = os.path.join(MOTO_ROOT, "data", "myservice", "2015-03-01")

        # Loader searches CUSTOMER_DATA_PATH (moto) and the BUILTIN_DATA_PATH (botocore)
        # Our file loader mock returns service info on the botocore path and extra info
        # on the moto path.

        self.assertEqual(call_args[1], os.path.join(botocore_path, "service-2"))
        self.assertEqual(call_args[2], os.path.join(moto_path, "service-2.moto-extras"))

    def test_moto_extras_not_found(self):
        service_data = {"foo": "service", "bar": "service"}
        service_data_copy = copy.copy(service_data)
        self.file_loader.load_file.side_effect = [None, service_data, None, None]

        loaded = self.data_loader.load_service_model("myservice", "service-2")
        self.assertEqual(loaded, service_data_copy)

    def test_nothing_in_moto_extras_to_merge(self):
        service_data = {"foo": "service", "bar": "service"}
        service_data_copy = copy.copy(service_data)
        self.file_loader.load_file.side_effect = [None, service_data, {}, None]

        loaded = self.data_loader.load_service_model("myservice", "service-2")
        self.assertEqual(loaded, service_data_copy)
