import unittest
from unittest.mock import MagicMock, patch

import requests

from src.fabric_api_client import FabricApiClient, FabricApiError


def make_response(payload, status_code=200):
    response = requests.Response()
    response.status_code = status_code
    response._content = payload.encode("utf-8")
    response.headers["Content-Type"] = "application/json"
    return response


class FabricApiClientTests(unittest.TestCase):
    def test_non_f2_sku_refuses_without_force(self):
        client = FabricApiClient(dry_run=True)

        with self.assertRaises(FabricApiError):
            client.assert_capacity_is_f2({"sku": {"name": "F4"}, "properties": {"state": "Active"}})

    def test_paused_capacity_requires_explicit_resume_flag(self):
        client = FabricApiClient(dry_run=True)
        client.assert_capacity_is_f2 = MagicMock(
            return_value={
                "sku": {"name": "F2"},
                "properties": {"state": "Paused", "capacityId": "capacity-guid"},
            }
        )

        with self.assertRaises(FabricApiError):
            client.bootstrap(resume_capacity=False)

    def test_dry_run_does_not_create_resources(self):
        client = FabricApiClient(dry_run=True)
        client.assert_capacity_is_f2 = MagicMock(
            return_value={
                "sku": {"name": "F2"},
                "properties": {"state": "Active", "capacityId": "capacity-guid"},
            }
        )
        client.get_workspace_by_name = MagicMock(return_value=None)
        client.list_items = MagicMock(return_value=[])
        client.prepare_csv_upload = MagicMock(return_value=[])

        with patch.object(client.session, "request", wraps=client.session.request) as request_mock:
            result = client.bootstrap(skip_notebook=True)

        self.assertTrue(result.dry_run)
        self.assertIn("workspace", result.created)
        self.assertIn("lakehouse", result.created)
        request_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
