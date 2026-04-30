import httpx
import base64
import json
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse

from app.core.config import settings


class GitHubService:
    """GitHub API 服务"""
    
    BASE_URL = "https://api.github.com"
    RAW_URL = "https://raw.githubusercontent.com"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or getattr(settings, 'GITHUB_TOKEN', None)
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "N.E.KO-Plugin-Market"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def _parse_repo_url(self, repo_url: str) -> tuple:
        """解析 GitHub 仓库 URL"""
        # 处理多种格式的 URL
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # github.com/owner/repo
        # https://github.com/wangjunyu200708/n.e.k.o_plugin_mijia
        
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/')
        
        if path.endswith('.git'):
            path = path[:-4]
        
        parts = path.split('/')
        if len(parts) >= 2:
            owner = parts[0]
            # 仓库名可能包含点号，如 n.e.k.o_plugin_mijia
            repo = parts[1]
            return owner, repo
        raise ValueError(f"无效的 GitHub 仓库 URL: {repo_url}")
    
    async def get_repo_info(self, repo_url: str) -> Dict[str, Any]:
        """获取仓库基本信息"""
        owner, repo = self._parse_repo_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo_contents(
        self, 
        repo_url: str, 
        path: str = "",
        ref: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取仓库目录内容"""
        owner, repo = self._parse_repo_url(repo_url)
        
        params = {}
        if ref:
            params["ref"] = ref
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_file_content(
        self, 
        repo_url: str, 
        path: str,
        ref: Optional[str] = None
    ) -> str:
        """获取文件内容"""
        owner, repo = self._parse_repo_url(repo_url)
        
        params = {}
        if ref:
            params["ref"] = ref
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # 解码 base64 内容
            if "content" in data:
                content = base64.b64decode(data["content"]).decode('utf-8')
                return content
            return ""
    
    async def get_raw_file(
        self,
        repo_url: str,
        path: str,
        ref: str = "main"
    ) -> str:
        """通过 raw.githubusercontent.com 获取文件"""
        owner, repo = self._parse_repo_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.RAW_URL}/{owner}/{repo}/{ref}/{path}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.text
    
    async def get_readme(self, repo_url: str, ref: Optional[str] = None) -> str:
        """获取 README 内容"""
        owner, repo = self._parse_repo_url(repo_url)
        
        params = {}
        if ref:
            params["ref"] = ref
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/readme",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 404:
                return ""
            
            response.raise_for_status()
            data = response.json()
            
            if "content" in data:
                return base64.b64decode(data["content"]).decode('utf-8')
            return ""
    
    async def get_latest_release(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """获取最新发布版本"""
        owner, repo = self._parse_repo_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/releases/latest",
                headers=self.headers
            )
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
    
    async def list_releases(self, repo_url: str, per_page: int = 10) -> List[Dict[str, Any]]:
        """获取发布版本列表"""
        owner, repo = self._parse_repo_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/releases",
                headers=self.headers,
                params={"per_page": per_page}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo_tree(
        self, 
        repo_url: str, 
        recursive: bool = True,
        ref: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取仓库文件树"""
        owner, repo = self._parse_repo_url(repo_url)
        
        # 首先获取默认分支
        if not ref:
            repo_info = await self.get_repo_info(repo_url)
            ref = repo_info.get("default_branch", "main")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/{ref}",
                headers=self.headers,
                params={"recursive": "1" if recursive else "0"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("tree", [])
    
    async def get_plugin_manifest(
        self, 
        repo_url: str, 
        ref: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取插件清单文件 (manifest.json 或 package.json)"""
        manifest_files = ["manifest.json", "package.json", "plugin.json", "nekko.json"]
        
        for filename in manifest_files:
            try:
                content = await self.get_file_content(repo_url, filename, ref)
                if content:
                    return json.loads(content)
            except (httpx.HTTPError, json.JSONDecodeError):
                continue
        
        return None
    
    async def download_archive(
        self, 
        repo_url: str, 
        ref: str = "main",
        format: str = "zip"
    ) -> bytes:
        """下载仓库归档"""
        owner, repo = self._parse_repo_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/{format}ball/{ref}",
                headers=self.headers,
                follow_redirects=True
            )
            response.raise_for_status()
            return response.content
    
    async def validate_repo_access(self, repo_url: str) -> bool:
        """验证仓库是否可访问"""
        try:
            await self.get_repo_info(repo_url)
            return True
        except httpx.HTTPError:
            return False
    
    async def get_repo_languages(self, repo_url: str) -> Dict[str, int]:
        """获取仓库使用的编程语言"""
        owner, repo = self._parse_repo_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/languages",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
