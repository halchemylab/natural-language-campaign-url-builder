import unittest
from unittest.mock import patch, MagicMock
from utils import normalize_url, build_campaign_url, generate_campaign_data, validate_url_reachability

class TestUtils(unittest.TestCase):

    @patch('utils.requests.head')
    def test_validate_url_reachability_success(self, mock_head):
        mock_head.return_value.status_code = 200
        self.assertTrue(validate_url_reachability("https://example.com"))

    @patch('utils.requests.head')
    def test_validate_url_reachability_failure(self, mock_head):
        mock_head.return_value.status_code = 404
        self.assertFalse(validate_url_reachability("https://example.com/broken"))
        
    @patch('utils.requests.head')
    def test_validate_url_reachability_exception(self, mock_head):
        mock_head.side_effect = Exception("Connection error")
        self.assertFalse(validate_url_reachability("https://example.com/error"))

    @patch('utils.requests.head')
    @patch('utils.requests.get')
    def test_validate_url_reachability_fallback(self, mock_get, mock_head):
        # Simulate 405 on HEAD, then 200 on GET
        mock_head.return_value.status_code = 405
        mock_get.return_value.status_code = 200
        self.assertTrue(validate_url_reachability("https://example.com/protected"))
        mock_get.assert_called_once()

    def test_normalize_url(self):
        # Case: Already has https
        self.assertEqual(normalize_url("https://example.com"), "https://example.com")
        # Case: Already has http
        self.assertEqual(normalize_url("http://example.com"), "http://example.com")
        # Case: Missing scheme
        self.assertEqual(normalize_url("example.com"), "https://example.com")
        # Case: Missing scheme with path
        self.assertEqual(normalize_url("example.com/path"), "https://example.com/path")
        # Case: Empty string
        self.assertEqual(normalize_url(""), "")
        # Case: Whitespace
        self.assertEqual(normalize_url("  example.com  "), "https://example.com")

    def test_build_campaign_url_basic(self):
        base = "https://example.com"
        result = build_campaign_url(base, "google", "cpc", "spring_sale", None, None, None)
        self.assertIn("utm_source=google", result)
        self.assertIn("utm_medium=cpc", result)
        self.assertIn("utm_campaign=spring_sale", result)

    def test_build_campaign_url_with_existing_params(self):
        base = "https://example.com?existing=param"
        result = build_campaign_url(base, "google", "cpc", "spring_sale", None, None, None)
        self.assertIn("existing=param", result)
        self.assertIn("utm_source=google", result)

    def test_build_campaign_url_overwrite_params(self):
        base = "https://example.com?utm_source=old_source"
        result = build_campaign_url(base, "new_source", "cpc", "spring_sale", None, None, None)
        self.assertIn("utm_source=new_source", result)
        self.assertNotIn("utm_source=old_source", result)

    def test_build_campaign_url_all_params(self):
        base = "example.com" # Should be normalized
        result = build_campaign_url(
            base, "src", "med", "name", "id123", "term_here", "content_here"
        )
        self.assertTrue(result.startswith("https://example.com"))
        self.assertIn("utm_source=src", result)
        self.assertIn("utm_medium=med", result)
        self.assertIn("utm_campaign=name", result)
        self.assertIn("utm_id=id123", result)
        self.assertIn("utm_term=term_here", result)
        self.assertIn("utm_content=content_here", result)

    @patch('utils.OpenAI')
    def test_generate_campaign_data_success(self, mock_openai_cls):
        # Mock the client instance and its method chain
        mock_client = mock_openai_cls.return_value
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Mock the response content
        fake_response_content = """
        {
            "website_url": "https://example.com/promo",
            "campaign_source": "insta",
            "campaign_medium": "social",
            "campaign_name": "winter_sale",
            "campaign_id": null,
            "campaign_term": null,
            "campaign_content": null
        }
        """
        mock_completion.choices[0].message.content = fake_response_content
        
        # Call the function
        result = generate_campaign_data("test prompt", "fake_key", "gpt-4o-mini", 0.2)
        
        # Assertions
        self.assertEqual(result['website_url'], "https://example.com/promo")
        self.assertEqual(result['campaign_source'], "insta")
        self.assertEqual(result['campaign_medium'], "social")
        self.assertEqual(result['campaign_name'], "winter_sale")
        
    @patch('utils.OpenAI')
    def test_generate_campaign_data_validation_error(self, mock_openai_cls):
        # Test malformed JSON/schema violation handling
        mock_client = mock_openai_cls.return_value
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Missing required field 'campaign_source'
        bad_response = """
        {
            "website_url": "https://example.com",
            "campaign_medium": "email"
        }
        """
        mock_completion.choices[0].message.content = bad_response
        
        # Should raise ValidationError (propagated from Pydantic)
        with self.assertRaises(Exception): # Using generic Exception as we didn't import ValidationError here, but Pydantic raises it
            generate_campaign_data("test prompt", "fake_key", "gpt-4o-mini", 0.2)

if __name__ == "__main__":
    unittest.main()
