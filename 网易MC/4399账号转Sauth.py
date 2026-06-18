import json,time,os
import sys
import urllib3
import string,random
from colorama import init, Fore, Back, Style
from urllib.parse import parse_qs, urlparse
import requests

init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def generate_pe_captcha_id() -> str:
    """生成手游端标准的 32 位大写不带编组的 Hex 验证码 ID (对应 Guid.NewGuid().ToString().Replace("-","").ToUpper())"""
    chars = "0123456789ABCDEF"
    return "".join(random.choice(chars) for _ in range(32))

def generate_pe_udid() -> str:
    """生成手游端 16 位随机字母数字组成的 UDID"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(16))

def extract_error_tip(html_text: str) -> str:
    """提取登录页面中的网页错误提示"""
    start_marker = 'id="login_err_msg"'
    if start_marker in html_text:
        try:
            start_idx = html_text.index(start_marker)
            content_start = html_text.index(">", start_idx) + 1
            content_end = html_text.index("</", content_start)
            return html_text[content_start:content_end].strip()
        except ValueError:
            pass

    # 备用匹配兼容方案
    if 'login_err_msg">' in html_text:
        try:
            start_idx = html_text.index('login_err_msg">') + len(
                'login_err_msg">'
            )
            end_idx = html_text.index("</p>", start_idx)
            return html_text[start_idx:end_idx].strip()
        except ValueError:
            pass
    return ""

def get_sauth_token(username, password) -> str:
    session = requests.Session()
    session.verify = False  # 绕过本地证书校验

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
    )

    # ── Step 1: 获取并识别验证码 ──
    print("[4399PE] Step 1: 获取并识别验证码...", file=sys.stderr)
    captcha_id = generate_pe_captcha_id()
    captcha_url = (
        f"https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={captcha_id}"
    )
    captcha_res = session.get(captcha_url)

    captcha_text = ""
    api_url = "http://110.42.70.32:13423/api/fantnel/captcha"
    try:
        api_res = session.post(api_url, data=captcha_res.content, timeout=8)
        api_data = api_res.json()
        if api_data.get("code") == 1:
            captcha_text = str(api_data.get("data", "")).strip().lower()
            print(
                f"[4399PE] 验证码自动识别结果: {captcha_text}", file=sys.stderr
            )
        else:
            raise Exception(f"接口响应 code 错误: {api_data.get('msg')}")
    except Exception as e:
        print(
            f"⚠️ [4399PE] 远程识别失败 ({e})，切换到手动模式...",
            file=sys.stderr,
        )
        print(f"请打开验证码 URL 查看图片: {captcha_url}", file=sys.stderr)
        captcha_text = input("请输入看到的 4 位验证码: ").strip().lower()

    # ── Step 2: 获取 OAuth 参数 ──
    print("[4399PE] Step 2: 获取 OAuth 参数...", file=sys.stderr)
    callback_config_url = "https://m.4399api.com/openapi/oauth-callback.html?gamekey=44770&game_key=115716"
    oauth_res = session.get(callback_config_url)
    oauth_data = oauth_res.json()

    oauth_url = oauth_data.get("result", "")
    if not oauth_url:
        raise Exception(f"获取 oauth URL 失败: {oauth_res.text}")

    # 解析 URL Query 参数
    from urllib.parse import parse_qs, urlparse

    parsed_query = parse_qs(urlparse(oauth_url).query)
    client_id = parsed_query.get("client_id", [""])[0]
    state = parsed_query.get("state", [""])[0]
    ref_val = parsed_query.get("ref", [""])[0]

    # ── Step 3: POST loginAndAuthorize (禁止自动重定向) ──
    print("[4399PE] Step 3: 提交登录表单...", file=sys.stderr)
    payload = {
        "auth_action": "ORILOGIN",
        "bizId": "2100001792",
        "captcha": captcha_text,
        "captcha_id": captcha_id,
        "client_id": client_id,
        "isInputRealname": "false",
        "isVaildRealname": "false",
        "password": password,
        "redirect_uri": "https://m.4399api.com/openapi/oauth-callback.html?gamekey=44770&game_key=115716",
        "ref": ref_val,
        "response_type": "TOKEN",
        "scope": "basic",
        "sec": "0",
        "state": state,
        "username": username,
    }

    login_url = "https://ptlogin.4399.com/oauth2/loginAndAuthorize.do?channel=&sdk=op&sdk_version=3.12.2.503"
    # allow_redirects=False 对应 C# 中的 AllowAutoRedirect = false
    login_res = session.post(login_url, data=payload, allow_redirects=False)

    # ── Step 4: 处理 302 重定向并请求回调 ──
    if login_res.status_code in (301, 302):
        location = login_res.headers.get("Location")
        if not location:
            raise Exception("登录成功但未在响应头中获取到 Location 地址")

        print(
            f"[4399PE] Step 4: 捕获到 302 重定向，请求回调地址...",
            file=sys.stderr,
        )
        callback_res = session.get(location)
        callback_json = callback_res.json()

        result_obj = callback_json.get("result", {})
        uid = result_obj.get("uid")
        user_state = result_obj.get("state")

        if not uid or not user_state:
            raise Exception(f"OAuth 回调数据解析缺少 uid/state: {callback_json}")
    else:
        # 未触发重定向说明登录失败，解析 HTML 错误体
        response_body = login_res.text
        if "验证码错误" in response_body:
            raise Exception("4399 登录返回错误: 验证码错误")
        error_tip = extract_error_tip(response_body)
        if error_tip:
            raise Exception(f"4399 登录返回错误: {error_tip}")
        raise Exception("未知登录错误或密码错误")

    # ── Step 5: 构建手游端标准的 SAuth 结构体 ──
    print(
        f"[4399PE] Step 5: 成功获取 uid={uid}, 开始构建 SAuth 凭证...",
        file=sys.stderr,
    )

    sauth_data = {
        "aim_info": json.dumps(
            {"aim": "127.0.0.1", "country": "CN", "tz": "+0800", "tzid": ""},
            separators=(",", ":"),
        ),
        "realname": json.dumps(
            {"realname_type": 2}, separators=(",", ":")
        ),  # 对应 C# 中的整数 2
        "app_channel": "4399com",
        "platform": "ad",  # 对应手游 Android 标识
        "client_login_sn": "4399FuckYou",  # 对齐 C# 硬编码
        "gameid": "x19",
        "login_channel": "4399com",
        "sdk_version": "3.12.2",  # 手游 SDK 版本
        "sdkuid": str(uid),
        "sessionid": str(user_state),
        "udid": generate_pe_udid(),
        "deviceid": "4399FuckYou",  # 对齐 C# 硬编码
    }

    # 严格按照 C# 代码中的无空格紧凑 JSON 序列化形式
    sauth_json_str = json.dumps(sauth_data, separators=(",", ":"))

    # ── Step 6: 请求网易手游验证端进行 uni_sauth 激活 ──
    print(
        "[4399PE] Step 6: 正在向网易手游端发送 uni_sauth 激活请求...",
        file=sys.stderr,
    )
    sauth_url = "https://mgbsdk.matrix.netease.com/x19/sdk/uni_sauth"
    sauth_headers = {"Content-Type": "application/json"}

    uni_res = session.post(
        sauth_url, data=sauth_json_str, headers=sauth_headers, timeout=10
    )
    print(f"[4399PE] uni_sauth 校验端返回成功", file=sys.stderr)

    # 封装为外部调用期望的最终输出格式
    final_output = json.dumps(
        {"sauth_json": sauth_json_str}, separators=(",", ":")
    )
    return final_output

# ==================== 调用测试入口 ====================
if __name__ == "__main__":
    os.system('cls')
    print(Fore.GREEN + "网易4399Com转Sauth")
    print(Fore.CYAN + "验证码识别api来自Fantnel\nFantnel官网:https://npyyds.top/")
    time.sleep(1)
    UserInfo = sys.argv
    if UserInfo and len(UserInfo) >= 3:
        UserName = UserInfo[1]
        Password = UserInfo[2]
    else:
        UserName = input("请输入4399账号: ")
        Password = input("请输入4399密码: ")

    try:
        sauth_result = get_sauth_token(UserName, Password)
        print("转换后的Sauth为以下Json:", file=sys.stderr)
        print(sauth_result)
    except Exception as e:
        print(f"\n转换Sauth失败: {e}", file=sys.stderr)
        sys.exit(1)