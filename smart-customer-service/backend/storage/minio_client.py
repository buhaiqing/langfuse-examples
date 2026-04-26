"""MinIO 对象存储客户端"""

import io

from core.config import settings
from minio import Minio
from minio.error import S3Error


class MinIOClient:
    """MinIO 客户端封装"""

    def __init__(self):
        self.client = None

    def connect(self):
        """连接 MinIO"""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

        buckets = self.client.list_buckets()
        bucket_names = [b.name for b in buckets]

        if settings.minio_bucket not in bucket_names:
            self.client.make_bucket(settings.minio_bucket)

    def upload_file(self, bucket: str, object_name: str, file_data: bytes):
        """上传文件"""
        try:
            self.client.put_object(bucket, object_name, io.BytesIO(file_data), len(file_data))
        except S3Error as e:
            raise Exception(f"MinIO upload failed: {e}") from e

    def download_file(self, bucket: str, object_name: str) -> bytes:
        """下载文件"""
        try:
            response = self.client.get_object(bucket, object_name)
            return response.read()
        except S3Error as e:
            raise Exception(f"MinIO download failed: {e}") from e

    def delete_file(self, bucket: str, object_name: str):
        """删除文件"""
        try:
            self.client.remove_object(bucket, object_name)
        except S3Error as e:
            raise Exception(f"MinIO delete failed: {e}") from e

    def list_files(self, bucket: str, prefix: str = "") -> list[str]:
        """列出文件"""
        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error:
            return []


minio_client = MinIOClient()
