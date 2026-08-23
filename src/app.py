"""虚空终端 TUI 主应用"""
import asyncio
import json
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Input, Button, Static, ListView, ListItem, Label, Header, Footer
from textual.reactive import reactive
from textual.binding import Binding
from .api import ChatAPI
from .ws_client import WSClient


class LoginScreen(Container):
    """登录界面"""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("虚空终端 VoidTerminal", id="login-title"),
            Static("Linux TUI 版", id="login-subtitle"),
            Input(placeholder="用户名", id="login-username"),
            Input(placeholder="密码", id="login-password", password=True),
            Horizontal(
                Button("登录", id="login-btn", variant="primary"),
                Button("注册", id="register-btn"),
                id="login-buttons"
            ),
            Static("", id="login-error"),
            id="login-box"
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            await self.app.do_login()
        elif event.button.id == "register-btn":
            await self.app.do_register()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("login-username", "login-password"):
            await self.app.do_login()


class ChatMessage(Static):
    """聊天消息组件"""

    def __init__(self, msg: dict, is_me: bool = False, **kwargs):
        self.msg = msg
        self.is_me = is_me
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        msg = self.msg
        name = msg.get("fromName", "未知")
        content = msg.get("content", "")
        time_str = datetime.fromtimestamp(msg.get("time", 0) / 1000).strftime("%H:%M") if msg.get("time") else ""

        # 处理图片
        images = msg.get("images", [])
        img_text = ""
        if images:
            img_text = "\n" + "\n".join(f"[图片] {img}" for img in images)

        # 处理表情包
        sticker = msg.get("sticker")
        sticker_text = ""
        if sticker:
            sticker_text = f"\n[表情包] {sticker.get('name', '')} {sticker.get('url', '')}"

        if self.is_me:
            text = f"[right][bold]{name}[/bold] [{time_str}]\n{content}{img_text}{sticker_text}[/right]"
        else:
            text = f"[bold]{name}[/bold] [{time_str}]\n{content}{img_text}{sticker_text}"

        yield Static(text, classes="msg-bubble me" if self.is_me else "msg-bubble")


class ConversationItem(ListItem):
    """会话列表项"""

    def __init__(self, conv_type: str, conv_id: str, name: str, unread: int = 0, **kwargs):
        self.conv_type = conv_type
        self.conv_id = conv_id
        self.conv_name = name
        self.unread = unread
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        unread_text = f" ({self.unread})" if self.unread > 0 else ""
        type_icon = "🌐" if self.conv_type == "global" else ("👤" if self.conv_type == "dm" else "👥")
        yield Label(f"{type_icon} {self.conv_name}{unread_text}")


