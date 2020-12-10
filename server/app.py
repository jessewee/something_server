# -*- coding: utf-8 -*-
import logging
from flask import Flask, request, session
from base import base
from forum import forum
import time
import uuid
import os
from pub import response_json, connect_db, DEBUG, is_empty_collection, PRIVATE_FILE_DIR
from error_codes import Codes


app = Flask(__name__, template_folder='templates', static_folder='data/public', static_url_path='/files')
app.config.update(RESTFUL_JSON=dict(ensure_ascii=False))
app.secret_key = 'OJDAOonangoijJKLSDGOdfg'
app.config['JSON_AS_ASCII'] = False  # 返回中文是编码，需要把这个设置False。（没管用）

# 邮件服务
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 587  # 465或587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jessewee@qq.com'
app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']

# 加载蓝图
app.register_blueprint(base, url_prefix='/')
app.register_blueprint(forum, url_prefix='/forum')

# 设置日志相关
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('app')
file_handler = logging.FileHandler(f'{PRIVATE_FILE_DIR}logs/app.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logI = lambda *msgs: logger.info(msgs)
logW = lambda *msgs: logger.warning(msgs)
logE = lambda *msgs: logger.error(msgs)

# 不需要检查token的接口
apis_without_token = ['/', '/login', '/get_vf_code', '/register', '/reset_pwd', '/forum',
                      '/forum/get_posts', '/forum/get_floors', '/forum/get_inner_floors', '/forum/get_post_labels']


# 是否是访问静态文件
def is_static_file(path):
    return path.startswith('/files/')


# 通过refresh_token重新获取token
def refresh_token_and_generate_new():
    refresh_token = request.headers.get('refresh_token')
    if refresh_token == None:
        return None
    db = connect_db()
    account = None
    # 获取session中保存的refresh_token
    last_refresh_token = session.get('refresh_token')
    last_refresh_token_time = session.get('refresh_token_time')
    if last_refresh_token == None:
        # session中没有的话从数据库的用户表里获取信息
        cursor = db.cursor()
        cursor.execute(
            f'''SELECT id,account,refresh_token_time FROM public.user WHERE refresh_token = '{refresh_token}' ''')
        rows = cursor.fetchall()
        if is_empty_collection(rows):
            db.close()
            return response_json(Codes.REFRESH_TOKEN_INVALID)
        account = rows[0][1]
        session['user_id'] = rows[0][0]
        session['account'] = account
        last_refresh_token_time = rows[0][2]
        last_refresh_token = refresh_token
    # 判断服务器的refresh_token和客户端发来的是否一样
    if last_refresh_token != refresh_token:
        db.close()
        return response_json(Codes.REFRESH_TOKEN_INVALID)
    # 判断refresh_token是否已过期 30天
    time_in_seconds = int(time.time())
    if last_refresh_token_time == None or time_in_seconds - last_refresh_token_time > 30 * 24 * 60 * 60:
        db.close()
        return response_json(Codes.REFRESH_TOKEN_INVALID)
    # 生成新的refresh_token和token，并保存到session和数据库中
    refresh_token = uuid.uuid4().hex
    token = uuid.uuid4().hex
    session['refresh_token'] = refresh_token
    session['refresh_token_time'] = time_in_seconds
    session['token'] = token
    session['token_time'] = time_in_seconds
    db.cursor().execute(
        f'''
        UPDATE public.user 
        SET refresh_token = '{refresh_token}', refresh_token_time = {time_in_seconds}
        WHERE account = '{account}'
        ''')
    db.commit()
    db.close()
    return None


# 验证token
def check_token():
    if request.headers.get('refresh_token') != None:
        return None
    token = request.headers.get('token')
    if token == None or session.get('token') != token:
        return response_json(Codes.TOKEN_INVALID)
    last_time = session.get('token_time')
    time_in_seconds = int(time.time())
    if last_time == None or time_in_seconds - last_time > 24 * 60 * 60:  # 1天
        return response_json(Codes.TOKEN_INVALID)
    return None


# 处理第一个请求之前运行
@app.before_first_request
def befor_first_request():
    logI('---------------------------------处理第一个请求之前')


# 在处理每次请求之前运行
@app.before_request
def before_request():
    logI(f'---------------------------------在处理每次请求之前运行')
    # 请求参数
    if DEBUG == True:
        for k in request.values:
            logI(f'请求参数---{k}:{request.values.get(k)}')
        for k in request.headers:
            logI(f'请求header---{k}:{request.headers.get(k)}')
    # 文件
    if is_static_file(request.path):
        return None
    # 不需要验证token
    if request.path in apis_without_token:
        return None
    # 通过refresh_token重新获取token
    result = refresh_token_and_generate_new()
    if result != None:
        return result
    # 验证token
    result = check_token()
    if result != None:
        return result


# 在每次请求之后运行（请求没有异常）
@app.after_request
def after_request(response):
    logI('---------------------------------在每次请求之后运行（请求没有异常）')
    # 文件
    if is_static_file(request.path):
        return response
    if request.path in apis_without_token:
        # 返回参数
        if DEBUG == True:
            logI(f'返回参数---{response.data}')
            for k in response.headers:
                logI(f'返回header---{k}:{response.headers.get(k)}')
        return response
    if request.headers.get('refresh_token') != None:
        if response.headers.get('refresh_token') == None and session.get('refresh_token') != None:
            response.headers['refresh_token'] = session.get('refresh_token')
        if response.headers.get('token') == None and session.get('token') != None:
            response.headers['token'] = session.get('token')
    # 返回参数
    if DEBUG == True:
        logI(f'返回参数---{response.data}')
        for k in response.headers:
            logI(f'返回header---{k}:{response.headers.get(k)}')
    return response


# 每一个请求之后运行，即使遇到了异常
@app.teardown_request
def teardown_request(error):
    if error != None:
        logE('---------------------------------每一个请求之后运行，即使遇到了异常', error)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
