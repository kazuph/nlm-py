
import os
import subprocess
import sys
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.build_py import build_py


def build_go_binaries():
    """Goバイナリをビルドする関数"""
    print("Building Go binaries for nlm-auth...")
    
    # Goソースのディレクトリへのパス
    go_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'go')
    
    # カレントディレクトリを保存
    current_dir = os.getcwd()
    
    try:
        # Goディレクトリに移動
        os.chdir(go_dir)
        
        # go mod tidyを実行
        subprocess.check_call(['go', 'mod', 'tidy'])
        
        # ビルドスクリプトを実行
        build_script = os.path.join(go_dir, 'build.sh')
        if sys.platform == 'win32':
            # Windowsの場合は別途対応が必要
            # WSLやGit Bashを使っている場合は'bash'を呼び出す
            try:
                subprocess.check_call(['bash', build_script])
            except FileNotFoundError:
                print("Warning: bash not found, cannot build Go binaries on Windows")
                print("Please run go/build.sh manually or use WSL/Git Bash")
        else:
            # Unix系OSの場合は直接実行
            subprocess.check_call([build_script])
            
    except subprocess.CalledProcessError as e:
        print(f"Error building Go binaries: {e}")
        print("Please build manually by running: cd go && ./build.sh")
    
    finally:
        # 元のディレクトリに戻る
        os.chdir(current_dir)


class BuildPyCommand(build_py):
    """build_pyコマンドをオーバーライドしてGoバイナリをビルド"""
    def run(self):
        build_go_binaries()
        build_py.run(self)


class InstallCommand(install):
    """installコマンドをオーバーライドしてGoバイナリをビルド"""
    def run(self):
        build_go_binaries()
        install.run(self)


class DevelopCommand(develop):
    """developコマンドをオーバーライドしてGoバイナリをビルド"""
    def run(self):
        build_go_binaries()
        develop.run(self)


setup(
    cmdclass={
        'build_py': BuildPyCommand,
        'install': InstallCommand,
        'develop': DevelopCommand,
    },
)