class ChatApp(App):
    """虚空终端 TUI 应用"""

    CSS = """
    Screen {
        background: #1a1a2e;
    }

    #login-box {
        width: 40;
        height: auto;
        margin: 1 2;
        padding: 1;
        background: #16213e;
        border: solid #0f3460;
    }

    #login-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
    }

    #login-subtitle {
        text-align: center;
        color: #888;
        height: 1;
        margin-bottom: 1;
    }

    #login-username, #login-password {
        margin: 1 0;
    }

    #login-buttons {
        height: 3;
        margin: 1 0;
    }

    #login-btn, #register-btn {
        width: 1fr;
    }

    #login-error {
        color: #e94560;
        height: 1;
    }

    /* 主聊天界面 */
    #main-container {
        height: 1fr;
    }

    #sidebar {
        width: 25;
        background: #16213e;
        border-right: solid #0f3460;
    }

    #chat-area {
        width: 1fr;
        background: #1a1a2e;
    }

    #chat-header {
        height: 2;
        padding: 0 1;
        background: #16213e;
        border-bottom: solid #0f3460;
    }

    #chat-title {
        color: #e94560;
        text-style: bold;
    }

    #messages-container {
        height: 1fr;
        padding: 1;
    }

    .msg-bubble {
        margin: 1 0;
        padding: 1 1;
        background: #16213e;
    }

    .msg-bubble.me {
        background: #0f3460;
    }

    #input-area {
        height: 3;
        padding: 0 1;
        background: #16213e;
        border-top: solid #0f3460;
    }

    #msg-input {
        width: 1fr;
    }

    #send-btn {
        width: 8;
    }

    #status-bar {
        height: 1;
        background: #0f3460;
        color: #aaa;
        padding: 0 1;
    }

    #conv-list {
        height: 1fr;
    }

    .conv-item {
        padding: 1 1;
    }

    .conv-item:hover {
        background: #0f3460;
    }

    .conv-item.active {
        background: #0f3460;
        color: #e94560;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出"),
        Binding("ctrl+s", "send_message", "发送"),
        Binding("tab", "switch_focus", "切换焦点"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api = ChatAPI()
        self.ws = WSClient()
        self.current_user = None
        self.active_conversation = {"type": "global", "id": None, "name": "公共大厅"}
        self.conversations = []
        self.messages = {"global": [], "dm": {}, "group": {}}
        self.friends = {}
        self.groups = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(id="main-container")
        yield Footer()

    def on_mount(self) -> None:
        """应用启动时显示登录界面"""
        self.show_login()

    def show_login(self) -> None:
        """显示登录界面"""
        container = self.query_one("#main-container", Container)
        container.remove_children()
        container.mount(LoginScreen())

    def show_chat(self) -> None:
        """显示聊天主界面"""
        container = self.query_one("#main-container", Container)
        container.remove_children()

        # 侧边栏（会话列表）
        sidebar = Vertical(
            Static("会话列表", id="sidebar-title"),
            ListView(id="conv-list"),
            id="sidebar"
        )

        # 聊天区域
        chat_area = Vertical(
            Horizontal(
                Static("公共大厅", id="chat-title"),
                id="chat-header"
            ),
            ScrollableContainer(id="messages-container"),
            Horizontal(
                Input(placeholder="输入消息...", id="msg-input"),
                Button("发送", id="send-btn", variant="primary"),
                id="input-area"
            ),
            Static("连接中...", id="status-bar"),
            id="chat-area"
        )

        main = Horizontal(sidebar, chat_area, id="chat-main")
        container.mount(main)

        # 加载默认会话
        self.load_conversations()
        self.switch_conversation("global", None, "公共大厅")

        # 连接 WebSocket
        asyncio.create_task(self.connect_ws())

    async def do_login(self) -> None:
        """执行登录"""
        try:
            username = self.query_one("#login-username", Input).value
            password = self.query_one("#login-password", Input).value
            if not username or not password:
                self.query_one("#login-error", Static).update("请输入用户名和密码")
                return

            result = self.api.login(username, password)
            if result.get("token"):
                self.current_user = result.get("user")
                self.show_chat()
            else:
                self.query_one("#login-error", Static).update(result.get("error", "登录失败"))
        except Exception as e:
            self.query_one("#login-error", Static).update(f"登录异常: {e}")

    async def do_register(self) -> None:
        """执行注册"""
        try:
            username = self.query_one("#login-username", Input).value
            password = self.query_one("#login-password", Input).value
            if not username or not password:
                self.query_one("#login-error", Static).update("请输入用户名和密码")
                return

            result = self.api.register(username, password)
            if result.get("ok") or result.get("token"):
                self.query_one("#login-error", Static).update("注册成功，请登录")
            else:
                self.query_one("#login-error", Static).update(result.get("error", "注册失败"))
        except Exception as e:
            self.query_one("#login-error", Static).update(f"注册异常: {e}")

    async def connect_ws(self) -> None:
        """连接 WebSocket"""
        self.ws.token = self.api.token
        self.ws.on_message = self.on_ws_message
        self.ws.on_open = self.on_ws_open
        self.ws.on_close = self.on_ws_close
        await self.ws.connect(self.api.token)

    async def on_ws_open(self) -> None:
        """WebSocket 连接成功，等待认证"""
        try:
            status = self.query_one("#status-bar", Static)
            status.update("[yellow]● 认证中...[/yellow]")
        except Exception as e:
            self.log(f"[on_ws_open] 异常: {e}")

    async def on_ws_close(self, reason: str = "") -> None:
        """WebSocket 断开"""
        try:
            status = self.query_one("#status-bar", Static)
            status.update(f"[red]● 断开连接: {reason}[/red]")
        except Exception as e:
            self.log(f"[on_ws_close] 异常: {e}")

    async def on_ws_message(self, data: dict) -> None:
        """处理 WebSocket 消息"""
        msg_type = data.get("type")

        if msg_type == "hello":
            # 初始数据
            self.current_user = data.get("self", self.current_user)
            self.friends = {f["id"]: f for f in data.get("friends", [])}
            self.groups = {g["id"]: g for g in data.get("groups", [])}
            self.messages["global"] = data.get("globalMsgs", [])

            # 私聊历史
            dm_rooms = data.get("dmRooms", {})
            if isinstance(dm_rooms, dict):
                for key, msgs in dm_rooms.items():
                    parts = key.split("_")
                    if len(parts) >= 2:
                        peer = parts[1] if parts[0] == self.current_user.get("id") else parts[0]
                        self.messages["dm"][peer] = msgs

            # 群聊历史
            group_msgs = data.get("groupMsgs", {})
            if isinstance(group_msgs, dict):
                for gid, msgs in group_msgs.items():
                    self.messages["group"][gid] = msgs

            self.load_conversations()
            self.refresh_messages()

            # 认证完成，更新状态栏
            try:
                status = self.query_one("#status-bar", Static)
                status.update("[green]● 已连接[/green]")
            except Exception as e:
                self.log(f"[hello] 更新状态栏异常: {e}")

        elif msg_type in ("global", "dm", "group"):
            # 新消息
            if msg_type == "global":
                self.messages["global"].append(data)
            elif msg_type == "dm":
                peer = data.get("from") if data.get("from") != self.current_user.get("id") else data.get("to")
                if peer not in self.messages["dm"]:
                    self.messages["dm"][peer] = []
                self.messages["dm"][peer].append(data)
            elif msg_type == "group":
                gid = data.get("gid")
                if gid not in self.messages["group"]:
                    self.messages["group"][gid] = []
                self.messages["group"][gid].append(data)

            # 如果在当前会话，刷新显示
            if (self.active_conversation["type"] == msg_type and
                (msg_type == "global" or
                 (msg_type == "dm" and self.active_conversation["id"] in (data.get("from"), data.get("to"))) or
                 (msg_type == "group" and self.active_conversation["id"] == data.get("gid")))):
                self.refresh_messages()

            self.load_conversations()

    def load_conversations(self) -> None:
        """加载会话列表"""
        try:
            list_view = self.query_one("#conv-list", ListView)
            list_view.clear()

            # 公共大厅
            list_view.append(ConversationItem("global", None, "公共大厅"))

            # 好友私聊
            for fid, friend in self.friends.items():
                unread = 0
                list_view.append(ConversationItem("dm", fid, friend.get("username", fid), unread))

            # 群聊
            for gid, group in self.groups.items():
                unread = 0
                list_view.append(ConversationItem("group", gid, group.get("name", gid), unread))
        except Exception as e:
            self.log(f"[load_conversations] 异常: {e}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """会话列表选中"""
        item = event.item
        if isinstance(item, ConversationItem):
            self.switch_conversation(item.conv_type, item.conv_id, item.conv_name)

    def switch_conversation(self, conv_type: str, conv_id: str, name: str) -> None:
        """切换会话"""
        self.active_conversation = {"type": conv_type, "id": conv_id, "name": name}
        try:
            self.query_one("#chat-title", Static).update(name)
        except:
            pass
        self.refresh_messages()

    def refresh_messages(self) -> None:
        """刷新消息显示"""
        try:
            container = self.query_one("#messages-container", ScrollableContainer)
            container.remove_children()

            conv = self.active_conversation
            msgs = []

            if conv["type"] == "global":
                msgs = self.messages.get("global", [])
            elif conv["type"] == "dm":
                msgs = self.messages.get("dm", {}).get(conv["id"], [])
            elif conv["type"] == "group":
                msgs = self.messages.get("group", {}).get(conv["id"], [])

            my_id = self.current_user.get("id") if self.current_user else None
            for msg in msgs[-100:]:  # 最多显示100条
                is_me = msg.get("from") == my_id
                container.mount(ChatMessage(msg, is_me=is_me))

            # 滚动到底部
            container.scroll_end(animate=False)
        except Exception as e:
            self.log(f"[refresh_messages] 异常: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击"""
        if event.button.id == "send-btn":
            await self.send_current_message()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入框回车"""
        if event.input.id == "msg-input":
            await self.send_current_message()

    async def send_current_message(self) -> None:
        """发送当前消息"""
        try:
            input_widget = self.query_one("#msg-input", Input)
            content = input_widget.value.strip()
            if not content:
                return

            conv = self.active_conversation
            kwargs = {}
            if conv["type"] == "dm":
                kwargs["to"] = conv["id"]
            elif conv["type"] == "group":
                kwargs["gid"] = conv["id"]

            success = await self.ws.send_message(conv["type"], content, **kwargs)
            if success:
                input_widget.value = ""
            else:
                self.notify("发送失败：WebSocket 未连接，请稍候重试", severity="error")
        except Exception as e:
            self.log(f"[send_current_message] 异常: {e}")
            self.notify(f"发送失败: {e}", severity="error")

    async def action_send_message(self) -> None:
        """快捷键发送"""
        await self.send_current_message()

    def action_switch_focus(self) -> None:
        """切换焦点"""
        try:
            input_widget = self.query_one("#msg-input", Input)
            input_widget.focus()
        except:
            pass


def main():
    app = ChatApp()
    app.run()


if __name__ == "__main__":
    main()
