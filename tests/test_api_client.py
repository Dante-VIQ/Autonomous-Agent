# tests/test_api_client.py

import importlib
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.api_client import LaravelApiClient
from src.config import Config

class TestLaravelApiClient(unittest.TestCase):
    
    def setUp(self):
        self.client = LaravelApiClient()
    
    @patch('src.utils.api_client.requests.Session.request')
    def test_get_opportunities(self, mock_request):
        """Test fetching opportunities."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"opportunities": [{"id": 1, "type": "seo_issue"}]}
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.get_opportunities(1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "seo_issue")
    
    @patch('src.utils.api_client.requests.Session.request')
    def test_get_analytics(self, mock_request):
        """Test fetching analytics."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"visitors": 1000, "conversions": 50}
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.get_analytics(1)
        self.assertEqual(result["visitors"], 1000)
        self.assertEqual(result["conversions"], 50)

    @patch('src.utils.api_client.requests.Session.request')
    def test_get_seo_recommendations(self, mock_request):
        """Test fetching SEO recommendations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"recommendations": [{"priority": "high", "action": "rewrite meta title"}]}
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = self.client.get_seo_recommendations(1, "issue-123")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "rewrite meta title")

    def test_main_module_imports(self):
        """The application entry point should import cleanly as a package."""
        module = importlib.import_module('src.main')
        self.assertTrue(hasattr(module, 'run_cycle'))

if __name__ == '__main__':
    unittest.main()