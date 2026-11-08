"""Private storage for AI studio images (customer photos and results).

Nothing here is served from MEDIA_URL: files are streamed by the API to their owner (or staff) only.
Locally they live under AI_STUDIO_PRIVATE_ROOT (outside MEDIA_ROOT); in deployment set
AI_STUDIO_PRIVATE_BUCKET to keep them in a private S3/R2 bucket with no public URLs.
"""

import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible
from django.utils.functional import LazyObject


@deconstructible
class PrivateAIFileSystemStorage(FileSystemStorage):
    @property
    def location(self):
        return str(settings.AI_STUDIO_PRIVATE_ROOT)

    @property
    def base_location(self):
        return self.location

    @property
    def base_url(self):
        return None


def _bucket_storage(bucket: str) -> Storage:
    from storages.backends.s3 import S3Storage

    return S3Storage(
        bucket_name=bucket,
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
        default_acl="private",
        querystring_auth=True,
        file_overwrite=False,
        custom_domain=None,
        location="ai-studio",
    )


class _AIStorage(LazyObject):
    def _setup(self):
        bucket = settings.AI_STUDIO_PRIVATE_BUCKET
        self._wrapped = _bucket_storage(bucket) if bucket else PrivateAIFileSystemStorage()


ai_storage = _AIStorage()


def get_ai_storage():
    return ai_storage


def input_upload_to(instance, filename: str) -> str:
    return f"inputs/{instance.user_id}/{uuid.uuid4().hex}.jpg"


def result_upload_to(instance, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"results/{instance.user_id}/{uuid.uuid4().hex}.{extension}"
