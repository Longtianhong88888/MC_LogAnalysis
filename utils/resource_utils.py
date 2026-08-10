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
    """按顺序查找资源：外部根目录/当前目录 → PyInstaller 打包内置目录(_MEIPASS)。

    打包内置为默认回退；用户放在 exe 同目录（或项目根目录）的同名文件优先。
    找不到返回 None。
    """
    bases = [runtime_root(), os.getcwd()]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bases.append(meipass)
    for base in bases:
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    return None
