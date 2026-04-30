"""
插件验证工具
用于验证插件仓库命名规范等
"""
import re
from typing import Tuple, Optional


class PluginValidator:
    """插件验证器"""
    
    # 插件仓库命名规范：n.e.k.o_plugin_xxx
    PLUGIN_REPO_PATTERN = re.compile(r'^n\.e\.k\.o_plugin_[a-z0-9_]+$', re.IGNORECASE)
    
    @staticmethod
    def validate_repo_name(repo_name: str) -> Tuple[bool, Optional[str]]:
        """
        验证插件仓库名称是否符合规范
        
        Args:
            repo_name: 仓库名称，如 "n.e.k.o_plugin_mijia"
            
        Returns:
            (是否有效, 错误信息)
        """
        if not repo_name:
            return False, "仓库名称不能为空"
        
        # 检查基本格式
        if not PluginValidator.PLUGIN_REPO_PATTERN.match(repo_name):
            return False, (
                "仓库名称不符合规范。"
                "正确格式：n.e.k.o_plugin_xxx，"
                "如：n.e.k.o_plugin_mijia, n.e.k.o_plugin_game"
            )
        
        return True, None
    
    @staticmethod
    def extract_plugin_name(repo_name: str) -> Optional[str]:
        """
        从仓库名称中提取插件名称
        
        Args:
            repo_name: 仓库名称，如 "n.e.k.o_plugin_mijia"
            
        Returns:
            插件名称，如 "mijia"
        """
        if not repo_name.startswith('n.e.k.o_plugin_'):
            return None
        
        # 提取 xxx 部分
        prefix = 'n.e.k.o_plugin_'
        return repo_name[len(prefix):]
    
    @staticmethod
    def generate_repo_name(plugin_name: str) -> str:
        """
        根据插件名称生成仓库名称
        
        Args:
            plugin_name: 插件名称，如 "mijia"
            
        Returns:
            仓库名称，如 "n.e.k.o_plugin_mijia"
        """
        # 清理插件名称（只保留小写字母、数字和下划线）
        cleaned = re.sub(r'[^a-z0-9_]', '_', plugin_name.lower())
        return f"n.e.k.o_plugin_{cleaned}"
    
    @staticmethod
    def validate_github_url(repo_url: str) -> Tuple[bool, Optional[str]]:
        """
        验证 GitHub URL 是否符合插件仓库规范
        
        Args:
            repo_url: GitHub 仓库地址
            
        Returns:
            (是否有效, 错误信息)
        """
        if not repo_url:
            return False, "仓库地址不能为空"
        
        # 检查是否是 GitHub 地址
        if 'github.com' not in repo_url:
            return False, "必须是 GitHub 仓库地址"
        
        # 提取仓库名称
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            return False, "无效的仓库地址"
        
        repo_name = parts[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        return PluginValidator.validate_repo_name(repo_name)


def validate_plugin_repo(repo_url: str) -> Tuple[bool, Optional[str]]:
    """
    快捷函数：验证插件仓库
    
    Args:
        repo_url: GitHub 仓库地址
        
    Returns:
        (是否有效, 错误信息)
    """
    return PluginValidator.validate_github_url(repo_url)
