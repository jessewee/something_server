# -*- coding: utf-8 -*-
import uuid
import random
import time
import logging
from flask import Blueprint, request, session
from pub import *
from error_codes import Codes


__all__ = ['base']


base = Blueprint(
    'base',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# 设置日志相关
logger = logging.getLogger('base')
file_handler = logging.FileHandler('data/logs/base.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logI = lambda *msgs: logger.info(msgs)
logW = lambda *msgs: logger.warning(msgs)
logE = lambda *msgs: logger.error(msgs)


# 测试连接接口
@base.route('/', methods=['GET', 'POST'])
def test_api():
    if request.method == 'GET':
        content = request.args['param']
    elif request.method == 'POST':
        content = request.values['param']
    else:
        content = '未知的method'
    logI(f'你发送到base的内容是{content}')
    return f'你发送到base的内容是{content}'


# 获取邮箱验证码
@base.route('/get_vf_code', methods=['GET'])
def get_vf_code():
    email = request.args.get('email')
    if type(email) != str or len(email) == 0:
        return response_json(Codes.EMAIL_EMPTY)
    code = random.randint(100000, 999999)
    db = connect_db()
    db.cursor().execute(
        f'''INSERT INTO vf_code(email, code) VALUES('{email}', '{code}')''')
    db.commit()
    db.close()
    send_email(email, 'something验证码', f'您的验证码是：{code}，10分钟内有效')
    return response_json(Codes.SUCCESS)


# 注册用户
@base.route('/register', methods=['POST'])
def register():
    # 账号
    account = request.values.get('account')
    if type(account) != str or len(account) == 0:
        return response_json(Codes.ACCOUNT_EMPTY)
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(
        f'''SELECT id FROM public.user WHERE account = '{account}' ''')
    rows = cursor.fetchall()
    if rows != None and len(rows) > 0:
        db.close()
        return response_json(Codes.ACCOUNT_EXIST)
    # 密码
    pwd = request.values.get('pwd')
    if type(pwd) != str or len(pwd) == 0:
        return response_json(Codes.PWD_EMPTY)
    # 邮箱和验证码
    email = request.values.get('email')
    vfcode = request.values.get('vfcode')
    if type(email) == str and len(email) > 0:
        if type(vfcode) != str or len(vfcode) == 0:
            return response_json(Codes.VF_CODE_EMPTY)
        # 判断验证码
        cursor = db.cursor()
        cursor.execute(
            # 600秒，10分钟
            f'''SELECT email FROM vf_code WHERE code = '{vfcode}' AND email = '{email}' AND EXTRACT(epoch FROM now() - date) < 600''')
        rows = cursor.fetchall()
        if rows == None or len(rows) == 0:
            db.close()
            return response_json(Codes.VF_CODE_INCORRECT)
    # 处理
    db.cursor().execute(
        f'''INSERT INTO public.user(account, pwd, email) values('{account}', '{pwd}', '{email}')''')
    db.commit()
    db.close()
    # 返回结果
    return response_json(Codes.SUCCESS)


# 找回密码
@base.route('/reset_pwd', methods=['PUT'])
def reset_pwd():
    # 账号
    account = request.values.get('account')
    if type(account) != str or len(account) == 0:
        return response_json(Codes.ACCOUNT_EMPTY)
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(f'''
    SELECT 
        id, 
        (
            SELECT code FROM vf_code 
            WHERE u.email = email AND EXTRACT(epoch FROM now() - date) < 6000 
            ORDER BY date DESC
            LIMIT 1
        ) AS vf_code
    FROM public.user u
    WHERE account = '{account}'
    ''')
    rows = cursor.fetchall()
    if rows == None or len(rows) == 0:
        db.close()
        return response_json(Codes.ACCOUNT_NOT_EXIST)
    # 密码
    pwd = request.values.get('pwd')
    if type(pwd) != str or len(pwd) == 0:
        return response_json(Codes.PWD_EMPTY)
    # 验证码
    vfcode = request.values.get('vfcode')
    if type(vfcode) != str or len(vfcode) == 0:
        return response_json(Codes.VF_CODE_EMPTY)
    # 判断验证码
    if rows[0][1] != vfcode:
        db.close()
        return response_json(Codes.VF_CODE_INCORRECT)
    # 处理
    db.cursor().execute(
        f'''UPDATE public.user SET pwd = '{pwd}' WHERE account = '{account}' ''')
    db.commit()
    db.close()
    # 返回结果
    return response_json(Codes.SUCCESS)


# 登录
@base.route('/login', methods=['GET'])
def login():
    account = request.args.get('account')
    pwd = request.args.get('pwd')
    if account == None:
        return response_json(Codes.ACCOUNT_EMPTY)
    if pwd == None:
        return response_json(Codes.PWD_EMPTY)
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(
        f'''SELECT id,pwd FROM public.user WHERE account = '{account}' ''')
    rows = cursor.fetchall()
    if rows == None or len(rows) == 0:
        db.close()
        return response_json(Codes.ACCOUNT_NOT_EXIST)
    if rows[0][1] != pwd:
        db.close()
        return response_json(Codes.PWD_INCORRECT)
    refresh_token = uuid.uuid4().hex
    token = uuid.uuid4().hex
    time_in_seconds = int(time.time())
    session['user_id'] = rows[0][0]
    session['account'] = account
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
    return response_json(Codes.SUCCESS), 200, {'refresh_token': refresh_token, 'token': token}


# 获取用户信息
@base.route('/get_user_info', methods=['GET'])
def get_user_info():
    user_id = session.get('user_id')
    if user_id == None:
        return response_json(Codes.REFRESH_TOKEN_INVALID)
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(
        f'''SELECT name,avatar,avatar_thumb,gender,birthday,register_date,email FROM public.user WHERE id = {user_id}''')
    rows = cursor.fetchall()
    if rows == None or len(rows) == 0:
        db.close()
        return response_json(Codes.REFRESH_TOKEN_INVALID)
    result = {
        'name': rows[0][0],
        'avatar': rows[0][1],
        'avatar_thumb': rows[0][2],
        'gender': rows[0][3],
        'birthday': rows[0][4],
        'register_date': rows[0][5],
        'email': rows[0][6]
    }
    db.close()
    return response_json(Codes.SUCCESS, result)
