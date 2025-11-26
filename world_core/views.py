import json
import os
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests
from decouple import config, Csv

# 获取 API 密钥的函数
def get_gemini_api_key():
    """动态获取 Gemini API 密钥"""
    try:
        # 确保从项目根目录查找 .env 文件
        BASE_DIR = Path(__file__).resolve().parent.parent.parent  # world_core 目录
        env_path = BASE_DIR / '.env'
        
        # 方法1: 直接读取 .env 文件
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == 'GEMINI_API_KEY':
                            api_key = value.strip().strip('"').strip("'")
                            if api_key:
                                return api_key
        
        # 方法2: 使用 decouple（切换到项目根目录）
        original_cwd = os.getcwd()
        try:
            os.chdir(str(BASE_DIR))
            api_key = config('GEMINI_API_KEY', default='', cast=str)
            if api_key:
                return api_key
        finally:
            os.chdir(original_cwd)
        
        # 方法3: 从环境变量读取
        return os.getenv('GEMINI_API_KEY', '')
    except Exception as e:
        print(f"--- WARNING: Failed to load GEMINI_API_KEY: {e} ---")
        return os.getenv('GEMINI_API_KEY', '')

# 在模块加载时尝试加载一次（用于诊断）
_initial_key = get_gemini_api_key()
if _initial_key:
    print(f"--- DIAGNOSE: Key loaded successfully, prefix: {_initial_key[:5]} ---")
else:
    print("--- WARNING: GEMINI_API_KEY not found, AI chat will be disabled ---")

# 使用 Gemini 的标准 API 地址和模型名称
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL_NAME = "gemini-2.5-flash" 

# @csrf_exempt 允许没有 CSRF token 的请求
@csrf_exempt
def ai_chat_api(request):
    # 动态获取 API key
    GEMINI_API_KEY = get_gemini_api_key()
    
    if not GEMINI_API_KEY:
        return JsonResponse({'error': 'AI 服务未配置，请设置 GEMINI_API_KEY 环境变量。'}, status=503)
    
    if request.method == 'POST':
        try:
            # 1. 解析前端发来的 JSON 数据
            data = json.loads(request.body.decode('utf-8'))
            user_message = data.get('message', '')

            if not user_message:
                return JsonResponse({'error': '未收到消息'}, status=400)
            
            # 2. 构造发送给 AI 的请求体
            headers = {
                "Content-Type": "application/json",
            }
            
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"你是一个虚拟世界的智能客服，你对我们世界里的玩家和知识树规则了如指掌。请用友好的语气回答以下问题: {user_message}"}]}
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                },
                "systemInstruction": {
                    "parts": [{"text": "你是一个充满智慧和友好的虚拟世界向导，请用启发和鼓励的语气回答用户关于知识、交易或世界规则的问题。"}]
                }
            }

            # 3. 发送请求给 AI 服务器
            api_url = f"{BASE_URL}/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

            response = requests.post(
                api_url, 
                headers=headers, 
                json=payload,
                timeout=30
            )
            response.raise_for_status() # 检查HTTP请求是否成功

            # 4. 解析 AI 返回的结果
            ai_response_json = response.json()
            
            # 检查响应结构
            if 'candidates' not in ai_response_json or len(ai_response_json['candidates']) == 0:
                return JsonResponse({'error': 'AI 返回格式异常'}, status=500)
            
            candidate = ai_response_json['candidates'][0]
            if 'content' not in candidate or 'parts' not in candidate['content']:
                return JsonResponse({'error': 'AI 返回内容格式异常'}, status=500)
            
            parts = candidate['content']['parts']
            if len(parts) == 0 or 'text' not in parts[0]:
                return JsonResponse({'error': 'AI 返回文本格式异常'}, status=500)
            
            ai_text = parts[0]['text']

            # 5. 返回 AI 的回复给前端
            return JsonResponse({'reply': ai_text})

        except requests.exceptions.Timeout:
            print(f"API Request Timeout (Gemini)")
            return JsonResponse({'error': 'AI服务响应超时，请稍后重试。'}, status=504)
        except requests.exceptions.RequestException as e:
            print(f"API Request Error (Gemini): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Error detail: {error_detail}")
                except:
                    print(f"Error status: {e.response.status_code}")
            return JsonResponse({'error': 'AI服务暂时无法连接。'}, status=500)
        except Exception as e:
            print(f"Internal Server Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': '服务器处理请求失败。'}, status=500)

    return JsonResponse({'error': '只接受 POST 请求'}, status=405)