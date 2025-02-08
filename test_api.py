from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
import time
import hashlib
import base64
import hmac
import json

app = Flask(__name__)
CORS(app)

# API配置
API_KEY = "39b51c53b8fc459389a1de509524b7df.XZiGZkOeXRQuxNbR"
BASE_URL = "https://open.bigmodel.cn/api/llm-application/open"
APP_ID = "1880145051938672640"  # 更新为正确的应用ID

def get_auth_header():
    """获取认证头"""
    return f"Bearer {API_KEY}"

def get_application_variables():
    """获取应用变量信息"""
    try:
        url = f"{BASE_URL}/v2/application/{APP_ID}/variables"
        headers = {
            "Authorization": get_auth_header(),
            "Accept": "*/*"
        }
        
        print(f"Getting variables from: {url}")
        print(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers)
        print(f"Variables response: {response.text}")
        
        if response.status_code == 200:
            return response.json()['data']
        else:
            raise Exception(f"获取变量失败: {response.text}")
    except Exception as e:
        print(f"Error getting variables: {str(e)}")
        raise

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # 获取应用变量信息
        variables = get_application_variables()
        print("Application variables:", variables)
        
        user_message = request.json.get('message', '')
        conversation_id = request.json.get('conversation_id')
        
        # 如果没有会话ID，创建新会话
        if not conversation_id:
            url = f"{BASE_URL}/v2/application/{APP_ID}/conversation"
            headers = {
                "Authorization": get_auth_header(),
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"创建会话失败: {response.text}")
            conversation_id = response.json()['data']['conversation_id']
            print(f"Created new conversation: {conversation_id}")
        
        # 创建对话请求
        request_url = f"{BASE_URL}/v2/application/generate_request_id"
        headers = {
            "Authorization": get_auth_header(),
            "Content-Type": "application/json"
        }
        
        # 根据应用变量构建请求体
        key_value_pairs = []
        for var in variables:
            if var['type'] == 'input' and var.get('name') == '用户提问':
                key_value_pairs.append({
                    "id": var['id'],
                    "type": "input",
                    "name": var['name'],
                    "value": user_message
                })
        
        if not key_value_pairs:
            # 如果没有找到匹配的变量，使用默认格式
            key_value_pairs = [{
                "id": "user",
                "type": "input",
                "name": "用户提问",
                "value": user_message
            }]
        
        payload = {
            "app_id": APP_ID,
            "conversation_id": conversation_id,
            "key_value_pairs": key_value_pairs
        }
        
        print(f"Request URL: {request_url}")
        print(f"Headers: {headers}")
        print(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.post(request_url, headers=headers, json=payload)
        print(f"Generate request response: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"创建对话请求失败: {response.text}")
        
        request_id = response.json()['data']['id']
        
        # 获取对话结果
        sse_url = f"{BASE_URL}/v2/model-api/{request_id}/sse-invoke"
        headers = {
            "Authorization": get_auth_header(),
            "Accept": "text/event-stream"
        }
        
        response = requests.post(sse_url, headers=headers, stream=True)
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                print(f"SSE line: {line}")
                if line.startswith('data:'):
                    try:
                        data = json.loads(line[5:])
                        if 'msg' in data:
                            full_response += data['msg']
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON: {line[5:]}")
        
        return jsonify({
            'response': full_response,
            'conversation_id': conversation_id
        })
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'error': '服务器错误',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    # 启动时先测试获取变量
    try:
        variables = get_application_variables()
        print("Successfully got variables:", variables)
    except Exception as e:
        print("Failed to get variables:", str(e))
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)