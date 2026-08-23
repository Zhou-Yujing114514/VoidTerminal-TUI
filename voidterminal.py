#!/usr/bin/env python3
"""虚空终端 TUI 版 - 启动入口"""
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import main

if __name__ == "__main__":
    main()
