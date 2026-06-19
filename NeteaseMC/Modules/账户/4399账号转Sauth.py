import json,time,os
import sys
import string,random
from colorama import init, Fore, Back, Style
from urllib.parse import parse_qs, urlparse
import requests

init(autoreset=True)
import urllib3
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

def get_captcha(session):
    max_attempts = 5
    api_url = "http://110.42.70.32:13423/api/fantnel/captcha"
    captcha_id = None
    captcha_url = None

    for attempt in range(1, max_attempts + 1):
        captcha_id = generate_pe_captcha_id()
        captcha_url = f"https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={captcha_id}"

        print(f"[4399PE] Step 1: 获取并识别验证码 (第 {attempt}/{max_attempts} 次)...", file=sys.stderr)
        try:
            captcha_res = session.get(captcha_url, timeout=8)
            api_res = session.post(api_url, data=captcha_res.content, timeout=8)
            api_data = api_res.json()
            if api_data.get("code") == 1:
                captcha_text = str(api_data.get("data", "")).strip().lower()
                print(f"[4399PE] 验证码自动识别成功: {captcha_text}", file=sys.stderr)
                return captcha_id, captcha_text
            raise Exception(f"接口响应错误: {api_data.get('msg')}")
        except Exception as e:
            print(f"⚠️ [4399PE] 第 {attempt}/{max_attempts} 次验证码识别失败: {e}", file=sys.stderr)
            if attempt < max_attempts:
                time.sleep(1)
                continue

    print(f"⚠️ [4399PE] 远程识别连续 {max_attempts} 次失败，正在为您切换到手动模式...", file=sys.stderr)
    print(f"请打开验证码 URL 查看图片: {captcha_url}", file=sys.stderr)
    captcha_text = input("请输入看到的 4 位验证码: ").strip().lower()
    return captcha_id, captcha_text


def get_oauth(session):
    callback_config_url = "https://m.4399api.com/openapi/oauth-callback.html?gamekey=44770&game_key=115716"
    oauth_res = session.get(callback_config_url, timeout=10)
    oauth_data = oauth_res.json()

    oauth_url = oauth_data.get("result", "")
    if not oauth_url:
        raise Exception(f"获取 oauth URL 失败: {oauth_res.text}")

    parsed_query = parse_qs(urlparse(oauth_url).query)
    client_id = parsed_query.get("client_id", [""])[0]
    state = parsed_query.get("state", [""])[0]
    ref_val = parsed_query.get("ref", [""])[0]
    return client_id, state, ref_val

def post_login(session, username, password, captcha_id, captcha_text, client_id, state, ref_val):
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
    try:
        login_res = session.post(login_url, data=payload, allow_redirects=False, timeout=10)
    except requests.RequestException as e:
        return None, None, f"request_failed: {e}"

    if login_res.status_code in (301, 302):
        location = login_res.headers.get("Location")
        if not location:
            return None, None, "request_failed: 未获取到重定向 Location"

        print("[4399PE] 捕获到 302 重定向，请求回调地址...", file=sys.stderr)
        callback_res = session.get(location, timeout=10)
        try:
            callback_json = callback_res.json()
        except ValueError:
            return None, None, f"request_failed: 回调结果不是 JSON: {callback_res.text}"

        result_obj = callback_json.get("result", {})
        uid = result_obj.get("uid")
        user_state = result_obj.get("state")
        if not uid or not user_state:
            return None, None, f"request_failed: OAuth 回调数据解析缺少 uid/state: {callback_json}"

        return uid, user_state, "success"

    response_body = login_res.text
    if "验证码错误" in response_body:
        return None, None, "captcha_error"
    error_tip = extract_error_tip(response_body)
    if error_tip:
        return None, None, error_tip
    return None, None, "request_failed: 未知登录错误或密码错误"

def get_sauth_token(username, password) -> str:
    session = requests.Session()
    session.verify = False  # 绕过本地证书校验

    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"})

    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        print(f"[4399PE] 登录循环尝试: 第 {attempt}/{max_attempts} 次", file=sys.stderr)

        captcha_id, captcha_text = get_captcha(session)
        print("[4399PE] Step 2: 获取 OAuth 参数...", file=sys.stderr)
        client_id, state, ref_val = get_oauth(session)
        print("[4399PE] Step 3: 提交登录表单...", file=sys.stderr)
        uid, user_state, status = post_login(
            session,
            username,
            password,
            captcha_id,
            captcha_text,
            client_id,
            state,
            ref_val,
        )

        if status == "success":
            print(
                f"[4399PE] Step 4: 成功获取 uid={uid}, 开始构建 SAuth 凭证...",
                file=sys.stderr,
            )
            sauth_data = {
                "aim_info": json.dumps(
                    {"aim": "127.0.0.1", "country": "CN", "tz": "+0800", "tzid": ""},
                    separators=(",", ":"),
                ),
                "realname": json.dumps(
                    {"realname_type": 2}, separators=(",", ":")
                ),
                "app_channel": "4399com",
                "platform": "ad",
                "client_login_sn": "Random_" + ''.join(random.choices(string.ascii_letters, k=16)),
                "gameid": "x19",
                "login_channel": "4399com",
                "sdk_version": "3.12.2",
                "sdkuid": str(uid),
                "sessionid": str(user_state),
                "udid": generate_pe_udid(),
                "deviceid": "Random_" + ''.join(random.choices(string.ascii_letters, k=16)),
            }
            sauth_json_str = json.dumps(sauth_data, separators=(",", ":"))

            print(
                "[4399PE] Step 5: 正在向网易手游端发送 uni_sauth 激活请求...",
                file=sys.stderr,
            )
            sauth_url = "https://mgbsdk.matrix.netease.com/x19/sdk/uni_sauth"
            sauth_headers = {"Content-Type": "application/json"}
            session.post(
                sauth_url, data=sauth_json_str, headers=sauth_headers, timeout=10
            )
            print(f"[4399PE] uni_sauth 校验端返回完成", file=sys.stderr)

            return json.dumps({"sauth_json": sauth_json_str}, separators=(",", ":"))

        if status == "captcha_error":
            print("[4399PE] 验证码错误，正在返回 Step 1 重新获取验证码...", file=sys.stderr)
            continue

        if status.startswith("request_failed"):
            if attempt < max_attempts:
                print(
                    f"[4399PE] 登录请求失败，正在返回 Step 1 重新尝试... ({status})",
                    file=sys.stderr,
                )
                continue
            raise Exception(status)

        raise Exception(f"4399 登录返回错误: {status}")

    raise Exception("连续多次登录失败，已达到最大重试次数")

# ==================== 调用测试入口 ====================
if __name__ == "__main__":
    os.system('cls')
    print(Fore.GREEN + "网易4399账号转Sauth", file=sys.stderr)
    print(Fore.CYAN + "验证码识别api来自Fantnel\nFantnel官网:https://npyyds.top/", file=sys.stderr)
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