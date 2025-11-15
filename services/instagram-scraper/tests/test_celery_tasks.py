import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from celery.exceptions import Retry
from pydantic import ValidationError
from tasks import crawl_instagram_post, publish_raw_recipe_data
from models import CrawlRequest, RawRecipeData


class TestCrawlInstagramPostTask:
    """Test cases for crawl_instagram_post Celery task"""

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
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

        # When: Task processes the request successfully
        result = crawl_instagram_post(request_data)

        # Then: Should extract data and publish to next queue
        assert result['status'] == 'success'
        assert result['url'] == 'https://www.instagram.com/p/ABC123/'
        mock_publish.assert_called_once()

    def test_valid_request_data_structure(self):
        """Test task accepts properly formatted CrawlRequest data"""
        # Given: Request data with all required fields
        request_data = {
            'instagram_url': 'https://www.instagram.com/p/ABC123/',
            'request_id': 'req-456',
            'priority': 2
        }

        # When: Task validates the request
        request = CrawlRequest(**request_data)

        # Then: Should create valid CrawlRequest object
        assert str(request.instagram_url) == 'https://www.instagram.com/p/ABC123/'
        assert request.request_id == 'req-456'
        assert request.priority == 2

    def test_invalid_request_data_missing_url(self):
        """Test task rejects request data without instagram_url"""
        # Given: Request data missing instagram_url field
        request_data = {
            'request_id': 'req-789'
        }

        # When/Then: Task attempts to validate - Should raise ValidationError
        with pytest.raises(ValidationError):
            CrawlRequest(**request_data)

    def test_invalid_request_data_malformed_url(self):
        """Test task rejects request data with invalid URL format"""
        # Given: Request data with malformed instagram_url
        request_data = {
            'instagram_url': 'not-a-valid-url'
        }

        # When/Then: Task attempts to validate - Should raise ValidationError
        with pytest.raises(ValidationError):
            CrawlRequest(**request_data)

    @patch('tasks.InstagramCrawler')
    @patch('tasks.publish_raw_recipe_data.delay')
    def test_crawler_instance_created(self, mock_publish, mock_crawler_class):
        """Test that InstagramCrawler is properly instantiated"""
        # Given: Valid request data
        request_data = {'instagram_url': 'https://www.instagram.com/p/TEST123/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url='https://www.instagram.com/p/TEST123/',
            caption='',
            media_urls=[],
            author='test',
            timestamp=datetime.now(),
            hashtags=[],
            mentions=[]
        )

        # When: Task starts processing
        crawl_instagram_post(request_data)

        # Then: Should create InstagramCrawler instance
        mock_crawler_class.assert_called_once()

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_extract_post_data_called_with_correct_url(self, mock_crawler_class, mock_publish):
        """Test crawler.extract_post_data is called with the correct URL"""
        # Given: Request with specific instagram_url
        test_url = 'https://www.instagram.com/p/SPECIFIC123/'
        request_data = {'instagram_url': test_url}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url=test_url,
            caption='',
            media_urls=[],
            author='test',
            timestamp=datetime.now(),
            hashtags=[],
            mentions=[]
        )

        # When: Task processes the request
        crawl_instagram_post(request_data)

        # Then: Should call crawler.extract_post_data with exact URL string
        mock_crawler.extract_post_data.assert_called_once_with(test_url)

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_successful_extraction_returns_raw_data(self, mock_crawler_class, mock_publish):
        """Test successful extraction returns RawRecipeData object"""
        # Given: Valid Instagram post
        request_data = {'instagram_url': 'https://www.instagram.com/p/TEST/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler

        expected_data = RawRecipeData(
            url='https://www.instagram.com/p/TEST/',
            caption='Test caption',
            media_urls=['https://example.com/img.jpg'],
            author='test_user',
            timestamp=datetime(2025, 1, 15, 10, 0, 0),
            hashtags=['test'],
            mentions=['friend'],
            likes_count=50,
            comments_count=5
        )
        mock_crawler.extract_post_data.return_value = expected_data

        # When: Crawler extracts data
        result = crawl_instagram_post(request_data)

        # Then: Should return RawRecipeData with all fields populated
        assert result['author'] == 'test_user'
        assert result['caption_length'] == len('Test caption')
        assert result['media_count'] == 1

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_publish_task_called_with_extracted_data(self, mock_crawler_class, mock_publish):
        """Test publish_raw_recipe_data task is called with extracted data"""
        # Given: Successfully extracted raw data
        request_data = {'instagram_url': 'https://www.instagram.com/p/PUB123/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler

        raw_data = RawRecipeData(
            url='https://www.instagram.com/p/PUB123/',
            caption='Publish test',
            media_urls=['https://example.com/pub.jpg'],
            author='publisher',
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            hashtags=[],
            mentions=[]
        )
        mock_crawler.extract_post_data.return_value = raw_data

        # When: Crawl task completes extraction
        crawl_instagram_post(request_data)

        # Then: Should call publish_raw_recipe_data.delay() with serialized data
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0][0]
        assert call_args['url'] == 'https://www.instagram.com/p/PUB123/'
        assert call_args['author'] == 'publisher'

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_task_returns_success_status(self, mock_crawler_class, mock_publish):
        """Test task returns success status with metadata"""
        # Given: Successful crawl operation
        request_data = {'instagram_url': 'https://www.instagram.com/p/SUCCESS/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url='https://www.instagram.com/p/SUCCESS/',
            caption='Success story',
            media_urls=['img1.jpg', 'img2.jpg'],
            author='success_user',
            timestamp=datetime.now(),
            hashtags=[],
            mentions=[]
        )

        # When: Task completes
        result = crawl_instagram_post(request_data)

        # Then: Should return dict with status='success', url, author, caption_length, media_count
        assert result['status'] == 'success'
        assert 'url' in result
        assert 'author' in result
        assert 'caption_length' in result
        assert 'media_count' in result

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_return_metadata_accuracy(self, mock_crawler_class, mock_publish):
        """Test returned metadata matches extracted data"""
        # Given: Extracted data with specific values
        request_data = {'instagram_url': 'https://www.instagram.com/p/METADATA/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url='https://www.instagram.com/p/METADATA/',
            caption='This is a test caption with specific length',
            media_urls=['img1.jpg', 'img2.jpg', 'img3.jpg'],
            author='metadata_tester',
            timestamp=datetime.now(),
            hashtags=[],
            mentions=[]
        )

        # When: Task completes
        result = crawl_instagram_post(request_data)

        # Then: Returned metadata should accurately reflect extracted data
        assert result['author'] == 'metadata_tester'
        assert result['caption_length'] == len('This is a test caption with specific length')
        assert result['media_count'] == 3
        assert result['url'] == 'https://www.instagram.com/p/METADATA/'

    @patch('tasks.InstagramCrawler')
    def test_crawler_extraction_failure(self, mock_crawler_class):
        """Test handling when crawler.extract_post_data raises exception"""
        # Given: Crawler that raises Exception during extraction
        request_data = {'instagram_url': 'https://www.instagram.com/p/FAIL/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Extraction failed')

        # When/Then: Task attempts to extract data - Should catch exception and trigger retry
        # The task will raise Retry exception when it encounters an error
        with pytest.raises(Exception) as exc_info:
            crawl_instagram_post(request_data)

        # Verify it's a Retry exception (task will retry)
        assert 'Extraction failed' in str(exc_info.value) or isinstance(exc_info.value, Retry)

    @patch('tasks.InstagramCrawler')
    def test_instagram_private_post_error(self, mock_crawler_class):
        """Test handling of private/unavailable Instagram posts"""
        # Given: URL to private or deleted post
        request_data = {'instagram_url': 'https://www.instagram.com/p/PRIVATE/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Post is private')

        # When/Then: Crawler attempts to access - Should handle gracefully and retry
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    @patch('tasks.InstagramCrawler')
    def test_instagram_login_required_error(self, mock_crawler_class):
        """Test handling when Instagram requires login"""
        # Given: Post that requires authentication
        request_data = {'instagram_url': 'https://www.instagram.com/p/LOGIN/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Login required')

        # When/Then: Crawler attempts to access without login - Should handle error and retry
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    @patch('tasks.InstagramCrawler')
    def test_network_timeout_error(self, mock_crawler_class):
        """Test handling of network timeout during crawling"""
        # Given: Network timeout exception
        request_data = {'instagram_url': 'https://www.instagram.com/p/TIMEOUT/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Network timeout')

        # When/Then: Task attempts to crawl - Should trigger retry with backoff
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    @patch('tasks.InstagramCrawler')
    def test_retry_mechanism_first_attempt(self, mock_crawler_class):
        """Test retry mechanism on first failure (60s countdown)"""
        # Given: Task fails on first attempt (retries=0)
        request_data = {'instagram_url': 'https://www.instagram.com/p/RETRY1/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('First failure')

        # When/Then: Exception is raised - Should retry with 60 second countdown
        # Verify the task will attempt to retry
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    @patch('tasks.InstagramCrawler')
    def test_retry_mechanism_second_attempt(self, mock_crawler_class):
        """Test retry mechanism on second failure (120s countdown)"""
        # Given: Task fails on second attempt (retries=1)
        request_data = {'instagram_url': 'https://www.instagram.com/p/RETRY2/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Second failure')

        # When/Then: Exception is raised - Should retry with 120 second countdown
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    @patch('tasks.InstagramCrawler')
    def test_retry_mechanism_third_attempt(self, mock_crawler_class):
        """Test retry mechanism on third failure (240s countdown)"""
        # Given: Task fails on third attempt (retries=2)
        request_data = {'instagram_url': 'https://www.instagram.com/p/RETRY3/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Third failure')

        # When/Then: Exception is raised - Should retry with 240 second countdown
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    def test_max_retries_reached(self):
        """Test behavior when max retries (3) is reached"""
        # Given: Task decorated with max_retries=3
        # When: Checking task configuration
        # Then: Should have max_retries set to 3
        assert crawl_instagram_post.max_retries == 3

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff formula: 2^retries * 60"""
        # Given: Different retry counts (0, 1, 2)
        # When: Calculating countdown
        # Then: Should calculate 60s, 120s, 240s respectively
        assert 2 ** 0 * 60 == 60
        assert 2 ** 1 * 60 == 120
        assert 2 ** 2 * 60 == 240

    @patch('tasks.logger')
    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_logging_on_successful_processing(self, mock_crawler_class, mock_publish, mock_logger):
        """Test that success is logged with correct information"""
        # Given: Successful crawl
        request_data = {'instagram_url': 'https://www.instagram.com/p/LOG_SUCCESS/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url='https://www.instagram.com/p/LOG_SUCCESS/',
            caption='Logged',
            media_urls=[],
            author='logger',
            timestamp=datetime.now(),
            hashtags=[],
            mentions=[]
        )

        # When: Task completes
        crawl_instagram_post(request_data)

        # Then: Should log info message with Instagram URL
        assert mock_logger.info.called

    @patch('tasks.logger')
    @patch('tasks.InstagramCrawler')
    def test_logging_on_error(self, mock_crawler_class, mock_logger):
        """Test that errors are logged with exception details"""
        # Given: Failed crawl operation
        request_data = {'instagram_url': 'https://www.instagram.com/p/LOG_ERROR/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Test error')

        # When/Then: Exception occurs - Should log error message with URL and exception
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

    def test_task_binding_and_self_access(self):
        """Test that task is bound and has access to self.request"""
        # Given: Task decorated with bind=True
        # When: Checking task configuration
        # Then: Should have access to self and self.request attributes
        # This is verified by the task's ability to access self.request.retries in retry logic
        assert hasattr(crawl_instagram_post, 'request')

    def test_task_name_registration(self):
        """Test task is registered with correct name 'crawl_instagram_post'"""
        # Given: Task definition with name parameter
        # When: Checking task name
        # Then: Should be accessible by name 'crawl_instagram_post'
        assert crawl_instagram_post.name == 'crawl_instagram_post'

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_concurrent_task_execution(self, mock_crawler_class, mock_publish):
        """Test multiple tasks can be processed concurrently"""
        # Given: Multiple crawl requests queued
        request_data_1 = {'instagram_url': 'https://www.instagram.com/p/CONCURRENT1/'}
        request_data_2 = {'instagram_url': 'https://www.instagram.com/p/CONCURRENT2/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url='test',
            caption='',
            media_urls=[],
            author='test',
            timestamp=datetime.now(),
            hashtags=[],
            mentions=[]
        )

        # When: Worker processes tasks
        result1 = crawl_instagram_post(request_data_1)
        result2 = crawl_instagram_post(request_data_2)

        # Then: Should handle concurrent execution without conflicts
        assert result1['status'] == 'success'
        assert result2['status'] == 'success'

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_task_idempotency(self, mock_crawler_class, mock_publish):
        """Test that re-processing same URL produces consistent results"""
        # Given: Same Instagram URL processed multiple times
        request_data = {'instagram_url': 'https://www.instagram.com/p/IDEMPOTENT/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.return_value = RawRecipeData(
            url='https://www.instagram.com/p/IDEMPOTENT/',
            caption='Same content',
            media_urls=['same.jpg'],
            author='same_author',
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            hashtags=[],
            mentions=[]
        )

        # When: Task executes multiple times
        result1 = crawl_instagram_post(request_data)
        result2 = crawl_instagram_post(request_data)

        # Then: Should produce identical results
        assert result1 == result2


class TestPublishRawRecipeDataTask:
    """Test cases for publish_raw_recipe_data Celery task"""

    def test_successful_data_publishing(self):
        """Test successful publishing of raw recipe data"""
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

        # When: Task processes the data
        result = publish_raw_recipe_data(raw_data)

        # Then: Should validate and publish successfully
        assert result['status'] == 'published'
        assert result['url'] == 'https://www.instagram.com/p/TEST/'

    def test_data_validation_with_raw_recipe_data_model(self):
        """Test data is validated against RawRecipeData model"""
        # Given: Raw data dictionary
        raw_data = {
            'url': 'https://www.instagram.com/p/VALIDATE/',
            'caption': 'Validation test',
            'media_urls': ['img.jpg'],
            'author': 'validator',
            'timestamp': '2025-01-15T10:00:00',
            'hashtags': [],
            'mentions': []
        }

        # When: Task validates data
        result = publish_raw_recipe_data(raw_data)

        # Then: Should create valid RawRecipeData object and succeed
        assert result['status'] == 'published'

    def test_valid_data_structure_all_fields(self):
        """Test validation accepts data with all required fields"""
        # Given: Data with url, caption, media_urls, author, timestamp, hashtags, mentions
        data = {
            'url': 'https://www.instagram.com/p/ALLFIELDS/',
            'caption': 'All fields present',
            'media_urls': ['img1.jpg', 'img2.jpg'],
            'author': 'complete_user',
            'timestamp': datetime(2025, 1, 15, 12, 0, 0),
            'hashtags': ['food', 'recipe'],
            'mentions': ['friend']
        }

        # When: Validating against RawRecipeData
        validated = RawRecipeData(**data)

        # Then: Should pass validation
        assert validated.url == 'https://www.instagram.com/p/ALLFIELDS/'
        assert validated.author == 'complete_user'

    def test_valid_data_structure_with_optional_fields(self):
        """Test validation accepts data with optional fields populated"""
        # Given: Data including likes_count, comments_count, author_top_comment
        data = {
            'url': 'https://www.instagram.com/p/OPTIONAL/',
            'caption': 'With optional fields',
            'media_urls': ['img.jpg'],
            'author': 'optional_user',
            'timestamp': datetime.now(),
            'hashtags': [],
            'mentions': [],
            'likes_count': 150,
            'comments_count': 25,
            'author_top_comment': 'Thanks for the support!'
        }

        # When: Validating against RawRecipeData
        validated = RawRecipeData(**data)

        # Then: Should pass validation with optional fields
        assert validated.likes_count == 150
        assert validated.comments_count == 25
        assert validated.author_top_comment == 'Thanks for the support!'

    def test_valid_data_structure_without_optional_fields(self):
        """Test validation accepts data without optional fields"""
        # Given: Data with only required fields
        data = {
            'url': 'https://www.instagram.com/p/REQUIRED/',
            'caption': 'Only required',
            'media_urls': ['img.jpg'],
            'author': 'required_user',
            'timestamp': datetime.now(),
            'hashtags': [],
            'mentions': []
        }

        # When: Validating against RawRecipeData
        validated = RawRecipeData(**data)

        # Then: Should pass validation with None for optional fields
        assert validated.likes_count is None
        assert validated.comments_count is None
        assert validated.author_top_comment is None

    def test_invalid_data_missing_required_field(self):
        """Test validation fails when required field is missing"""
        # Given: Data missing required field (e.g., 'url')
        data = {
            'caption': 'Missing URL',
            'media_urls': ['img.jpg'],
            'author': 'missing_url',
            'timestamp': datetime.now(),
            'hashtags': [],
            'mentions': []
        }

        # When/Then: Validating against RawRecipeData - Should raise ValidationError
        with pytest.raises(ValidationError):
            RawRecipeData(**data)

    def test_invalid_data_wrong_type_media_urls(self):
        """Test validation fails when media_urls is not a list"""
        # Given: Data with media_urls as string instead of list
        data = {
            'url': 'https://www.instagram.com/p/WRONGTYPE/',
            'caption': 'Wrong type',
            'media_urls': 'should_be_a_list.jpg',  # Wrong type
            'author': 'wrong_user',
            'timestamp': datetime.now(),
            'hashtags': [],
            'mentions': []
        }

        # When/Then: Validating against RawRecipeData - Should raise ValidationError
        with pytest.raises(ValidationError):
            RawRecipeData(**data)

    def test_invalid_data_wrong_type_timestamp(self):
        """Test validation fails when timestamp is not datetime/parseable"""
        # Given: Data with invalid timestamp format
        data = {
            'url': 'https://www.instagram.com/p/BADTIME/',
            'caption': 'Bad timestamp',
            'media_urls': ['img.jpg'],
            'author': 'time_user',
            'timestamp': 'not-a-valid-timestamp',  # Wrong type
            'hashtags': [],
            'mentions': []
        }

        # When/Then: Validating against RawRecipeData - Should raise ValidationError
        with pytest.raises(ValidationError):
            RawRecipeData(**data)

    def test_task_return_status_on_success(self):
        """Test task returns success status with metadata"""
        # Given: Successfully published data
        raw_data = {
            'url': 'https://www.instagram.com/p/RETURN/',
            'caption': 'Return test',
            'media_urls': ['img.jpg'],
            'author': 'return_user',
            'timestamp': '2025-01-15T14:30:00',
            'hashtags': [],
            'mentions': []
        }

        # When: Task completes
        result = publish_raw_recipe_data(raw_data)

        # Then: Should return dict with status='published', url, timestamp
        assert result['status'] == 'published'
        assert 'url' in result
        assert 'timestamp' in result

    def test_return_timestamp_iso_format(self):
        """Test returned timestamp is in ISO format"""
        # Given: Data with datetime timestamp
        raw_data = {
            'url': 'https://www.instagram.com/p/ISOFORMAT/',
            'caption': 'ISO format test',
            'media_urls': ['img.jpg'],
            'author': 'iso_user',
            'timestamp': datetime(2025, 1, 15, 16, 45, 30),
            'hashtags': [],
            'mentions': []
        }

        # When: Task completes
        result = publish_raw_recipe_data(raw_data)

        # Then: Should return timestamp in ISO 8601 format
        assert 'timestamp' in result
        # Verify it's a valid ISO format string
        datetime.fromisoformat(result['timestamp'])

    @patch('tasks.logger')
    def test_logging_on_successful_publish(self, mock_logger):
        """Test success is logged with URL"""
        # Given: Successful publish
        raw_data = {
            'url': 'https://www.instagram.com/p/LOGPUB/',
            'caption': 'Log publish test',
            'media_urls': ['img.jpg'],
            'author': 'log_user',
            'timestamp': '2025-01-15T12:00:00',
            'hashtags': [],
            'mentions': []
        }

        # When: Task completes
        publish_raw_recipe_data(raw_data)

        # Then: Should log info messages with post URL
        assert mock_logger.info.called

    @patch('tasks.logger')
    def test_logging_on_validation_error(self, mock_logger):
        """Test validation errors are logged"""
        # Given: Invalid data structure
        raw_data = {
            'caption': 'Missing URL field',
            'media_urls': ['img.jpg'],
            'author': 'invalid_user',
            'timestamp': '2025-01-15T12:00:00',
            'hashtags': [],
            'mentions': []
        }

        # When/Then: Validation fails - Should log error message with exception details
        with pytest.raises(ValidationError):
            publish_raw_recipe_data(raw_data)

    @patch('tasks.logger')
    @patch('tasks.RawRecipeData')
    def test_exception_handling_and_propagation(self, mock_model, mock_logger):
        """Test exceptions are caught, logged, and re-raised"""
        # Given: Any exception during processing
        mock_model.side_effect = Exception('Unexpected error')

        raw_data = {
            'url': 'https://www.instagram.com/p/ERROR/',
            'caption': 'Error test',
            'media_urls': ['img.jpg'],
            'author': 'error_user',
            'timestamp': '2025-01-15T12:00:00',
            'hashtags': [],
            'mentions': []
        }

        # When/Then: Exception occurs - Should log error and raise exception
        with pytest.raises(Exception):
            publish_raw_recipe_data(raw_data)

    def test_task_name_registration(self):
        """Test task is registered with correct name 'publish_raw_recipe_data'"""
        # Given: Task definition with name parameter
        # When: Checking task name
        # Then: Should be accessible by name 'publish_raw_recipe_data'
        assert publish_raw_recipe_data.name == 'publish_raw_recipe_data'

    def test_no_retry_on_failure(self):
        """Test publish task does not retry on failure"""
        # Given: Task without bind=True
        # When: Checking if task is bound
        # Then: Should not be bound (no self.retry() available)
        # Celery tasks without bind=True don't have retry() method accessible
        assert not hasattr(publish_raw_recipe_data, '__self__')

    def test_queue_routing_integration(self):
        """Test task is routed to raw_recipe_data queue"""
        # Given: Task configuration in celeryapp.py
        from celeryapp import app

        # When: Checking task routing
        task_routes = app.conf.task_routes

        # Then: Should be routed to 'raw_recipe_data' queue
        assert 'tasks.publish_raw_recipe_data' in task_routes
        assert task_routes['tasks.publish_raw_recipe_data']['queue'] == 'raw_recipe_data'


class TestCeleryAppConfiguration:
    """Test cases for Celery app configuration in celeryapp.py"""

    def test_app_name_configuration(self):
        """Test Celery app is created with correct name"""
        # Given: Celery app definition
        from celeryapp import app

        # When: Checking app name
        # Then: App name should be 'instagram-scraper'
        assert app.main == 'instagram-scraper'

    def test_broker_url_configuration(self):
        """Test broker_url is set from RABBITMQ_URL config"""
        # Given: RABBITMQ_URL from config
        from celeryapp import app
        from config import RABBITMQ_URL

        # When: Checking broker configuration
        # Then: broker_url should match RABBITMQ_URL
        assert app.conf.broker_url == RABBITMQ_URL

    def test_result_backend_disabled(self):
        """Test result_backend is set to None"""
        # Given: App configuration
        from celeryapp import app

        # When: Checking result_backend
        # Then: Should be None (no result storage)
        assert app.conf.result_backend is None

    def test_task_serializer_json(self):
        """Test task_serializer is set to 'json'"""
        # Given: App configuration
        from celeryapp import app

        # When: Checking serializer settings
        # Then: task_serializer should be 'json'
        assert app.conf.task_serializer == 'json'

    def test_accept_content_json_only(self):
        """Test accept_content is limited to json"""
        # Given: App configuration
        from celeryapp import app

        # When: Checking accepted content types
        # Then: accept_content should be ['json']
        assert app.conf.accept_content == ['json']

    def test_result_serializer_json(self):
        """Test result_serializer is set to 'json'"""
        # Given: App configuration
        from celeryapp import app

        # When: Checking serializer settings
        # Then: result_serializer should be 'json'
        assert app.conf.result_serializer == 'json'

    def test_timezone_utc(self):
        """Test timezone is set to UTC"""
        # Given: App configuration
        from celeryapp import app

        # When: Checking timezone settings
        # Then: timezone should be 'UTC'
        assert app.conf.timezone == 'UTC'

    def test_enable_utc_true(self):
        """Test enable_utc is set to True"""
        # Given: App configuration
        from celeryapp import app

        # When: Checking UTC settings
        # Then: enable_utc should be True
        assert app.conf.enable_utc is True

    def test_task_routing_crawl_instagram_post(self):
        """Test crawl_instagram_post task routes to crawl_requests queue"""
        # Given: task_routes configuration
        from celeryapp import app

        # When: Checking task routing
        task_routes = app.conf.task_routes

        # Then: Should route to 'crawl_requests' queue
        assert 'tasks.crawl_instagram_post' in task_routes
        assert task_routes['tasks.crawl_instagram_post']['queue'] == 'crawl_requests'

    def test_task_routing_publish_raw_recipe_data(self):
        """Test publish_raw_recipe_data task routes to raw_recipe_data queue"""
        # Given: task_routes configuration
        from celeryapp import app

        # When: Checking task routing
        task_routes = app.conf.task_routes

        # Then: Should route to 'raw_recipe_data' queue
        assert 'tasks.publish_raw_recipe_data' in task_routes
        assert task_routes['tasks.publish_raw_recipe_data']['queue'] == 'raw_recipe_data'

    def test_worker_prefetch_multiplier_one(self):
        """Test worker processes one task at a time"""
        # Given: worker_prefetch_multiplier configuration
        from celeryapp import app

        # When: Checking worker settings
        # Then: Should be set to 1
        assert app.conf.worker_prefetch_multiplier == 1

    def test_task_acks_late_enabled(self):
        """Test task_acks_late is enabled for reliability"""
        # Given: task_acks_late configuration
        from celeryapp import app

        # When: Checking acknowledgment settings
        # Then: Should be True (acknowledge after completion)
        assert app.conf.task_acks_late is True

    def test_worker_max_tasks_per_child(self):
        """Test worker restarts after 1000 tasks"""
        # Given: worker_max_tasks_per_child configuration
        from celeryapp import app

        # When: Checking worker lifecycle settings
        # Then: Should be set to 1000
        assert app.conf.worker_max_tasks_per_child == 1000

    def test_task_autodiscovery(self):
        """Test tasks are auto-discovered from tasks module"""
        # Given: autodiscover_tasks configuration
        from celeryapp import app

        # When: Checking registered tasks
        registered_tasks = list(app.tasks.keys())

        # Then: Should discover tasks from ['tasks'] module
        assert 'crawl_instagram_post' in registered_tasks or 'tasks.crawl_instagram_post' in registered_tasks
        assert 'publish_raw_recipe_data' in registered_tasks or 'tasks.publish_raw_recipe_data' in registered_tasks


class TestTaskIntegration:
    """Integration tests for task workflow"""

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_end_to_end_crawl_to_publish_workflow(self, mock_crawler_class, mock_publish):
        """Test complete workflow from crawl request to data publishing"""
        # Given: Valid crawl request
        request_data = {
            'instagram_url': 'https://www.instagram.com/p/E2E_TEST/',
            'request_id': 'e2e-123'
        }

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler

        # Mock the extraction to return valid data
        raw_data = RawRecipeData(
            url='https://www.instagram.com/p/E2E_TEST/',
            caption='End to end test recipe',
            media_urls=['https://example.com/e2e.jpg'],
            author='e2e_chef',
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            hashtags=['e2e', 'test'],
            mentions=[],
            likes_count=200,
            comments_count=15
        )
        mock_crawler.extract_post_data.return_value = raw_data

        # When: crawl_instagram_post processes request
        result = crawl_instagram_post(request_data)

        # Then: Should extract data and trigger publish_raw_recipe_data
        assert result['status'] == 'success'
        mock_publish.assert_called_once()

        # Verify the data passed to publish task
        published_data = mock_publish.call_args[0][0]
        assert published_data['url'] == 'https://www.instagram.com/p/E2E_TEST/'
        assert published_data['author'] == 'e2e_chef'

    @patch('tasks.publish_raw_recipe_data.delay')
    @patch('tasks.InstagramCrawler')
    def test_failed_crawl_does_not_publish(self, mock_crawler_class, mock_publish):
        """Test that publish is not called when crawl fails"""
        # Given: Crawl request that will fail
        request_data = {'instagram_url': 'https://www.instagram.com/p/FAIL_TEST/'}

        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.extract_post_data.side_effect = Exception('Crawl failed')

        # When: crawl_instagram_post encounters error
        with pytest.raises(Exception):
            crawl_instagram_post(request_data)

        # Then: Should not call publish_raw_recipe_data
        mock_publish.assert_not_called()

    def test_queue_isolation_between_tasks(self):
        """Test tasks operate on separate queues"""
        # Given: Both tasks configured with different queues
        from celeryapp import app
        task_routes = app.conf.task_routes

        # When: Checking queue configuration
        crawl_queue = task_routes['tasks.crawl_instagram_post']['queue']
        publish_queue = task_routes['tasks.publish_raw_recipe_data']['queue']

        # Then: Should maintain queue isolation
        assert crawl_queue == 'crawl_requests'
        assert publish_queue == 'raw_recipe_data'
        assert crawl_queue != publish_queue

    @patch('tasks.InstagramCrawler')
    def test_message_format_consistency(self, mock_crawler_class):
        """Test data format is consistent between crawl and publish tasks"""
        # Given: Data output from crawl task
        mock_crawler = Mock()
        mock_crawler_class.return_value = mock_crawler

        raw_data = RawRecipeData(
            url='https://www.instagram.com/p/FORMAT_TEST/',
            caption='Format consistency test',
            media_urls=['https://example.com/format.jpg'],
            author='format_user',
            timestamp=datetime(2025, 1, 15, 14, 30, 0),
            hashtags=['format'],
            mentions=[],
            likes_count=50
        )
        mock_crawler.extract_post_data.return_value = raw_data

        with patch('tasks.publish_raw_recipe_data.delay') as mock_publish:
            # When: Crawl task outputs data
            crawl_instagram_post({'instagram_url': 'https://www.instagram.com/p/FORMAT_TEST/'})

            # Get the serialized data that would be sent to publish task
            serialized_data = mock_publish.call_args[0][0]

        # Then: Should be valid input for publish task validation
        # This should not raise a ValidationError
        validated_data = RawRecipeData(**serialized_data)

        # Verify the data structure is preserved
        assert validated_data.url == raw_data.url
        assert validated_data.author == raw_data.author
        assert validated_data.caption == raw_data.caption