import unittest
from utils import normalize_url, build_campaign_url

class TestUtils(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()
