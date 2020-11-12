# -*- coding: utf-8 -*-
import uuid
import random
import time
import logging
from flask import Blueprint, request, session
from pub import *
from error_codes import Codes
from PIL import Image


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
    if is_empty_str(email):
        return response_json(Codes.EMAIL_EMPTY)
    code = random.randint(100000, 999999)
    db = connect_db()
    db.cursor().execute(f'''
        INSERT INTO vf_code(email, code) 
        VALUES('{email}', '{code}')
        ''')
    db.commit()
    db.close()
    send_email(email, 'something验证码', f'您的验证码是：{code}，10分钟内有效')
    return response_json(Codes.SUCCESS)


# 注册用户
@base.route('/register', methods=['POST'])
def register():
    # 账号
    account = request.values.get('account')
    if is_empty_str(account):
        return response_json(Codes.ACCOUNT_EMPTY)
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(f'''
        SELECT id 
        FROM public.user 
        WHERE account = '{account}'
        ''')
    rows = cursor.fetchall()
    if is_not_empty_collection(rows):
        db.close()
        return response_json(Codes.ACCOUNT_EXIST)
    # 密码
    pwd = request.values.get('pwd')
    if is_empty_str(pwd):
        return response_json(Codes.PWD_EMPTY)
    # 邮箱和验证码
    email = request.values.get('email')
    vfcode = request.values.get('vfcode')
    if is_empty_str(email):
        if is_empty_str(vfcode):
            return response_json(Codes.VF_CODE_EMPTY)
        # 判断验证码
        cursor = db.cursor()
        # 600秒，10分钟
        cursor.execute(f'''
            SELECT email 
            FROM vf_code 
            WHERE code = '{vfcode}' AND email = '{email}' AND EXTRACT(epoch FROM now() - date) < 600
            ''')
        rows = cursor.fetchall()
        if is_empty_collection(rows):
            db.close()
            return response_json(Codes.VF_CODE_INCORRECT)
    # 处理
    db.cursor().execute(f'''
        INSERT INTO public.user(name,account, pwd, email) 
        values('{account}','{account}','{pwd}','{email}')
        ''')
    db.commit()
    db.close()
    # 返回结果
    return response_json(Codes.SUCCESS)


