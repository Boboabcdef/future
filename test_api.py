from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

API_KEY = "39b51c53b8fc459389a1de509524b7df.XZiGZkOeXRQuxNbR"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message', '')
        
        payload = {
            "model": "glm-4",
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload
        )
        
        print("Status Code:", response.status_code)  # 调试信息
        print("Response:", response.text)  # 调试信息
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return jsonify({'response': ai_response})
        else:
            return jsonify({
                'error': f'API调用失败: {response.status_code}',
                'details': response.text
            }), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")  # 调试信息
        return jsonify({
            'error': '服务器错误',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)