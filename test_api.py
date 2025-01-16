from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = "iCSwD8g0yUfSO2kLjdHxDAB2"
SECRET_KEY = "gEcWnkQvOdxSbm9w9JSoKLBLWaEBX3xK"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # 1. 获取 access_token
        token_response = requests.post(
            'https://aip.baidubce.com/oauth/2.0/token',
            params={
                'grant_type': 'client_credentials',
                'client_id': API_KEY,
                'client_secret': SECRET_KEY
            }
        )
        access_token = token_response.json()['access_token']

        # 2. 获取用户消息
        user_message = request.json.get('message', '')
        
        # 3. 调用文心一言API
        chat_response = requests.post(
            f'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}',
            json={
                'messages': [{
                    'role': 'user',
                    'content': user_message
                }]
            }
        )
        
        return jsonify(chat_response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)