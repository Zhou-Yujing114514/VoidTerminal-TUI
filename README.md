# 虚空终端 TUI 版 (VoidTerminal-TUI)

虚空终端聊天网站的 Linux 命令行 TUI 客户端，基于 Python + textual 框架开发。

## 功能

- 🔐 登录 / 注册
- 🌐 公共大厅聊天
- 👤 好友私聊
- 👥 群聊
- 📜 历史消息加载
- 🔄 WebSocket 自动重连
- ⌨️ 快捷键支持

## 安装

```bash
# 克隆仓库
git clone https://github.com/Zhou-Yujing114514/VoidTerminal-TUI.git
cd VoidTerminal-TUI

# 安装依赖
pip install -r requirements.txt
```

## 使用

```bash
python voidterminal.py
```

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+C` | 退出 |
| `Ctrl+S` | 发送消息 |
| `Enter` | 发送消息（输入框聚焦时） |
| `Tab` | 聚焦到输入框 |

### 操作说明

1. 启动后输入用户名和密码，点击「登录」（或按 Enter）
2. 左侧是会话列表，使用方向键选择，Enter 进入会话
3. 右侧是聊天区域，底部输入框输入消息
4. 按 Enter 或 Ctrl+S 发送消息
5. 点击「注册」可以注册新账号

## 配置

默认连接服务器：`http://buer.kdns.fr`

如需修改服务器地址，编辑 `src/api.py` 和 `src/ws_client.py` 中的 `DEFAULT_SERVER` 和 `DEFAULT_WS`。

## 技术栈

- Python 3.8+
- [textual](https://github.com/Textualize/textual) - 现代 TUI 框架
- [websockets](https://github.com/python-websockets/websockets) - WebSocket 客户端
- [requests](https://github.com/psf/requests) - HTTP 请求

## 项目结构

```
VoidTerminal-TUI/
├── voidterminal.py      # 启动入口
├── requirements.txt     # 依赖
├── README.md           # 说明文档
└── src/
    ├── __init__.py
    ├── app.py          # TUI 主应用
    ├── api.py          # HTTP API 封装
    └── ws_client.py    # WebSocket 客户端
```

## 相关项目

- [VoidTerminal-iOS](https://github.com/Zhou-Yujing114514/VoidTerminal-iOS) - iOS 原生客户端
- [VoidTerminal-Android](https://github.com/Zhou-Yujing114514/VoidTerminal-Android) - 安卓客户端
- 网页版：http://buer.kdns.fr

## License

MIT
