# -*- coding: utf-8 -*-
import psycopg2
import os
import json
from flask_mail import Mail, Message
from flask import current_app
import datetime

DEBUG = True


# 检查字符串的长度是否为0，有None判断
def is_empty_str(e):
    if e == None or type(e) != str:
        return True
    return len(e) == 0


def is_not_empty_str(e):
    if e == None or type(e) != str:
        return False
    return len(e) > 0


def is_all_empty_str(*vare):
    for e in vare:
        if is_not_empty_str(e):
            return False
    return True


# 检查列表或元组的长度是否为0，有None判断
def is_empty_collection(e):
    if e == None or (type(e) != list and type(e) != tuple):
        return True
    return len(e) == 0


def is_not_empty_collection(e):
    if e == None or (type(e) != list and type(e) != tuple):
        return False
    return len(e) > 0


# 创建数据库连接
def connect_db():
    conn = psycopg2.connect(
        database='something',
        user='postgres',
        password='wsj1989',
        host=os.environ['POSTGRES_HOST'],
        port=os.environ['POSTGRES_PORT'])
    return conn


# 返回数据格式，code是枚举Codes的值
def response_json(code, data=None):
    if data == None:
        return json.dumps({'code': code.value, 'msg': code.msg()})
    else:
        return json.dumps({'code': code.value, 'msg': code.msg(), 'data': data}, cls=JsonAboutEncoder)


# 发送邮件
def send_email(recipient, title, content):
    msg = Message(title, sender='jessewee@qq.com', recipients=[recipient])
    msg.body = content
    mail = Mail(current_app)
    with current_app.app_context():
        mail.send(msg)


# json格式化相关
class JsonAboutEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, datetime.time):
            return obj.strftime("%H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)
