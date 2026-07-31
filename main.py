import sys
from app import App

if __name__ == "__main__":
    app = App()
    app.run()


if getattr(sys, 'frozen', False):
    # 打包模式，无需终端
    pass