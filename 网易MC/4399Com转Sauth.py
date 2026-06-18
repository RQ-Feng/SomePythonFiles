import json
import time
import urllib3
import uuid
from urllib.parse import parse_qs, urlparse
import requests

# 关闭关闭验证后控制台弹出的黄色安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def generate_captcha_id() -> str:
    """生成 4399 格式的 96 位验证码 ID (由 3 个无分隔符的大写 UUID 组成)"""
    return (uuid.uuid4().hex + uuid.uuid4().hex + uuid.uuid4().hex).upper()


def extract_error_tip(html_text: str) -> str:
    """提取登录页面中的网页错误提示"""
    start_marker = 'login_err_msg">'
    end_marker = "</p>"

    if start_marker in html_text:
        try:
            start_idx = html_text.index(start_marker) + len(start_marker)
            end_idx = html_text.index(end_marker, start_idx)
            return html_text[start_idx:end_idx].strip()
        except ValueError:
            pass
    return ""


def get_sauth_token(username, password) -> str:
    # 建立会话，自动管理全局 CookieContainer
    session = requests.Session()
    session.verify = False  # 绕过本地证书验证问题

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
    )

    print("[1/4] 正在获取 OAuth 回调参数...")
    oauth_url = "https://m.4399api.com/openapi/oauth-callback.html?gamekey=44770&game_key=115716"
    oauth_res = session.get(oauth_url)
    oauth_data = oauth_res.json()

    if not oauth_data or "result" not in oauth_data:
        raise Exception(f"无法获取 OAuth 回调配置: {oauth_res.text}")

    result_obj = oauth_data["result"]

    if isinstance(result_obj, str):
        parsed_query = parse_qs(urlparse(result_obj).query)
        client_id = parsed_query.get("client_id", [""])[0]
        state = parsed_query.get("state", [""])[0]
        ref_val = parsed_query.get("ref", [""])[0]
    else:
        client_id = result_obj.get("client_id", "")
        state = result_obj.get("state", "")
        ref_val = result_obj.get("ref", "")

    print("[2/4] 正在获取并识别验证码...")
    captcha_id = generate_captcha_id()
    captcha_url = (
        f"https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={captcha_id}"
    )
    captcha_res = session.get(captcha_url)

    # 🔄 替换后的远程 API 识别逻辑
    captcha_text = ""
    api_url = "http://110.42.70.32:13423/api/fantnel/captcha"
    try:
        print("正在发送图片到远程接口识别...")
        # 将验证码图片的二进制流 (content) 直接作为 Body 传入 POST 请求
        api_res = session.post(api_url, data=captcha_res.content, timeout=8)
        api_data = api_res.json()

        if api_data.get("code") == 1:
            captcha_text = str(api_data.get("data", "")).strip().lower()
            print(f"远程 API 自动识别成功: {captcha_text}")
        else:
            raise Exception(f"接口响应 code 错误: {api_data.get('msg')}")
    except Exception as e:
        # 如果远程 API 挂了、超时或者识别失败，降级为手动输入，确保程序不崩溃
        print(f"⚠️ 远程识别失败 ({e})，正在为您切换到手动模式...")
        print(f"请在浏览器中打开验证码 URL 查看图片:\n{captcha_url}")
        captcha_text = input("请输入看到的 4 位验证码: ").strip().lower()

    print("[3/4] 正在提交登录认证...")
    payload = {
        "isInputRealname": "false",
        "isVaildRealname": "false",
        "sec": "0",
        "client_id": client_id,
        "state": state,
        "ref": ref_val,
        "response_type": "TOKEN",
        "scope": "basic",
        "bizId": "2100001792",
        "auth_action": "ORILOGIN",
        "redirect_uri": "https://m.4399api.com/openapi/oauth-callback.html?gamekey=44770&game_key=115716",
        "username": username,
        "password": password,
        "captcha_id": captcha_id,
        "captcha": captcha_text,
    }

    login_url = "https://ptlogin.4399.com/oauth2/loginAndAuthorize.do?channel=&sdk=op&sdk_version=3.14.5.577"
    login_res = session.post(login_url, data=payload)
    login_text = login_res.text

    error_tip = extract_error_tip(login_text)
    if error_tip:
        raise Exception(f"4399 登录返回错误: {error_tip}")

    try:
        user_info = login_res.json()
    except json.JSONDecodeError:
        raise Exception(f"无法解析返回的登录响应数据: {login_text}")

    if user_info.get("code") != "100":
        raise Exception(f"登录失败: {user_info.get('message', '未知错误')}")

    user_result = user_info.get("result", {})
    uid = str(user_result.get("uid", ""))
    user_state = str(user_result.get("state", ""))

    print("[4/4] 登录验证成功，正在构建 SAuth 凭证...")

    sauth_data = {
        "gameid": "x19",
        "login_channel": "4399com",
        "app_channel": "4399com",
        "platform": "pc",
        "sdkuid": uid,
        "sessionid": user_state,
        "sdk_version": "1.0.0",
        "udid": uuid.uuid4().hex.upper(),
        "deviceid": uuid.uuid4().hex.upper(),
        "aim_info": json.dumps(
            {"aim": "127.0.0.1", "country": "CN", "tz": "0800", "tzid": ""},
            separators=(",", ":"),
        ),
        "client_login_sn": uuid.uuid4().hex.upper(),
        "gas_token": "",
        "source_platform": "pc",
        "userid": username,
        "realname": json.dumps(
            {"realname_type": "0"}, separators=(",", ":")
        ),
        "timestamp": str(int(time.time())),
    }

    inner_json = json.dumps(sauth_data, separators=(",", ":"))
    final_sauth = json.dumps(
        {"sauth_json": inner_json}, separators=(",", ":")
    )

    return final_sauth


# ==================== 调用测试入口 ====================
if __name__ == "__main__":
    USER = input("请输入4399账号: ")
    PASS = input("请输入4399密码: ")

    try:
        sauth_result = get_sauth_token(USER, PASS)
        print("\n🎉 生成成功！最终的 Sauth 结果如下：")
        print(sauth_result)
    except Exception as e:
        print(f"\n❌ 程序运行异常: {e}")