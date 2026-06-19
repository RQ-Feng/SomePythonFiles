import json
import os
import subprocess
import sys
import winreg
from pathlib import Path
from colorama import init, Fore, Back, Style

init(autoreset=True)


def MCPath():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Netease\MCLauncher",
        ) as key:
            mc_path, _ = winreg.QueryValueEx(key, "DownloadPath")
    except Exception:
        mc_path = input(f"未检测到网易MC路径,请手动输入路径(例如 D:\\MCLDownload):")
    return mc_path


def MCLauncherPath():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Netease\MCLauncher",
        ) as key:
            launcher_path, _ = winreg.QueryValueEx(key, "InstallLocation")
    except Exception:
        launcher_path = input(f"未检测到网易MC启动器安装路径,请手动输入路径(例如 D:\\MCLauncher):")
    return launcher_path


def settings_path(root=None, filename="Settings.json"):
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parent
    path = root_path / filename
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
    return path


def load_settings(root=None, filename="Settings.json"):
    path = settings_path(root, filename)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data, root=None, filename="Settings.json"):
    path = settings_path(root, filename)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def clear_screen():
    os.system('cls')


def list_modules_root(current_file):
    return Path(current_file).resolve().parent / 'Modules'


def sorted_dirs(path):
    return [p for p in sorted(path.iterdir(), key=lambda p: p.name.lower()) if p.is_dir()]


def sorted_py_files(path):
    return [p for p in sorted(path.iterdir(), key=lambda p: p.name.lower()) if p.is_file() and p.suffix == '.py']


def choose_from_list(prompt, items, allow_back=True, allow_exit=False, header=None):
    while True:
        if header:
            try:
                hdr = header() if callable(header) else header
            except Exception:
                hdr = str(header)
            print(hdr)
        for i, name in enumerate(items, start=1):
            print(f"{i}. {name}")
        extras = []
        if allow_back:
            extras.append("b. 返回上级")
        if allow_exit:
            extras.append("exit. 退出")
        if extras:
            print(' / '.join(extras))

        choice = input(prompt).strip()
        if allow_exit and choice.lower() == 'exit':
            return 'exit'
        if allow_back and (choice.lower() == 'b' or choice.lower() == 'back'):
            return 'back'
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
        clear_screen()


def run_py_file(path):
    print(Fore.CYAN + f"正在运行: {path}\n----- 输出开始 -----")
    try:
        subprocess.run([sys.executable, str(path)], check=False)
    except Exception as e:
        print(Fore.RED + f"运行文件时出错: {e}")
    print(Fore.CYAN + "----- 输出结束 -----")
