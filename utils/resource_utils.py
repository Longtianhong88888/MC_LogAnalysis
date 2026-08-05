import os
import sys


def resource_path(name):
    """返回资源文件的绝对路径，兼容 PyInstaller onefile 打包模式。"""
    base = getattr(sys, '_MEIPASS', None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def runtime_root():
    """返回用户可放置外部资源的根目录：打包后为 exe 所在目录，开发时为项目根目录。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_external_resource(name):
    """在外部资源根目录/当前目录查找文件（不随包内置，由用户自行放置），找不到返回 None。"""
    for base in (runtime_root(), os.getcwd()):
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    return None