# 找回密码
@base.route('/reset_pwd', methods=['PUT'])
def reset_pwd():
    # 账号
    account = request.values.get('account')
    if is_empty_str(account):
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
    if is_empty_collection(rows):
        db.close()
        return response_json(Codes.ACCOUNT_NOT_EXIST)
    # 密码
    pwd = request.values.get('pwd')
    if is_empty_str(pwd):
        return response_json(Codes.PWD_EMPTY)
    # 验证码
    vfcode = request.values.get('vfcode')
    if is_empty_str(vfcode):
        return response_json(Codes.VF_CODE_EMPTY)
    # 判断验证码
    if rows[0][1] != vfcode:
        db.close()
        return response_json(Codes.VF_CODE_INCORRECT)
    # 处理
    db.cursor().execute(f'''
        UPDATE public.user 
        SET pwd = '{pwd}' 
        WHERE account = '{account}'
        ''')
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
    cursor.execute(f'''
        SELECT id,pwd 
        FROM public.user 
        WHERE account = '{account}'
        ''')
    rows = cursor.fetchall()
    if is_empty_collection(rows):
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
    db.cursor().execute(f'''
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
    cursor.execute(f'''
        SELECT name,avatar,avatar_thumb,gender,birthday,register_date,email,remark 
        FROM public.user 
        WHERE id = {user_id}
        ''')
    rows = cursor.fetchall()
    if is_empty_collection(rows):
        db.close()
        return response_json(Codes.REFRESH_TOKEN_INVALID)
    result = {
        'name': rows[0][0],
        'avatar': rows[0][1],
        'avatar_thumb': rows[0][2],
        'gender': rows[0][3],
        'birthday': rows[0][4],
        'register_date': rows[0][5],
        'email': rows[0][6],
        'remark': rows[0][7]
    }
    db.close()
    return response_json(Codes.SUCCESS, result)


# 修改用户信息
@base.route('/update_user_info', methods=['PUT'])
def update_user_info():
    user_id = session.get('user_id')
    name = request.values.get('name')
    avatar = request.values.get('avatar')
    avatar_thumb = request.values.get('avatar_thumb')
    gender = request.values.get('gender')
    birthday = request.values.get('birthday')
    register_date = request.values.get('register_date')
    email = request.values.get('email')
    remark = request.values.get('remark')
    if is_all_empty_str(name, avatar, avatar_thumb, gender, birthday, register_date, email, remark):
        return response_json(Codes.PARAM_INCORRECT)
    db = connect_db()
    cursor = db.cursor()
    # 检查重名
    cursor.execute(
        f'''SELECT COUNT(id) FROM public.user WHERE name = '{name}' ''')
    existed = cursor.fetchall()
    if is_not_empty_collection(existed):
        db.close()
        return response_json(Codes.NAME_EXISTED)
    # 组装sql
    sql_part_value = ''
    if is_not_empty_str(name):
        sql_part_value = f'name={name}'
    if is_not_empty_str(avatar):
        if len(sql_part_value) == 0:
            sql_part_value = f'avatar={avatar}'
        else:
            sql_part_value += f',avatar={avatar}'
    if is_not_empty_str(avatar_thumb):
        if len(sql_part_value) == 0:
            sql_part_value = f'avatar_thumb={avatar_thumb}'
        else:
            sql_part_value += f',avatar_thumb={avatar_thumb}'
    if is_not_empty_str(gender):
        if len(sql_part_value) == 0:
            sql_part_value = f'gender={gender}'
        else:
            sql_part_value += f',gender={gender}'
    if is_not_empty_str(birthday):
        if len(sql_part_value) == 0:
            sql_part_value = f'birthday={birthday}'
        else:
            sql_part_value += f',birthday={birthday}'
    if is_not_empty_str(register_date):
        if len(sql_part_value) == 0:
            sql_part_value = f'register_date={register_date}'
        else:
            sql_part_value += f',register_date={register_date}'
    if is_not_empty_str(email):
        if len(sql_part_value) == 0:
            sql_part_value = f'email={email}'
        else:
            sql_part_value += f',email={email}'
    if is_not_empty_str(remark):
        if len(sql_part_value) == 0:
            sql_part_value = f'remark={remark}'
        else:
            sql_part_value += f',remark={remark}'
    cursor.execute(
        f'UPDATE public.user SET {sql_part_value} WHERE id = {user_id}')
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS)


# 上传文件，只考虑一次上传一个文件的情况
@base.route('/upload', methods=['POST'])
def upload():
    if request.files == None or len(request.files) == 0:
        return response_json(Codes.NO_FILE_RECEIVED)
    file = request.files['file']
    file_data = file.read()
    if len(file_data) == 0:
        return response_json(Codes.NO_FILE_RECEIVED)
    file_type = request.values.get('type')
    # 源文件保存到本地时的文件名
    file_name_head = time.strftime(r'%y%m%d%H%M%S', time.localtime())
    file_name = file_name_head + str(time.time()).split('.')[1]
    thumb_file_path = None
    # 图片文件
    if file_type == 'image':
        file_path = f'data/images/{file_name}{file.filename[-4:]}'
        file.save(file_path)
        # 获取缩略图
        im = Image.open(file_path)
        if im.size[0] > 360:
            target_h = im.size[1] / im.size[0] * 360
            im.thumbnail((360, target_h))
            thumb_file_path = f'{file_path[:-4]}_thumb{file_path[-4:]}'
            im.save(thumb_file_path)
    # 视频文件
    elif file_type == 'video':
        file_path = f'data/videos/{file_name}{file.filename[-4:]}'
        file.save(file_path)
        # TODO 视频缩略图
        thumb_file_path = ''
    # 音频文件
    elif file_type == 'voice':
        file_path = f'data/others/{file_name}{file.filename[-4:]}'
        file.save(file_path)
    # 未知类型
    else:
        file_type = 'unknown'
        file_path = f'data/others/{file_name}{file.filename[-4:]}'
        file.save(file_path)
    # 保存信息到数据库
    db = connect_db()
    cursor = db.cursor()
    if thumb_file_path == None:
        thumb_file_path = file_path
    cursor.execute(f'''
        INSERT INTO public.files(type,url,thumb_url) 
        VALUES('{file_type}','{file_path}','{thumb_file_path}')
        RETURNING id
        ''')
    info = cursor.fetchone()
    resp_data = {
        'id': info[0],
        'type': file_type,
        'url': file_path,
        'thumb_url': thumb_file_path
    }
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS, resp_data)
