"""
E2E 测试运行脚本

提供:
- 测试环境检查
- 测试执行入口
- 结果报告生成
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


def check_dependencies():
    """检查测试依赖"""
    print("=== 检查测试依赖 ===")

    required_packages = [
        "pytest",
        "pytest-asyncio",
        "httpx",
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing.append(package)

    if missing:
        print(f"\n请安装缺失的依赖: pip install {', '.join(missing)}")
        return False

    # 检查可选依赖
    optional_packages = ["playwright", "websockets"]
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装（可选）")
        except ImportError:
            print(f"⚠️  {package} 未安装（可选，部分测试可能跳过）")

    return True


def check_service_health():
    """检查后端服务健康状态"""
    print("\n=== 检查后端服务 ===")

    import httpx

    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")

    try:
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            response = client.get("/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 后端服务健康: {data.get('status', 'unknown')}")
                print(f"   Redis: {data.get('redis', 'unknown')}")
                return True
            else:
                print(f"❌ 后端服务返回错误: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ 后端服务不可达: {e}")
        print(f"   请确保后端服务在 {base_url} 运行")
        return False


def run_tests(test_type: str = "all", verbose: bool = True):
    """运行 E2E 测试

    Args:
        test_type: 测试类型 (all, user, agent, integration, api)
        verbose: 是否详细输出
    """
    print("\n=== 运行 E2E 测试 ===")
    print(f"测试类型: {test_type}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 构建测试命令
    pytest_args = ["pytest"]

    if verbose:
        pytest_args.append("-v")

    # 选择测试文件
    test_dir = Path(__file__).parent

    if test_type == "all":
        pytest_args.append(str(test_dir))
    elif test_type == "user":
        pytest_args.append(str(test_dir / "test_user_flow.py"))
    elif test_type == "agent":
        pytest_args.append(str(test_dir / "test_agent_flow.py"))
    elif test_type == "integration":
        pytest_args.append(str(test_dir / "test_integration.py"))
    elif test_type == "api":
        pytest_args.append(str(test_dir / "test_api.py"))
    else:
        print(f"未知测试类型: {test_type}")
        return False

    # 添加报告选项
    pytest_args.extend([
        "--tb=short",
        "-W", "ignore::DeprecationWarning",
    ])

    print(f"命令: {' '.join(pytest_args)}")
    print()

    # 运行测试
    result = subprocess.run(pytest_args, cwd=str(test_dir))

    print("\n=== 测试完成 ===")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"返回码: {result.returncode}")

    return result.returncode == 0


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="E2E 测试运行器")
    parser.add_argument(
        "--type",
        choices=["all", "user", "agent", "integration", "api"],
        default="all",
        help="测试类型",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出",
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="跳过健康检查",
    )

    args = parser.parse_args()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 检查服务健康
    if not args.skip_health_check:
        if not check_service_health():
            print("\n⚠️  后端服务不可用，测试可能失败")
            print("   可以使用 --skip-health-check 跳过检查")

    # 运行测试
    success = run_tests(args.type, args.verbose)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()