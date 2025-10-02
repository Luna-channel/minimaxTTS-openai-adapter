from flask import Flask, request, Response, jsonify
import requests
import json
import io

app = Flask(__name__)
minimax_url = "https://api.minimax.chat/v1/t2a_v2"

def safe_parse_voice_parameter(voice_input):
    if not voice_input:
        return None
    
    # 如果包含等号（半角或全角），则解析出voice_id
    if '=' in voice_input or '＝' in voice_input:
        # 将全角等号替换为半角等号
        normalized = voice_input.replace('＝', '=')
        # 分割并取等号后面的部分
        parts = normalized.split('=', 1)
        if len(parts) == 2:
            voice_id = parts[1].strip()
            print(f"Parsed voice_id from '{voice_input}': '{voice_id}'")
            return voice_id
    
    # 如果不包含等号，直接返回原值（现有软件的正常使用方式）
    return voice_input

@app.route("/audio/speech", methods=["POST"])
def test():
    # 获取认证信息 (Authorization header)
    client_auth = request.headers.get("Authorization")

    if not client_auth:
        print("Error: Authorization header is missing")
        return {"error": "Authorization header is missing"}, 401

    # 从 POST 请求的 JSON body 中获取必需的字段
    json_data = request.get_json()
    model = json_data.get("model")  # 模型 - 必需
    voice_raw = json_data.get("voice")  # 声音参数
    text = json_data.get("input")  # 文本 - 必需

    # 安全解析voice参数，确保向后兼容
    voice = safe_parse_voice_parameter(voice_raw)

    # 检查必需的字段是否存在
    if not all([model, voice, text]):
        print(f"Error: Missing required fields from OM. Received: model={model}, voice_raw={voice_raw}, voice_parsed={voice}, input={text}")
        return jsonify({"error": "缺少必需字段（model、voice、input）"}), 400

    headers = {
        "Authorization": client_auth,
        "Content-Type": "application/json"
    }

    # --- 构造 voice_setting 对象 ---
    # 先初始化 voice_setting，只包含 voice_id
    voice_setting = {
        "voice_id": voice
    }

    # 从 URL 查询参数 (query parameters) 中获取可选的 voice_setting 参数
    # `request.args.get()` 用于获取 URL 查询参数，即使是 POST 请求也可以
    speed_param = request.args.get('speed')
    vol_param = request.args.get('vol')
    pitch_param = request.args.get('pitch')

    # 处理 speed (语速) 参数
    if speed_param is not None:
        try:
            speed_val = float(speed_param)
            # 可以在这里添加范围校验，但通常让下游API（Minimax）处理更严格的校验
            # 根据文档 speed 范围 [0.5, 2]
            if 0.5 <= speed_val <= 2.0:
                voice_setting["speed"] = speed_val
            else:
                print(f"Warning: Speed value {speed_val} is out of recommended range [0.5, 2.0]. Passing as is.")
                voice_setting["speed"] = speed_val # 即使超出范围也传递，让Minimax决定
        except ValueError:
            print(f"Warning: Invalid speed value '{speed_param}'. Skipping speed parameter.")

    # 处理 vol (音量) 参数
    if vol_param is not None:
        try:
            vol_val = float(vol_param)
            # 根据文档 vol 范围 (0, 10]
            if 0 < vol_val <= 10.0:
                voice_setting["vol"] = vol_val
            else:
                print(f"Warning: Volume value {vol_val} is out of recommended range (0, 10.0]. Passing as is.")
                voice_setting["vol"] = vol_val # 即使超出范围也传递
        except ValueError:
            print(f"Warning: Invalid volume value '{vol_param}'. Skipping volume parameter.")

    # 处理 pitch (语调) 参数
    if pitch_param is not None:
        try:
            # 语调通常是整数，但为了兼容性，先尝试转浮点再转整数
            pitch_val = int(float(pitch_param))
            # 根据文档 pitch 范围 [-12, 12]
            if -12 <= pitch_val <= 12:
                voice_setting["pitch"] = pitch_val
            else:
                print(f"Warning: Pitch value {pitch_val} is out of recommended range [-12, 12]. Passing as is.")
                voice_setting["pitch"] = pitch_val # 即使超出范围也传递
        except ValueError:
            print(f"Warning: Invalid pitch value '{pitch_param}'. Skipping pitch parameter.")


    # --- 构造发给 Minimax 的完整 payload ---
    payload = {
        "model": model,          
        "text": text,            
        "stream": False,         # 根据文档固定为 False
        "voice_setting": voice_setting # 使用上面构建好的 voice_setting 字典，包含了可选参数
    }

    # --- 【隐私保护升级！】创建用于打印日志的副本 ---
    # 1. 复制一份 payload，避免修改原始数据
    log_payload = payload.copy()
    # 2. 如果文本长度超过10个字符，就截取前10个并加上省略号
    if len(text) > 10:
        text_for_log = f"{text[:10]}..."
    else:
        text_for_log = text
    # 3. 在日志副本中，用缩短后的文本替换原始文本
    log_payload['text'] = text_for_log

    # 4. 打印修改后的日志副本，而不是原始 payload
    print(f"Sending payload to Minimax (text truncated for privacy): {json.dumps(log_payload, indent=2, ensure_ascii=False)}")


    # === 请求 Minimax API ===
    response = requests.post(minimax_url, headers=headers, data=json.dumps(payload))

    if response.status_code != 200:
        # 尝试解析Minimax返回的错误信息
        error_message = "未知错误"
        try:
            minimax_error = response.json()
            error_message = minimax_error.get("base_resp", {}).get("message", response.text)
        except json.JSONDecodeError:
            error_message = response.text

        print(f"Error calling Minimax API: Status {response.status_code}, Message: {error_message}")
        return jsonify({
            "error": "调用 Minimax 接口失败",
            "status_code": response.status_code,
            "message": error_message
        }), 500

    print("Minimax API 响应成功。")

    result = response.json()
    
    # === 检查Minimax是否返回了任务失败信息 ===
    if "base_resp" in result:
        base_resp = result["base_resp"]
        status_code = base_resp.get("status_code")
        status_msg = base_resp.get("status_msg", "未知错误")
        
        # 如果status_code不是0，说明任务失败
        if status_code != 0:
            print(f"Minimax task failed: status_code={status_code}, status_msg={status_msg}")
            return jsonify({
                "error": status_msg,
                "status_code": status_code,
                "status_msg": status_msg
            }), 500
    
    # === 检查是否有音频数据 ===
    audio_str = result.get("data", {}).get("audio", "")
    if not audio_str:
        print("Error: Audio field not found in Minimax response.")
        return jsonify({"error": "返回中未找到音频字段"}), 500

    # 将十六进制字符串转换为字节
    audio_bytes = bytes.fromhex(audio_str)
    
    # === 返回音频内容作为流 ===
    return Response(
        io.BytesIO(audio_bytes),
        mimetype="audio/mpeg", 
        headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-cache",
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)