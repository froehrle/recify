"""Tests for tasks module (pika-based worker functions)"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pydantic import ValidationError
import json
from src.tasks import crawl_instagram_post, publish_raw_recipe_data
from src.models import CrawlRequest, RawRecipeData


class TestCrawlInstagramPost:
    """Test cases for crawl_instagram_post function"""

    @patch('src.tasks.publish_raw_recipe_data')
    @patch('src.tasks.InstagramCrawler')
    def test_successful_crawl_and_publish(self, mock_crawler_class, mock_publish):
        """Test successful Instagram post crawling and publishing"""
        # Given: Valid request data
        request_data = {
            'instagram_url': 'https://www.instagram.com/p/ABC123/',
            'request_id': 'req-123'
        }

        # Mock crawler instance and extracted data
        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler

        mock_raw_data = RawRecipeData(
            url='https://www.instagram.com/p/ABC123/',
            caption='Test recipe',
            media_urls=['https://example.com/image.jpg'],
            author='test_chef',
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            hashtags=['recipe', 'food'],
            mentions=[],
            likes_count=100,
            comments_count=10
        )
        mock_crawler.extract_post_data.return_value = mock_raw_data

        # When: Function processes the request successfully
        result = crawl_instagram_post(request_data)

        # Then: Should extract data and publish to next queue
        assert result['status'] == 'success'
        assert result['url'] == 'https://www.instagram.com/p/ABC123/'
        assert result['author'] == 'test_chef'
        assert result['caption_length'] == len('Test recipe')
        assert result['media_count'] == 1
        mock_publish.assert_called_once()

    def test_valid_request_data_structure(self):
        """Test function accepts properly formatted CrawlRequest data"""
        # Given: Request data with all required fields
        request_data = {
            'instagram_url': 'https://www.instagram.com/p/ABC123/',
            'request_id': 'req-456',
            'priority': 2
        }

        # When: Validating the request
        request = CrawlRequest(**request_data)

        # Then: Should create valid CrawlRequest object
        assert str(request.instagram_url) == 'https://www.instagram.com/p/ABC123/'
        assert request.request_id == 'req-456'
        assert request.priority == 2

    def test_invalid_request_data_missing_url(self):
        """Test function rejects request data without instagram_url"""
        # Given: Request data missing instagram_url field
        request_data = {
            'request_id': 'req-789'
        }

        # When/Then: Validation should raise ValidationError
        with pytest.raises(ValidationError):
            CrawlRequest(**request_data)

    @patch('src.tasks.publish_raw_recipe_data')
    @patch('src.tasks.InstagramCrawler')
    def test_crawler_extraction_failure(self, mock_crawler_class, mock_publish):
        """Test handling when crawler.extract_post_data raises exception"""
        # Given: Crawler that raises Exception during extraction
        request_data = {'instagram_url': 'https://www.instagram.com/p/FAIL/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Extraction failed')

        # When/Then: Function should raise the exception
        with pytest.raises(Exception) as exc_info:
            crawl_instagram_post(request_data)

        assert 'Extraction failed' in str(exc_info.value)
        # Should not call publish if extraction fails
        mock_publish.assert_not_called()


class TestPublishRawRecipeData:
    """Test cases for publish_raw_recipe_data function"""

    @patch('src.tasks.pika.BlockingConnection')
    def test_successful_data_publishing(self, mock_connection):
        """Test successful publishing of raw recipe data to RabbitMQ"""
        # Given: Valid raw_data dict
        raw_data = {
            'url': 'https://www.instagram.com/p/TEST/',
            'caption': 'Test recipe',
            'media_urls': ['https://example.com/img.jpg'],
            'author': 'test_user',
            'timestamp': '2025-01-15T12:00:00',
            'hashtags': ['recipe'],
            'mentions': []
        }

        # Mock RabbitMQ connection and channel
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel

        # When: Function publishes the data
        publish_raw_recipe_data(raw_data)

        # Then: Should publish to RabbitMQ
        mock_channel.queue_declare.assert_called_once_with(queue='raw_recipe_data', durable=True)
        mock_channel.basic_publish.assert_called_once()
        mock_connection.return_value.close.assert_called_once()

    @patch('src.tasks.pika.BlockingConnection')
    def test_message_published_with_correct_format(self, mock_connection):
        """Test message is published with correct JSON format"""
        # Given: Data with datetime timestamp
        raw_data = {
            'url': 'https://www.instagram.com/p/FORMAT/',
            'caption': 'Format test',
            'media_urls': ['img.jpg'],
            'author': 'format_user',
            'timestamp': datetime(2025, 1, 15, 16, 45, 30),
            'hashtags': [],
            'mentions': []
        }

        # Mock RabbitMQ
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel

        # When: Function publishes
        publish_raw_recipe_data(raw_data)

        # Then: Should publish JSON with ISO timestamp
        call_args = mock_channel.basic_publish.call_args
        published_body = call_args[1]['body']
        message = json.loads(published_body)

        assert message['url'] == 'https://www.instagram.com/p/FORMAT/'
        assert message['timestamp'] == '2025-01-15T16:45:30'  # ISO format

    @patch('src.tasks.pika.BlockingConnection')
    def test_message_persistence(self, mock_connection):
        """Test messages are published with persistence"""
        # Given: Valid data
        raw_data = {
            'url': 'https://www.instagram.com/p/PERSIST/',
            'caption': 'Persistence test',
            'media_urls': ['img.jpg'],
            'author': 'persist_user',
            'timestamp': '2025-01-15T12:00:00',
            'hashtags': [],
            'mentions': []
        }

        # Mock RabbitMQ
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel

        # When: Function publishes
        publish_raw_recipe_data(raw_data)

        # Then: Should publish with delivery_mode=2 (persistent)
        call_args = mock_channel.basic_publish.call_args
        properties = call_args[1]['properties']
        assert properties.delivery_mode == 2
        assert properties.content_type == 'application/json'

    def test_invalid_data_validation_error(self):
        """Test validation fails when required field is missing"""
        # Given: Data missing required field (e.g., 'url')
        raw_data = {
            'caption': 'Missing URL',
            'media_urls': ['img.jpg'],
            'author': 'missing_url',
            'timestamp': datetime.now(),
            'hashtags': [],
            'mentions': []
        }

        # When/Then: Should raise ValidationError
        with pytest.raises(ValidationError):
            publish_raw_recipe_data(raw_data)


class TestDataModels:
    """Test cases for data models"""

    def test_crawl_request_model(self):
        """Test CrawlRequest model validation"""
        # Given: Valid request data
        data = {
            'instagram_url': 'https://www.instagram.com/p/TEST123/',
            'request_id': 'test-request-1',
            'priority': 1
        }

        # When: Creating model
        request = CrawlRequest(**data)

        # Then: Should validate correctly
        assert str(request.instagram_url) == 'https://www.instagram.com/p/TEST123/'
        assert request.request_id == 'test-request-1'
        assert request.priority == 1

    def test_raw_recipe_data_model(self):
        """Test RawRecipeData model validation"""
        # Given: Valid recipe data
        data = {
            'url': 'https://www.instagram.com/p/RECIPE/',
            'caption': 'Delicious recipe',
            'media_urls': ['img1.jpg', 'img2.jpg'],
            'author': 'chef_user',
            'timestamp': datetime.now(),
            'hashtags': ['food', 'recipe'],
            'mentions': ['friend'],
            'likes_count': 100,
            'comments_count': 10
        }

        # When: Creating model
        recipe = RawRecipeData(**data)

        # Then: Should validate correctly
        assert recipe.url == 'https://www.instagram.com/p/RECIPE/'
        assert recipe.author == 'chef_user'
        assert len(recipe.media_urls) == 2
        assert recipe.likes_count == 100
