"""WebSocket 客户端"""
import asyncio
import json
import websockets
from typing import Callable, Optional

# 安全：WS 通道携带鉴权 token，必须走 WSS（v2.1.0 起由 ws 改为 wss）
DEFAULT_WS = "wss://buer.kdns.fr/ws"

class WSClient:
    def __init__(self, ws_url: str = DEFAULT_WS):
        self.ws_url = ws_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.token: Optional[str] = None
        self.on_message: Optional[Callable] = None
        self.on_open: Optional[Callable] = None
        self.on_close: Optional[Callable] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self, token: str):
        """连接 WebSocket 并认证"""
        self.token = token
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def _run(self):
        """后台运行消息循环"""
        reconnect_delay = 1
        while self._running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=30) as ws:
                    self.ws = ws
                    reconnect_delay = 1
                    # 发送认证
                    await ws.send(json.dumps({"type": "auth", "token": self.token}))
                    if self.on_open:
                        await self._safe_call(self.on_open)
                    # 消息循环
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                            if self.on_message:
                                await self._safe_call(self.on_message, data)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                self.ws = None
                if self.on_close:
                    await self._safe_call(self.on_close, str(e))
                if self._running:
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 10)

    async def _safe_call(self, callback, *args):
        """安全调用回调，捕获异常"""
        try:
            result = callback(*args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            print(f"[WS] 回调异常: {e}")

    async def send(self, data: dict):
        """发送消息"""
        if self.ws and self.ws.state == websockets.State.OPEN:
            await self.ws.send(json.dumps(data))
            return True
        return False

    async def send_message(self, msg_type: str, content: str, **kwargs):
        """发送聊天消息"""
        payload = {"type": msg_type, "content": content}
        payload.update(kwargs)
        return await self.send(payload)

    async def close(self):
        """关闭连接"""
        self._running = False
        if self.ws:
            await self.ws.close()
        if self._task:
            self._task.cancel()
