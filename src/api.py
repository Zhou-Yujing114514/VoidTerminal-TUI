"""HTTP API 封装"""
import requests
import json

# 安全：登录/注册接口携带账号密码，必须走 HTTPS（v2.1.0 起由 http 改为 https）
DEFAULT_SERVER = "https://buer.kdns.fr"

class ChatAPI:
    def __init__(self, server: str = DEFAULT_SERVER):
        self.server = server.rstrip("/")
        self.token = None
        self.user = None

    def _url(self, path: str) -> str:
        return f"{self.server}{path}"

    def login(self, username: str, password: str) -> dict:
        """登录，返回 {ok, token, user}"""
        r = requests.post(self._url("/api/login"), json={
            "username": username,
            "password": password
        }, timeout=10)
        data = r.json()
        if data.get("token"):
            self.token = data["token"]
            self.user = data.get("user")
        return data

    def register(self, username: str, password: str) -> dict:
        """注册"""
        r = requests.post(self._url("/api/register"), json={
            "username": username,
            "password": password
        }, timeout=10)
        return r.json()

    def get_stickers(self) -> list:
        """获取表情包列表"""
        try:
            r = requests.get(self._url("/api/stickers"), timeout=5)
            return r.json().get("stickers", [])
        except Exception:
            return []
