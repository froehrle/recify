import instaloader
from models import RawRecipeData
from typing import Optional
from config import INSTAGRAM_SESSION_FILE, INSTAGRAM_USERNAME
import os

class InstagramCrawler:
    def __init__(self, use_session: bool = True):
        self.loader = instaloader.Instaloader()
        # Configure instaloader for minimal footprint
        self.loader.download_pictures = False
        self.loader.download_videos = False
        self.loader.download_video_thumbnails = False

        # Try to load session if available and requested
        if use_session and INSTAGRAM_USERNAME and INSTAGRAM_SESSION_FILE:
            self._load_session_if_available()

    def _load_session_if_available(self):
        """Load Instagram session if available"""
        try:
            if os.path.exists(INSTAGRAM_SESSION_FILE):
                self.loader.load_session_from_file(INSTAGRAM_USERNAME, INSTAGRAM_SESSION_FILE)
                print(f"✅ Loaded Instagram session for {INSTAGRAM_USERNAME}")
            else:
                print(f"⚠️  No session file found at {INSTAGRAM_SESSION_FILE}, using anonymous access")
        except Exception as e:
            print(f"⚠️  Failed to load session: {e}, using anonymous access")

    def extract_post_data(self, instagram_url: str) -> RawRecipeData:
        """
        Extract post data from Instagram URL
        """
        try:
            # Extract shortcode from URL
            shortcode = self._extract_shortcode(instagram_url)

            # Get post using instaloader
            post = instaloader.Post.from_shortcode(
                self.loader.context,
                shortcode
            )

            # Extract relevant data
            raw_data = RawRecipeData(
                url=instagram_url,
                caption=post.caption or "",
                media_urls=self._extract_media_urls(post),
                author=post.owner_username,
                timestamp=post.date_utc,
                hashtags=list(post.caption_hashtags),
                mentions=list(post.caption_mentions),
                likes_count=post.likes,
                comments_count=post.comments,
                author_top_comment=self._extract_author_top_comment(post)
            )

            return raw_data

        except Exception as e:
            raise Exception(f"Failed to extract Instagram post: {str(e)}")

    def _extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Instagram URL"""
        # Handle various Instagram URL formats
        if '/p/' in url:
            return url.split('/p/')[-1].split('/')[0]
        elif '/reel/' in url:
            return url.split('/reel/')[-1].split('/')[0]
        else:
            raise ValueError(f"Invalid Instagram URL format: {url}")

    def _extract_media_urls(self, post) -> list[str]:
        """Extract media URLs from post"""
        media_urls = []
        if post.url:
            media_urls.append(post.url)
        # Handle carousel posts
        for node in post.get_sidecar_nodes():
            if node.display_url:
                media_urls.append(node.display_url)
        return media_urls

    def _extract_author_top_comment(self, post) -> Optional[str]:
        """Extract the author's most liked comment"""
        try:
            # Get comments from the post
            comments = post.get_comments()
            author_username = post.owner_username

            # Find all comments by the author
            author_comments = []
            for comment in comments:
                if comment.owner.username == author_username:
                    author_comments.append(comment)

            if not author_comments:
                return None

            # Find the comment with the most likes
            most_liked_comment = max(author_comments, key=lambda c: c.likes)
            return most_liked_comment.text

        except Exception:
            # If comments can't be fetched, return None
            return None