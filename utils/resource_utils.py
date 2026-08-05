import os
import sys


def resource_path(name):
    """返回资源文件的绝对路径，兼容 PyInstaller onefile 打包模式。"""
    base = getattr(sys, '_MEIPASS', None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)
