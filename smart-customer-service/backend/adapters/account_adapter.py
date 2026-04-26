"""账户系统适配器"""

from typing import Any

from utils.api_client import APIClient


class AccountAPIClient(APIClient):
    """账户系统 API 客户端"""

    async def check_account_status(self, user_id: str) -> dict[str, Any]:
        """
        检查账户状态

        Args:
            user_id: 用户 ID

        Returns:
            账户状态信息
        """
        return await self.get(f"/api/v1/accounts/{user_id}/status")

    async def reset_password(self, user_id: str, channel: str = "email") -> dict[str, Any]:
        """
        重置密码

        Args:
            user_id: 用户 ID
            channel: 通知渠道 (email/sms)

        Returns:
            重置结果
        """
        return await self.post(
            f"/api/v1/accounts/{user_id}/password/reset",
            json={"channel": channel},
        )

    async def update_profile(self, user_id: str, profile_data: dict[str, Any]) -> dict[str, Any]:
        """更新用户资料"""
        return await self.put(
            f"/api/v1/accounts/{user_id}/profile",
            json=profile_data,
        )


class AccountService:
    """账户服务封装"""

    def __init__(self, base_url: str = ""):
        self.client = AccountAPIClient(base_url)

    async def check_status(self, user_id: str) -> dict[str, Any]:
        """检查账户状态"""
        return await self.client.check_account_status(user_id)

    async def reset_password(self, user_id: str, channel: str = "email"):
        """重置密码"""
        return await self.client.reset_password(user_id, channel)


account_service = AccountService()
