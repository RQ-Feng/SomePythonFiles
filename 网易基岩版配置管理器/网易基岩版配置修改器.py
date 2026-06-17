import os,json,copy,time
import winreg
from colorama import init, Fore, Back, Style
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import requests

EncryptX19sign = "http://127.0.0.1:4600/EncryptX19sign"
DecryptX19sign = "http://127.0.0.1:4600/DecryptX19sign"
X19SignHeaders = {"Content-Type": "text/plain; charset=utf-8"}

def normalize_text(value: str) -> str:
    value = value.replace("\\r\\n", "\n")
    value = value.replace('\\"', '"')
    return value

def WaitingForTempConfig(file_path: str):
    path = Path(file_path).resolve()
    
    # 1. 创建一个只监控特定文件名的处理器
    event_handler = PatternMatchingEventHandler(
        patterns=[path.name], 
        ignore_directories=True
    )
    
    # 2. 定义触发事件：当文件被修改时，改变标志位
    refreshed = False
    def on_modified(event):
        nonlocal refreshed
        refreshed = True

    event_handler.on_modified = on_modified

    # 3. 启动监控（监控目标文件所在的父目录）
    observer = Observer()
    observer.schedule(event_handler, path=str(path.parent), recursive=False)
    observer.start()
    
    print(f"正在等待 {path.name} 刷新，请加入任意基岩版房间以触发刷新...")
    
    # 4. 简单循环：一旦检测到刷新，立刻退出
    try:
        while not refreshed:
            time.sleep(0.1)  # 极短的延迟，保证响应速度且不占 CPU
    finally:
        observer.stop()
        observer.join()

init(autoreset=True)

def main() -> None:
    os.system('cls')
    print(Fore.GREEN + "网易基岩版配置修改器 v0.0.1")
    print(Fore.CYAN + "需要WPFLauncher_Hook安装且启动Web服务器,否则无法修改配置文件")
    time.sleep(1)
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
    
    WaitingForTempConfig(temp_config_path)
    print(f"检测到 {temp_config_path.name} 文件已刷新，尝试读取配置文件内容...")
    try:
        X19SignString = temp_config_path.read_text(encoding="utf-8")
        print("成功读取配置文件内容！")
        response = requests.post(DecryptX19sign, headers=X19SignHeaders, data=X19SignString.encode("utf-8"), timeout=5)
        response.raise_for_status()
        data = response.json()
        DecryptedX19sign = normalize_text(data["ToDecryptX19sign"])
    except FileNotFoundError:
        print(f"错误：在当前文件夹下没有找到 {temp_config_path.name} 文件")
        return
    except requests.exceptions.RequestException as exc:
        print("请求失败：", exc)
        return
    except json.JSONDecodeError as exc:
        print("无法解析返回的 JSON:", exc)
        print("响应内容：", response.text)
        return
    print("配置文件解密成功!")
    JsonX19Sign = json.loads(DecryptedX19sign)

    while True:
        Edit = input("你想如何修改配置文件?\nA. 按配置模板修改\nB. 手动修改\n请输入选项:")
        Edit = Edit.strip().upper()
        if Edit in ["A", "B"]:
            break  # 输入正确，跳出循环
    if Edit == "A":
        ConfigModule = input("请输入配置模板名称:")
        Module = Path(__file__).resolve().parent / "ConfigModules" / f"{ConfigModule}.json"
        try:
            with open(Module, "r", encoding="utf-8") as f:
                JsonModule = json.load(f)
        except FileNotFoundError:
            print(f"错误：在当前文件夹下没有找到 {Module.name} 文件")
            return
        except json.JSONDecodeError as exc:
            print("无法解析返回的 JSON:", exc)
            return
        urs = JsonX19Sign["player_info"]["urs"]
        JsonModule['path'] = JsonX19Sign['path'].split(urs)[0] + urs + "\\NetGame\\" + JsonModule['path'].split("\\NetGame\\")[1]
        JsonModule["player_info"] = JsonX19Sign["player_info"]
        JsonModule["skin_info"] = JsonX19Sign["skin_info"]
        JsonModule["misc"] = JsonX19Sign["misc"]
        JsonModule["room_info"]["token"] = JsonX19Sign["room_info"]["token"]
        JsonModule["room_info"]["host_id"] = JsonX19Sign["player_info"]["user_id"]
        JsonX19Sign = copy.deepcopy(JsonModule)
        print(f"已成功应用配置模板 {ConfigModule} !")
    else:
        #配置文件手动修改
        JsonX19Sign["room_info"]["ip"] = input("请输入新的IP地址(留空为默认):") or JsonX19Sign["room_info"]["ip"]
        JsonX19Sign["room_info"]["port"] = input("请输入新的端口号(留空为默认):") or JsonX19Sign["room_info"]["port"]
        JsonX19Sign["player_info"]["user_name"] = input("请输入你想修改的用户昵称(留空为默认):") or JsonX19Sign["player_info"]["user_name"]
        JsonX19Sign['path'] = JsonModule['path'].split(urs)[0] + urs + "\\NetGame\\" + JsonX19Sign['path'].split("\\NetGame\\")[1]
        print(f"已成功应用配置模板 {ConfigModule} !")

    #不明奶龙文字昵称(出于未知原因保留)
    #JsonX19Sign["player_info"]["user_name"] = "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n@@@@@@@@@@@
    JsonToStringX19Sign = json.dumps(JsonX19Sign, ensure_ascii=False, indent=4)
    print("当前房间地址为: {}:{}".format(JsonX19Sign["room_info"]["ip"], JsonX19Sign["room_info"]["port"]))
    print("当前用户昵称为: {}".format(JsonX19Sign["player_info"]["user_name"]))
    print("成功修改配置文件，尝试写回文件...")
    try:
        response = requests.post(EncryptX19sign, headers=X19SignHeaders, data=JsonToStringX19Sign.encode("utf-8"), timeout=5)
        response.raise_for_status()
        data = response.json()
        EncryptedX19sign = data["ToEncryptX19sign"]
        temp_config_path.write_text(EncryptedX19sign, encoding="utf-8")
    except Exception as e:
        print(f"写回文件失败，错误信息: {e}")
    print("处理完成!")
    time.sleep(2)

if __name__ == "__main__":
    main()
    os.system('cls')