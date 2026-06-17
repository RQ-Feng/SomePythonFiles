import json
import sys
from pathlib import Path
import winreg
import requests

X19SignHeaders = {"Content-Type": "text/plain; charset=utf-8"}

def normalize_text(value: str) -> str:
    value = value.replace("\\r\\n", "\n")
    value = value.replace('\\"', '"')
    return value


def main() -> None:
    X19SignMode = input("X19Sign处理\nA. 加密\nB. 解密\nC. temp.config解密\n请输入选项:")
    if X19SignMode == "A":
        url = "http://127.0.0.1:4600/EncryptX19sign"
    elif X19SignMode in ["B", "C"]:
        url = "http://127.0.0.1:4600/DecryptX19sign"
    else:
        print("无效的处理方法")
        return
    
    if X19SignMode == "C":
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Netease\MCLauncher",
            ) as key:
                MCPath, _ = winreg.QueryValueEx(key, "DownloadPath")
        except Exception as _:
            MCPath = input(f"未检测到网易MC路径,请手动输入路径(例如 D:\\MCLDownload):")
        print(f"已获取网易MC路径: {MCPath}")
        try:
            temp_config_path = Path(MCPath) / "temp" / "temp.config"
        except Exception as e:
            print(f"无法寻找到网易基岩版配置文件。错误信息: {e}")
            return
        
    try:
        InputString = temp_config_path.read_text(encoding="utf-8") if X19SignMode == "C" else input('需要处理的字符串:')
    except FileNotFoundError:
        print(f"错误：在当前文件夹下没有找到 {temp_config_path.name} 文件")
        return
    
    try:
        response = requests.post(url, headers=X19SignHeaders, data=InputString.encode("utf-8"), timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        print("请求失败：", exc)
        return
    except json.JSONDecodeError as exc:
        print("无法解析返回的 JSON:", exc)
        print("响应内容：", response.text)
        return

    original = data["ToDecryptX19sign"] if X19SignMode in ["B", "C"] else data["ToEncryptX19sign"]
    result = normalize_text(original) if X19SignMode in ["B", "C"] else original

    print("处理后的字符串为:", result)

if __name__ == "__main__":
    main()