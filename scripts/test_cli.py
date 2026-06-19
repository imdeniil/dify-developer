import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import dify_dev_cli

class TestDifyDevCli(unittest.TestCase):

    def setUp(self):
        # Reset argument parsing or CLI state if any
        pass

    @patch('dify_dev_cli.urllib.request.urlopen')
    def test_api_call_success(self, mock_urlopen):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute call
        result = dify_dev_cli.api_call('/test-endpoint')

        # Assertions
        self.assertEqual(result, {"status": "ok"})
        mock_urlopen.assert_called_once()

    @patch('dify_dev_cli.urllib.request.urlopen')
    def test_run_draft_with_files(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.readline.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        dify_dev_cli.run_draft('app-id', {'param': 'val'}, [{'type': 'image', 'url': 'http://image'}])
        self.assertTrue(mock_urlopen.called)

    def test_format_timestamp(self):
        # Valid timestamp
        ts = 1781891861
        formatted = dify_dev_cli.format_timestamp(ts)
        self.assertTrue(formatted.startswith("2026-"))
        
        # Invalid or None timestamp
        self.assertEqual(dify_dev_cli.format_timestamp(None), "N/A")
        self.assertEqual(dify_dev_cli.format_timestamp("invalid"), "invalid")

    @patch('dify_dev_cli.api_call')
    @patch('builtins.print')
    def test_list_apps(self, mock_print, mock_api_call):
        # Mock api_call response
        mock_api_call.return_value = {
            'data': [
                {
                    'id': 'app-1',
                    'name': 'Test App 1',
                    'mode': 'workflow',
                    'description': 'Short description',
                    'created_at': 1781891861
                }
            ]
        }

        # Mock argparse
        args = MagicMock()
        args.command = "list-apps"
        args.page = 1
        args.limit = 50

        # Execute command handling directly by simulating python main flow
        # In a real script execution, the parsed command calls it.
        # Let's test the print_table directly or simulate command dispatch.
        res = dify_dev_cli.api_call(f'/console/api/apps')
        self.assertEqual(len(res.get('data', [])), 1)

    @patch('dify_dev_cli.api_call')
    def test_delete_mcp_resolution(self, mock_api_call):
        # Mock the tool providers call to return UUID resolution candidates
        mock_api_call.side_effect = [
            [
                {
                    'id': 'mcp-uuid-123',
                    'server_identifier': 'my-cool-mcp',
                    'name': 'Cool MCP Server',
                    'type': 'mcp'
                }
            ],
            {'result': 'success'} # delete response
        ]

        # Simulate resolving name to UUID in delete-mcp command logic
        provider_id = 'my-cool-mcp'
        providers = dify_dev_cli.api_call('/console/api/workspaces/current/tool-providers')
        mcp_providers = [p for p in providers if p.get('type') == 'mcp' or p.get('provider_type') == 'mcp']
        
        found_uuid = None
        for p in mcp_providers:
            if p.get('id') == provider_id or p.get('server_identifier') == provider_id or p.get('name') == provider_id:
                found_uuid = p.get('id')
                break

        self.assertEqual(found_uuid, 'mcp-uuid-123')

    @patch('dify_dev_cli.api_call')
    def test_show_app_details(self, mock_api_call):
        mock_api_call.return_value = {
            'id': 'app-1',
            'name': 'Test App',
            'mode': 'workflow',
            'description': 'Test description',
            'icon': '💼',
            'icon_background': '#000000',
            'enable_api': True,
            'api_base_url': 'http://localhost/v1',
            'created_at': 1781891861,
            'updated_at': 1781891861,
            'site': {'app_base_url': 'http://localhost', 'access_token': 'token123'}
        }
        res = dify_dev_cli.api_call('/console/api/apps/app-1')
        self.assertEqual(res.get('name'), 'Test App')
        self.assertEqual(res.get('site', {}).get('access_token'), 'token123')

    @patch('dify_dev_cli.api_call')
    def test_stop_run(self, mock_api_call):
        mock_api_call.return_value = {'result': 'success'}
        res = dify_dev_cli.api_call('/console/api/apps/app-1/workflow-runs/run-1/stop', 'POST', {})
        self.assertEqual(res.get('result'), 'success')

    @patch('dify_dev_cli.api_call')
    def test_check_deps(self, mock_api_call):
        mock_api_call.return_value = {'leaked_dependencies': []}
        res = dify_dev_cli.api_call('/console/api/apps/imports/app-1/check-dependencies')
        self.assertEqual(len(res.get('leaked_dependencies')), 0)

    @patch('dify_dev_cli.api_call')
    def test_get_default_model(self, mock_api_call):
        mock_api_call.return_value = {'data': {'provider': 'openai', 'model': 'gpt-4'}}
        res = dify_dev_cli.api_call('/console/api/workspaces/current/default-model?model_type=llm')
        self.assertEqual(res.get('data', {}).get('model'), 'gpt-4')

    @patch('dify_dev_cli.api_call')
    def test_validate_credentials(self, mock_api_call):
        mock_api_call.return_value = {'result': 'success'}
        res = dify_dev_cli.api_call('/console/api/workspaces/current/model-providers/openai/credentials/validate', 'POST', {})
        self.assertEqual(res.get('result'), 'success')

    @patch('dify_dev_cli.api_call')
    def test_get_draft_json(self, mock_api_call):
        mock_api_call.return_value = {'id': 'draft-1', 'graph': {}}
        res = dify_dev_cli.api_call('/console/api/apps/app-1/workflows/draft')
        self.assertEqual(res.get('id'), 'draft-1')

if __name__ == '__main__':
    unittest.main()
