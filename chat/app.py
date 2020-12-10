# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import os
import time
import logging

# 设置日志相关
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('app')
file_handler = logging.FileHandler(f'{os.getcwd()}/data/private/logs/app.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logI = lambda *msgs: logger.info(msgs)
logW = lambda *msgs: logger.warning(msgs)
logE = lambda *msgs: logger.error(msgs)

strangers = set()
members = {}

# 检查字符串的长度是否为0，有None判断
def is_empty_str(e):
    if e == None or type(e) != str:
        return True
    return len(e) == 0

# 给所有连接的客户端发消息
async def send_msg_to_clients(msg):
    msg['time'] = int(time.time())
    msg_str = json.dumps(msg)
    for ws in strangers:
        await ws.send(msg_str)
    for ws in list(members.values()):
        await ws.send(msg_str)

# 进入聊天室
async def join_chatroom(websocket, path, msg):
    name = msg['name']
    resp_msg_content = ''
    if is_empty_str(name):
        strangers.add(websocket)
        resp_msg_content = '路人进入了聊天室'
    else:
        members[name] = websocket
        resp_msg_content = f'{name}进入了聊天室'
    await send_msg_to_clients({
        'sender': 'system',
        'type': 'join', 
        'stranger_count': len(strangers), 
        'members': list(members.keys()), 
        'content': resp_msg_content
    })

# 退出聊天室
async def leave_chatroom(websocket, path):
    resp_msg_content = ''
    if websocket in strangers:
        strangers.remove(websocket)
        resp_msg_content = '路人离开了聊天室'
    for k,v in members.items():
        if v == websocket:
            members.pop(k)
            resp_msg_content = f'{k}离开了聊天室'
            break
    if len(resp_msg_content) == 0:
        return
    await send_msg_to_clients({
        'sender': 'system',
        'type': 'leave', 
        'stranger_count': len(strangers), 
        'members': list(members.keys()), 
        'content': resp_msg_content
    })

# 收到消息
async def receive_chat_msg(websocket, path, msg):
    sender = ''
    for k,v in members.items():
        if v == websocket:
            sender = k
    await send_msg_to_clients({
        'sender': sender,
        'type': 'message', 
        'content': msg['content']
    })

# 消息处理
async def handle_received_msg(websocket, path, text):
    msg = json.loads(text)
    msg_type = msg['type']
    # 加入聊天室
    if msg_type == 'join':
        await join_chatroom(websocket, path, msg)
    # 离开聊天室
    elif msg_type == 'leave':
        await leave_chatroom(websocket, path)
    # 聊天消息
    elif msg_type == 'message':
        await receive_chat_msg(websocket, path, msg)

# 主循环入口
async def run(websocket, path):
    while True:
        try:
            text = await websocket.recv()
            logI('收到消息', text)
            await handle_received_msg(websocket, path, text)
        except websockets.ConnectionClosed:
            logI('连接断开', path)
            await leave_chatroom(websocket, path)
            break
        except websockets.InvalidState:
            logW('连接无效')
            break
        except Exception as e:
            logE('Exception', e)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(websockets.serve(run, '0.0.0.0', 8765))
    asyncio.get_event_loop().run_forever()