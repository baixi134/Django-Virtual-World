import json
import os
from pathlib import Path
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
import requests
from decouple import config
from .models import MindNode, Player, Transaction
from .forms import PlayerRegisterForm, NodeForm, TransferForm

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

# 使用 Gemini 的标准 API 地址
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL_NAME = "gemini-1.5-flash"

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
# 首页：展示大家发的内容
def index(request):
    nodes = MindNode.objects.all().order_by('-created_at') # 按时间倒序，新的在上面
    context = {'nodes': nodes}
    return render(request, 'index.html', context)

# 注册页：处理新用户加入
def register(request):
    if request.method == 'POST':
        # 如果用户提交了数据
        form = PlayerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save() # 保存到数据库
            login(request, user) # 注册完直接帮他登录
            return redirect('index') # 只有成功才跳转回首页
    else:
        # 如果用户只是打开页面
        form = PlayerRegisterForm()
    
    return render(request, 'register.html', {'form': form})
# 新增：发布观点
@login_required # 这个魔法装饰器表示：只有登录了才能访问这个页面！
def create_node(request):
    if request.method == 'POST':
        form = NodeForm(request.POST)
        if form.is_valid():
            node = form.save(commit=False) # 先暂停保存，因为我们还差一个数据
            node.creator = request.user    # 把“发帖人”设为当前登录的用户
            node.save()                    # 现在才真正保存到数据库
            return redirect('index')       # 发完回首页
    else:
        form = NodeForm()
    
    return render(request, 'create_node.html', {'form': form})
# 新增：转账逻辑
@login_required
def transfer_coins(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            recipient_name = form.cleaned_data['recipient_username']
            amount = form.cleaned_data['amount']
            sender = request.user

            try:
                # 1. 找人：确认对方是否存在
                recipient = Player.objects.get(username=recipient_name)
                
                # 2. 查钱：确认余额是否充足
                if sender.coins >= amount:
                    # 3. 动手：开启“安全模式”(atomic)，保证下面三步要么都做，要么都不做
                    with transaction.atomic():
                        sender.coins -= amount
                        sender.save()
                        
                        recipient.coins += amount
                        recipient.save()
                        
                        # 记账
                        Transaction.objects.create(sender=sender, recipient=recipient, amount=amount)
                    
                    # 成功后回首页
                    return redirect('index')
                else:
                    form.add_error('amount', '你的余额不足！')
            
            except Player.DoesNotExist:
                form.add_error('recipient_username', '查无此人，请检查用户名。')
    else:
        form = TransferForm()
    
    return render(request, 'transfer.html', {'form': form})

# 新增：给帖子打赏
@login_required
def tip_node(request, node_id):
    # 1. 找到这篇帖子，找不到就报错 404
    node = get_object_or_404(MindNode, id=node_id)
    
    if request.method == 'POST':
        # 获取用户想打赏多少钱
        amount = int(request.POST.get('amount'))
        sender = request.user
        recipient = node.creator # 接收者就是帖子的作者

        # 不能给自己打赏
        if sender == recipient:
            messages.error(request, "不能给自己打赏哦！")
        # 余额不足
        elif sender.coins < amount:
            messages.error(request, "余额不足！")
        else:
            # 开启交易事务
            with transaction.atomic():
                sender.coins -= amount
                sender.save()
                
                recipient.coins += amount
                recipient.save()
                
                # 记账 (这里我们稍微改一下备注，方便区分)
                Transaction.objects.create(sender=sender, recipient=recipient, amount=amount)
            
            messages.success(request, f"成功打赏给 {recipient.username} {amount} 金币！")
            return redirect('index')

    return render(request, 'tip_node.html', {'node': node})

def logout_view(request):
    logout(request)
    return redirect('index') # 退出后回首页
# 新增：查看节点详情（并且列出它的子节点）
def node_detail(request, node_id):
    # 找到当前这个节点
    node = get_object_or_404(MindNode, id=node_id)
    # 找到所有属于这个节点的子节点（树枝）
    children = node.children.all()
    
    return render(request, 'node_detail.html', {'node': node, 'children': children})

# 新增：创建子节点（分支）
@login_required
def create_child_node(request, parent_id):
    parent_node = get_object_or_404(MindNode, id=parent_id)
    
    if request.method == 'POST':
        form = NodeForm(request.POST)
        if form.is_valid():
            new_node = form.save(commit=False)
            new_node.creator = request.user
            new_node.parent = parent_node  # 关键：设置父亲是谁
            new_node.save()
            return redirect('node_detail', node_id=parent_id) # 创建完回到父亲的详情页
    else:
        form = NodeForm()
    
    return render(request, 'create_child.html', {'form': form, 'parent_node': parent_node})