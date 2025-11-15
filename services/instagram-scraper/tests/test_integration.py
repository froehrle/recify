import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from instagram_crawler import InstagramCrawler
from models import RawRecipeData

class TestInstagramCrawlerIntegration:
    """Integration tests for Instagram post caption extraction"""

    def setup_method(self):
        """Set up test fixtures"""
        self.crawler = InstagramCrawler()

    @patch('instagram_crawler.instaloader.Post.from_shortcode')
    def test_instagram_post_extraction_with_caption(self, mock_from_shortcode):
        """
        Integration test: Input Instagram URL, expect caption extraction
        """
        # Mock Instagram post data
        mock_post = Mock()
        mock_post.caption = "Delicious pasta recipe! 🍝 #pasta #recipe #cooking"
        mock_post.owner_username = "chef_test"
        mock_post.date_utc = datetime(2024, 1, 15, 10, 30, 0)
        mock_post.caption_hashtags = {"pasta", "recipe", "cooking"}
        mock_post.caption_mentions = set()
        mock_post.likes = 150
        mock_post.comments = 25
        mock_post.url = "https://instagram.com/media1.jpg"
        mock_post.get_sidecar_nodes.return_value = []

        # Mock author comment
        mock_comment = Mock()
        mock_comment.owner.username = "chef_test"
        mock_comment.text = "Here's the full recipe: 1. Boil pasta 2. Make sauce 3. Combine!"
        mock_comment.likes = 50
        mock_post.get_comments.return_value = [mock_comment]

        mock_from_shortcode.return_value = mock_post

        # Test URL
        test_url = "https://www.instagram.com/p/ABC123DEF456/"

        # Execute extraction
        result = self.crawler.extract_post_data(test_url)

        # Assertions
        assert isinstance(result, RawRecipeData)
        assert result.url == test_url
        assert result.caption == "Delicious pasta recipe! 🍝 #pasta #recipe #cooking"
        assert result.author == "chef_test"
        assert set(result.hashtags) == {"pasta", "recipe", "cooking"}
        assert result.mentions == []
        assert result.likes_count == 150
        assert result.comments_count == 25
        assert result.media_urls == ["https://instagram.com/media1.jpg"]
        assert result.author_top_comment == "Here's the full recipe: 1. Boil pasta 2. Make sauce 3. Combine!"

    @patch('instagram_crawler.instaloader.Post.from_shortcode')
    def test_instagram_reel_extraction(self, mock_from_shortcode):
        """Test extraction from Instagram Reel URL"""
        # Mock Instagram reel data
        mock_post = Mock()
        mock_post.caption = "Quick recipe reel! #quickrecipe"
        mock_post.owner_username = "food_creator"
        mock_post.date_utc = datetime(2024, 1, 16, 12, 0, 0)
        mock_post.caption_hashtags = {"quickrecipe"}
        mock_post.caption_mentions = set()
        mock_post.likes = 500
        mock_post.comments = 50
        mock_post.url = "https://instagram.com/reel_video.mp4"
        mock_post.get_sidecar_nodes.return_value = []
        mock_post.get_comments.return_value = []

        mock_from_shortcode.return_value = mock_post

        # Test Reel URL
        test_url = "https://www.instagram.com/reel/XYZ789ABC123/"

        # Execute extraction
        result = self.crawler.extract_post_data(test_url)

        # Assertions
        assert result.url == test_url
        assert result.caption == "Quick recipe reel! #quickrecipe"
        assert result.author == "food_creator"
        assert result.hashtags == ["quickrecipe"]
        assert result.author_top_comment is None  # No author comments

    @patch('instagram_crawler.instaloader.Post.from_shortcode')
    def test_instagram_carousel_post_extraction(self, mock_from_shortcode):
        """Test extraction from carousel post with multiple media"""
        # Mock carousel post
        mock_post = Mock()
        mock_post.caption = "Step-by-step recipe photos #tutorial"
        mock_post.owner_username = "recipe_master"
        mock_post.date_utc = datetime(2024, 1, 17, 14, 30, 0)
        mock_post.caption_hashtags = {"tutorial"}
        mock_post.caption_mentions = set()
        mock_post.likes = 300
        mock_post.comments = 15
        mock_post.url = "https://instagram.com/media1.jpg"

        # Mock carousel nodes
        mock_node1 = Mock()
        mock_node1.display_url = "https://instagram.com/media2.jpg"
        mock_node2 = Mock()
        mock_node2.display_url = "https://instagram.com/media3.jpg"
        mock_post.get_sidecar_nodes.return_value = [mock_node1, mock_node2]
        mock_post.get_comments.return_value = []

        mock_from_shortcode.return_value = mock_post

        test_url = "https://www.instagram.com/p/CAROUSEL123/"

        result = self.crawler.extract_post_data(test_url)

        # Should include all media URLs
        expected_media_urls = [
            "https://instagram.com/media1.jpg",
            "https://instagram.com/media2.jpg",
            "https://instagram.com/media3.jpg"
        ]
        assert result.media_urls == expected_media_urls

    def test_extract_shortcode_from_post_url(self):
        """Test shortcode extraction from various URL formats"""
        # Regular post URL
        post_url = "https://www.instagram.com/p/ABC123DEF456/"
        shortcode = self.crawler._extract_shortcode(post_url)
        assert shortcode == "ABC123DEF456"

        # Post URL without trailing slash
        post_url_no_slash = "https://www.instagram.com/p/XYZ789"
        shortcode = self.crawler._extract_shortcode(post_url_no_slash)
        assert shortcode == "XYZ789"

    def test_extract_shortcode_from_reel_url(self):
        """Test shortcode extraction from reel URL"""
        reel_url = "https://www.instagram.com/reel/REEL123456/"
        shortcode = self.crawler._extract_shortcode(reel_url)
        assert shortcode == "REEL123456"

    def test_extract_shortcode_invalid_url(self):
        """Test error handling for invalid URL formats"""
        with pytest.raises(ValueError, match="Invalid Instagram URL format"):
            self.crawler._extract_shortcode("https://www.facebook.com/invalid")

    @patch('instagram_crawler.instaloader.Post.from_shortcode')
    def test_instagram_post_extraction_network_error(self, mock_from_shortcode):
        """Test error handling when Instagram API fails"""
        # Mock network error
        mock_from_shortcode.side_effect = Exception("Network error")

        test_url = "https://www.instagram.com/p/NETWORKERROR/"

        # Should raise exception with descriptive message
        with pytest.raises(Exception, match="Failed to extract Instagram post: Network error"):
            self.crawler.extract_post_data(test_url)

    @patch('instagram_crawler.instaloader.Post.from_shortcode')
    def test_instagram_post_no_caption(self, mock_from_shortcode):
        """Test handling posts without captions"""
        mock_post = Mock()
        mock_post.caption = None  # No caption
        mock_post.owner_username = "silent_chef"
        mock_post.date_utc = datetime(2024, 1, 18, 9, 0, 0)
        mock_post.caption_hashtags = set()
        mock_post.caption_mentions = set()
        mock_post.likes = 10
        mock_post.comments = 2
        mock_post.url = "https://instagram.com/no_caption.jpg"
        mock_post.get_sidecar_nodes.return_value = []
        mock_post.get_comments.return_value = []

        mock_from_shortcode.return_value = mock_post

        test_url = "https://www.instagram.com/p/NOCAPTION123/"

        result = self.crawler.extract_post_data(test_url)

        # Should handle None caption gracefully
        assert result.caption == ""
        assert result.hashtags == []
        assert result.mentions == []

    @patch('instagram_crawler.instaloader.Post.from_shortcode')
    def test_author_comment_extraction_comments_disabled(self, mock_from_shortcode):
        """Test handling when comments are disabled"""
        mock_post = Mock()
        mock_post.caption = "Recipe post"
        mock_post.owner_username = "private_chef"
        mock_post.date_utc = datetime(2024, 1, 19, 11, 0, 0)
        mock_post.caption_hashtags = set()
        mock_post.caption_mentions = set()
        mock_post.likes = 25
        mock_post.comments = 0
        mock_post.url = "https://instagram.com/private.jpg"
        mock_post.get_sidecar_nodes.return_value = []

        # Comments disabled/error
        mock_post.get_comments.side_effect = Exception("Comments disabled")

        mock_from_shortcode.return_value = mock_post

        test_url = "https://www.instagram.com/p/PRIVATE123/"

        result = self.crawler.extract_post_data(test_url)

        # Should handle comments error gracefully
        assert result.author_top_comment is None