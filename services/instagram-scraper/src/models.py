from pydantic import BaseModel, HttpUrl, ConfigDict, field_serializer
from datetime import datetime
from typing import List, Optional

class CrawlRequest(BaseModel):
    instagram_url: HttpUrl
    request_id: Optional[str] = None
    priority: int = 1

class RawRecipeData(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    url: str
    caption: str
    media_urls: List[str]
    author: str
    timestamp: datetime
    hashtags: List[str]
    mentions: List[str]
    likes_count: Optional[int] = None
    comments_count: Optional[int] = None
    author_top_comment: Optional[str] = None  # Most liked comment by the post author

    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime) -> str:
        return dt.isoformat()