import requests
from typing import Dict,Any

def send_message(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    发消息的通用方法
    """
    headers = {
        'Content-Type': 'application/json',
    }
    response = requests.post(url, json=data, headers=headers)
    return  response.json()

def send_wecom(url, msg):
    """
    企业微信
    """
    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }
    return send_message(url, data)

