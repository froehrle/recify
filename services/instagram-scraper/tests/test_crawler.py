import pytest
from unittest.mock import Mock
from instagram_crawler import InstagramCrawler

class TestInstagramCrawler:
    """Unit tests for InstagramCrawler methods"""

    def setup_method(self):
        """Set up test fixtures"""
        self.crawler = InstagramCrawler()

    def test_extract_shortcode_post_url_with_slash(self):
        """Test shortcode extraction from post URL with trailing slash"""
        url = "https://www.instagram.com/p/ABC123DEF456/"
        result = self.crawler._extract_shortcode(url)
        assert result == "ABC123DEF456"

    def test_extract_shortcode_post_url_without_slash(self):
        """Test shortcode extraction from post URL without trailing slash"""
        url = "https://www.instagram.com/p/XYZ789ABC123"
        result = self.crawler._extract_shortcode(url)
        assert result == "XYZ789ABC123"

    def test_extract_shortcode_reel_url_with_slash(self):
        """Test shortcode extraction from reel URL with trailing slash"""
        url = "https://www.instagram.com/reel/REEL123456/"
        result = self.crawler._extract_shortcode(url)
        assert result == "REEL123456"

    def test_extract_shortcode_reel_url_without_slash(self):
        """Test shortcode extraction from reel URL without trailing slash"""
        url = "https://www.instagram.com/reel/REEL789XYZ"
        result = self.crawler._extract_shortcode(url)
        assert result == "REEL789XYZ"

    def test_extract_shortcode_invalid_url_format(self):
        """Test error handling for invalid URL format"""
        invalid_urls = [
            "https://www.facebook.com/post/123",
            "https://instagram.com/user/",
            "https://www.instagram.com/stories/user/123",
            "not-a-url",
            ""
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid Instagram URL format"):
                self.crawler._extract_shortcode(url)

    def test_extract_media_urls_single_image(self):
        """Test media URL extraction for single image post"""
        mock_post = Mock()
        mock_post.url = "https://instagram.com/single_image.jpg"
        mock_post.get_sidecar_nodes.return_value = []

        result = self.crawler._extract_media_urls(mock_post)

        assert result == ["https://instagram.com/single_image.jpg"]

    def test_extract_media_urls_carousel_post(self):
        """Test media URL extraction for carousel post"""
        mock_post = Mock()
        mock_post.url = "https://instagram.com/image1.jpg"

        # Mock carousel nodes
        mock_node1 = Mock()
        mock_node1.display_url = "https://instagram.com/image2.jpg"

        mock_node2 = Mock()
        mock_node2.display_url = "https://instagram.com/image3.jpg"

        mock_post.get_sidecar_nodes.return_value = [mock_node1, mock_node2]

        result = self.crawler._extract_media_urls(mock_post)

        expected = [
            "https://instagram.com/image1.jpg",
            "https://instagram.com/image2.jpg",
            "https://instagram.com/image3.jpg"
        ]
        assert result == expected

    def test_extract_media_urls_no_main_url(self):
        """Test media URL extraction when main post URL is None"""
        mock_post = Mock()
        mock_post.url = None

        mock_node = Mock()
        mock_node.display_url = "https://instagram.com/carousel_only.jpg"
        mock_post.get_sidecar_nodes.return_value = [mock_node]

        result = self.crawler._extract_media_urls(mock_post)

        assert result == ["https://instagram.com/carousel_only.jpg"]

    def test_extract_author_top_comment_found(self):
        """Test author comment extraction when author has commented"""
        mock_post = Mock()
        mock_post.owner_username = "chef_test"

        # Mock comments with author comment
        mock_comment1 = Mock()
        mock_comment1.owner.username = "random_user"
        mock_comment1.text = "Looks delicious!"

        mock_author_comment = Mock()
        mock_author_comment.owner.username = "chef_test"
        mock_author_comment.text = "Thanks! Here's the recipe: mix, cook, enjoy!"
        mock_author_comment.likes = 25

        mock_comment2 = Mock()
        mock_comment2.owner.username = "another_user"
        mock_comment2.text = "Great post!"

        mock_post.get_comments.return_value = [
            mock_comment1,
            mock_author_comment,
            mock_comment2
        ]

        result = self.crawler._extract_author_top_comment(mock_post)

        assert result == "Thanks! Here's the recipe: mix, cook, enjoy!"

    def test_extract_author_top_comment_not_found(self):
        """Test author comment extraction when author hasn't commented"""
        mock_post = Mock()
        mock_post.owner_username = "chef_test"

        # Mock comments without author comment
        mock_comment1 = Mock()
        mock_comment1.owner.username = "fan1"
        mock_comment1.text = "Love this!"

        mock_comment2 = Mock()
        mock_comment2.owner.username = "fan2"
        mock_comment2.text = "Amazing recipe!"

        mock_post.get_comments.return_value = [mock_comment1, mock_comment2]

        result = self.crawler._extract_author_top_comment(mock_post)

        assert result is None

    def test_extract_author_top_comment_no_comments(self):
        """Test author comment extraction when no comments exist"""
        mock_post = Mock()
        mock_post.owner_username = "chef_test"
        mock_post.get_comments.return_value = []

        result = self.crawler._extract_author_top_comment(mock_post)

        assert result is None

    def test_extract_author_top_comment_comments_error(self):
        """Test author comment extraction when comments API fails"""
        mock_post = Mock()
        mock_post.owner_username = "chef_test"
        mock_post.get_comments.side_effect = Exception("Comments disabled")

        result = self.crawler._extract_author_top_comment(mock_post)

        assert result is None

    def test_extract_author_top_comment_returns_most_liked_comment(self):
        """Test that most liked author comment is returned when multiple exist"""
        mock_post = Mock()
        mock_post.owner_username = "chef_test"

        # Multiple author comments with different like counts
        mock_author_comment1 = Mock()
        mock_author_comment1.owner.username = "chef_test"
        mock_author_comment1.text = "First author comment"
        mock_author_comment1.likes = 5

        mock_other_comment = Mock()
        mock_other_comment.owner.username = "fan"
        mock_other_comment.text = "Fan comment"
        mock_other_comment.likes = 10

        mock_author_comment2 = Mock()
        mock_author_comment2.owner.username = "chef_test"
        mock_author_comment2.text = "Most liked author comment"
        mock_author_comment2.likes = 25  # Highest likes

        mock_author_comment3 = Mock()
        mock_author_comment3.owner.username = "chef_test"
        mock_author_comment3.text = "Another author comment"
        mock_author_comment3.likes = 15

        mock_post.get_comments.return_value = [
            mock_author_comment1,
            mock_other_comment,
            mock_author_comment2,
            mock_author_comment3
        ]

        result = self.crawler._extract_author_top_comment(mock_post)

        # Should return the most liked author comment
        assert result == "Most liked author comment"