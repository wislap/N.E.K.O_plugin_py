"""
通用 HTTP 客户端工具
封装了重试机制、错误处理和日志记录
"""
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class HTTPClient:
    """带重试和错误处理的 HTTP 客户端"""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        operation_name: str = "HTTP请求",
        retry_on_5xx: bool = True
    ) -> httpx.Response:
        """
        发送 HTTP 请求（带重试）
        
        Args:
            method: HTTP 方法 (GET, POST, etc.)
            url: 请求 URL
            headers: 请求头
            params: URL 参数
            json_data: JSON 请求体
            operation_name: 操作名称（用于日志）
            retry_on_5xx: 5xx 错误是否重试
            
        Returns:
            HTTP 响应
            
        Raises:
            httpx.HTTPStatusError: HTTP 错误
            httpx.RequestError: 网络错误
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"{operation_name} 尝试第 {attempt} 次: {method} {url}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_data,
                        timeout=self.timeout
                    )
                    
                    # 检查状态码
                    if response.status_code >= 500 and retry_on_5xx and attempt < self.max_retries:
                        logger.warning(f"{operation_name} 服务器错误 {response.status_code}，准备重试")
                        await asyncio.sleep(self.retry_delay * attempt)
                        continue
                    
                    response.raise_for_status()
                    logger.debug(f"{operation_name} 成功")
                    return response
                    
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"{operation_name} 第 {attempt} 次超时")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"{operation_name} 第 {attempt} 次网络错误: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    
            except Exception as e:
                last_exception = e
                logger.error(f"{operation_name} 第 {attempt} 次未知错误: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
        
        # 所有重试都失败
        logger.error(f"{operation_name} 在 {self.max_retries} 次尝试后失败")
        if last_exception:
            raise last_exception
        raise httpx.RequestError(f"{operation_name} 失败")
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        operation_name: str = "GET请求"
    ) -> httpx.Response:
        """发送 GET 请求"""
        return await self.request("GET", url, headers, params, operation_name=operation_name)
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        operation_name: str = "POST请求"
    ) -> httpx.Response:
        """发送 POST 请求"""
        return await self.request("POST", url, headers, json_data=json_data, operation_name=operation_name)


def handle_github_errors(func: Callable) -> Callable:
    """
    GitHub API 错误处理装饰器
    
    将 HTTP 错误转换为有意义的异常
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            
            if status_code == 404:
                raise ValueError("仓库不存在或无法访问")
            elif status_code == 403:
                error_data = e.response.json() if e.response.text else {}
                message = error_data.get("message", "")
                
                if "rate limit" in message.lower():
                    raise ValueError("GitHub API 速率限制 exceeded，请稍后重试")
                elif "abuse" in message.lower():
                    raise ValueError("请求被 GitHub 标记为滥用，请降低请求频率")
                else:
                    raise ValueError("访问被拒绝，请检查 GitHub Token 权限")
                    
            elif status_code == 401:
                raise ValueError("GitHub 认证失败，请检查 Token 是否有效")
            elif status_code == 500:
                raise ValueError("GitHub 服务器内部错误，请稍后重试")
            elif status_code == 502:
                raise ValueError("GitHub 服务暂时不可用，请稍后重试")
            elif status_code == 503:
                raise ValueError("GitHub 服务维护中，请稍后重试")
            else:
                raise ValueError(f"GitHub API 错误: {status_code}")
                
        except httpx.TimeoutException:
            raise ValueError("请求 GitHub API 超时，请检查网络连接")
        except httpx.RequestError as e:
            raise ValueError(f"无法连接到 GitHub: {str(e)}")
        except Exception as e:
            logger.error(f"GitHub API 调用异常: {str(e)}")
            raise ValueError("GitHub API 调用失败")
    
    return wrapper
