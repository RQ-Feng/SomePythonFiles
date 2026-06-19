import requests
import json
import pyperclip
import subprocess
import time
import winreg
import sys
import string,random
from pathlib import Path
from datetime import datetime

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_new_registered_account(Sauth):
    # 返回一个完整结构的字典
    return {
        "Name": "Alt " + "".join(random.choice(string.ascii_letters) for _ in range(5)),
        "Type": 0,
        "CookieData": Sauth,
        "Username": None,
        "Password": None,
        "PhoneNumber": None,
        "DeviceId": None,
        "LastUsed": datetime.now().isoformat(),
        "CreatedAt": datetime.now().isoformat(),
        "Notes": ""
    }

print("与WPFLauncher_Hook的账号管理器搭配使用的4399账号自动注册器")
time.sleep(1)  # 模拟一些等待时间
try:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Netease\MCLauncher",
    ) as key:
        MCPath, _ = winreg.QueryValueEx(key, "InstallLocation")
except Exception as _:
    MCPath = input(f"未检测到网易MC启动器安装路径,请手动输入路径(例如 D:\\MCLauncher):")

try:
    accounts_json_path = Path(MCPath) / "accounts.json"
except Exception as e:
    print(f"无法寻找到账号管理器配置文件。错误信息: {e}")
    sys.exit()
print(f"已获取网易MC启动器安装路径: {MCPath}")

with open(accounts_json_path, "r", encoding="utf-8") as f:
    accounts_json = json.load(f)

nekoinsi_api_file = Path(__file__).resolve().parent.parent.parent.parent / "Secure" / "nekoinsi_api.txt"
nekoinsi_api = nekoinsi_api_file.read_text(encoding="utf-8")
params = {"userApiKey": nekoinsi_api}

print("正在获取4399账号并转换为Sauth格式...")
response = requests.get("https://4399.nekoinsi.de/api/alt", params=params,verify = False,timeout=10)
try:
    response.raise_for_status()
    data = response.json()
    if data.get("code") == 0:
        UserInfo = data["data"][0]
    else:
        print(f"API抛出错误: {data.get('message', 'Unknown error')}")
except requests.exceptions.RequestException as e:
    print(f"请求失败,请检查API: {e}")
username, password = UserInfo.split("----")
print("成功获取4399账号。用户名:", username, "密码:", password + "\n正在转换为Sauth格式...")

# 传入外部脚本路径，以及账号、密码参数
Sauth = subprocess.run(
    ["python", Path(__file__).resolve().parent / "4399账号转Sauth.py", username, password],
    capture_output=True,  # 捕获输出
    text=True,            # 将输出结果转换为字符串
    encoding="gbk"      # 指定编码防乱码
)

# 获取另一个 py 文件的标准输出结果
if Sauth.returncode == 0:
    Sauth_json = Sauth.stdout.strip()
    print(f"成功获取到结果:\n{Sauth_json}")
    pyperclip.copy(Sauth_json)
    account_info = get_new_registered_account(Sauth_json)
    accounts_json.append(account_info)

    try:
        with open(accounts_json_path, "w", encoding="utf-8") as f:
            json.dump(accounts_json, f, indent=2, ensure_ascii=False)
        print("已添加新4399账户:", account_info["Name"])
    except Exception as e:
        print(f"添加失败: {e}")
else:
    print(f"执行失败，错误信息: {Sauth.stderr}")