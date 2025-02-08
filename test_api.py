from flask import Flask, request, jsonify, Response, send_file
import requests
from flask_cors import CORS
import os
import json
from cachetools import TTLCache
import traceback

app = Flask(__name__)
CORS(app)

print("Starting application...")

# API配置
API_KEY = "39b51c53b8fc459389a1de509524b7df.XZiGZkOeXRQuxNbR"
BASE_URL = "https://open.bigmodel.cn/api/llm-application/open"
APP_ID = "1880145051938672640"

# 缓存配置
variables_cache = TTLCache(maxsize=100, ttl=3600)  # 1小时缓存
conversation_cache = TTLCache(maxsize=1000, ttl=7200)  # 2小时缓存

def get_auth_header():
    return f"Bearer {API_KEY}"

def create_conversation():
    """创建新会话"""
    try:
        url = f"{BASE_URL}/v2/application/{APP_ID}/conversation"
        headers = {
            "Authorization": get_auth_header(),
            "Content-Type": "application/json"
        }
        print(f"Creating conversation with URL: {url}")
        print(f"Headers: {headers}")
        
        response = requests.post(url, headers=headers, timeout=10)
        print(f"Create conversation response: {response.text}")
        
        if response.status_code == 200:
            conv_id = response.json()['data']['conversation_id']
            print(f"Created conversation ID: {conv_id}")
            return conv_id
        else:
            print(f"Failed to create conversation. Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in create_conversation: {str(e)}")
        print(traceback.format_exc())
        return None

def get_cached_variables():
    """获取缓存的变量信息"""
    if 'variables' not in variables_cache:
        url = f"{BASE_URL}/v2/application/{APP_ID}/variables"
        headers = {
            "Authorization": get_auth_header(),
            "Accept": "*/*"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                variables_cache['variables'] = response.json()['data']
        except Exception as e:
            print(f"Error getting variables: {e}")
            return []
    return variables_cache.get('variables', [])

@app.route('/')
def index():
    print("Accessing index page")
    try:
        return send_file('index.html')
    except Exception as e:
        print(f"Error serving index.html: {e}")
        return str(e), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print("\n=== New Chat Request ===")
        user_message = request.json.get('message', '')
        conversation_id = request.json.get('conversation_id')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400

        if not conversation_id:
            conversation_id = create_conversation()
            if not conversation_id:
                return jsonify({'error': '创建会话失败'}), 500

        request_url = f"{BASE_URL}/v2/application/generate_request_id"
        headers = {
            "Authorization": get_auth_header(),
            "Content-Type": "application/json"
        }

        payload = {
            "app_id": APP_ID,
            "conversation_id": conversation_id,
            "key_value_pairs": [{
                "id": "user",
                "type": "input",
                "name": "用户提问",
                "value": user_message
            }]
        }

        def generate():
            try:
                response = requests.post(request_url, headers=headers, json=payload, timeout=10)
                
                if response.status_code != 200:
                    error_msg = response.json().get('message', '请求失败')
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                request_id = response.json()['data']['id']
                sse_url = f"{BASE_URL}/v2/model-api/{request_id}/sse-invoke"
                headers['Accept'] = 'text/event-stream'

                full_response = ""
                response_sent = False  # 添加标志来追踪是否已发送响应
                
                with requests.post(sse_url, headers=headers, stream=True) as response:
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data:'):
                                try:
                                    data = json.loads(line[5:])
                                    if 'msg' in data and data['msg'] and not response_sent:
                                        full_response = data['msg']
                                        yield f"data: {json.dumps({'response': full_response, 'conversation_id': conversation_id})}\n\n"
                                        response_sent = True  # 标记已发送响应
                                except json.JSONDecodeError:
                                    continue
                
                if not response_sent:  # 如果还没有发送过响应
                    yield f"data: {json.dumps({'response': full_response, 'conversation_id': conversation_id})}\n\n"

            except Exception as e:
                print(f"Error in generate: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': '服务器错误',
            'details': str(e)
        }), 500

# 添加一个测试端点
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'ok', 'message': 'API is working'})

if __name__ == '__main__':
    try:
        print("\nStarting server...")
        
        # 检查index.html是否存在
        if os.path.exists('index.html'):
            print("Found index.html in current directory")
        else:
            print("Warning: index.html not found in current directory!")
        
        port = int(os.environ.get('PORT', 5000))
        print(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except Exception as e:
        print(f"Startup error: {str(e)}")
        print(traceback.format_exc())