from src.blog.models import PublisherConfig
from src.blog.publisher.publisher import Publisher
from src.blog.publisher.webflow import WebflowPublisher


def create_publisher(config: PublisherConfig, token: str) -> Publisher:
    return WebflowPublisher(
        token=token,
        collection_id=config.collection_id,
        image_field=config.image_field,
    )
