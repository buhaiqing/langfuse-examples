"""适配器模块"""

from adapters.account_adapter import account_service
from adapters.product_adapter import product_service
from adapters.monitoring_adapter import monitoring_service

__all__ = ["account_service", "product_service", "monitoring_service"]
