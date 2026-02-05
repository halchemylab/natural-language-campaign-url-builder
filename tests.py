import pytest
from unittest.mock import patch, MagicMock
from utils import normalize_url, build_campaign_url, generate_campaign_data, validate_url_reachability, lint_utm_parameter

class TestUtils:

    def test_lint_utm_parameter(self):
        # Case: Clean parameter
        assert lint_utm_parameter("google") == []
        assert lint_utm_parameter("spring_sale") == []
        assert lint_utm_parameter("summer-2024") == []
        
        # Case: Uppercase
        warnings = lint_utm_parameter("Google")
        assert any("uppercase" in w for w in warnings)
        
        # Case: Spaces
        warnings = lint_utm_parameter("spring sale")
        assert any("spaces" in w for w in warnings)
        
        # Case: Special characters
        warnings = lint_utm_parameter("sale!")
        assert any("special characters" in w for w in warnings)
        
        # Case: Multiple issues
        warnings = lint_utm_parameter("Spring Sale!")
        assert len(warnings) == 3

    @patch('utils.requests.head')
    def test_validate_url_reachability_success(self, mock_head):
        mock_head.return_value.status_code = 200
        assert validate_url_reachability("https://example.com") is True

    @patch('utils.requests.head')
    def test_validate_url_reachability_failure(self, mock_head):
        mock_head.return_value.status_code = 404
        assert validate_url_reachability("https://example.com/broken") is False
        
    @patch('utils.requests.head')
    def test_validate_url_reachability_exception(self, mock_head):
        mock_head.side_effect = Exception("Connection error")
        assert validate_url_reachability("https://example.com/error") is False

    @patch('utils.requests.head')
    @patch('utils.requests.get')
    def test_validate_url_reachability_fallback(self, mock_get, mock_head):
        # Simulate 405 on HEAD, then 200 on GET
        mock_head.return_value.status_code = 405
        mock_get.return_value.status_code = 200
        assert validate_url_reachability("https://example.com/protected") is True
        mock_get.assert_called_once()

    def test_normalize_url(self):
        # Case: Already has https
        assert normalize_url("https://example.com") == "https://example.com"
        # Case: Already has http
        assert normalize_url("http://example.com") == "http://example.com"
        # Case: Missing scheme
        assert normalize_url("example.com") == "https://example.com"
        # Case: Missing scheme with path
        assert normalize_url("example.com/path") == "https://example.com/path"
        # Case: Empty string
        assert normalize_url("") == ""
        # Case: Whitespace
        assert normalize_url("  example.com  ") == "https://example.com"

    def test_build_campaign_url_basic(self):
        base = "https://example.com"
        result = build_campaign_url(base, "google", "cpc", "spring_sale", None, None, None)
        assert "utm_source=google" in result
        assert "utm_medium=cpc" in result
        assert "utm_campaign=spring_sale" in result

    def test_build_campaign_url_with_existing_params(self):
        base = "https://example.com?existing=param"
        result = build_campaign_url(base, "google", "cpc", "spring_sale", None, None, None)
        assert "existing=param" in result
        assert "utm_source=google" in result

    def test_build_campaign_url_overwrite_params(self):
        base = "https://example.com?utm_source=old_source"
        result = build_campaign_url(base, "new_source", "cpc", "spring_sale", None, None, None)
        assert "utm_source=new_source" in result
        assert "utm_source=old_source" not in result

    def test_build_campaign_url_all_params(self):
        base = "example.com" # Should be normalized
        result = build_campaign_url(
            base, "src", "med", "name", "id123", "term_here", "content_here"
        )
        assert result.startswith("https://example.com")
        assert "utm_source=src" in result
        assert "utm_medium=med" in result
        assert "utm_campaign=name" in result
        assert "utm_id=id123" in result
        assert "utm_term=term_here" in result
        assert "utm_content=content_here" in result

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
        assert result['website_url'] == "https://example.com/promo"
        assert result['campaign_source'] == "insta"
        assert result['campaign_medium'] == "social"
        assert result['campaign_name'] == "winter_sale"
        
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
        
        # Should raise exception
        with pytest.raises(Exception): 
            generate_campaign_data("test prompt", "fake_key", "gpt-4o-mini", 0.2)