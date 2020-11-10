# -*- coding: utf-8 -*-
import psycopg2
import os
import json
from flask_mail import Mail, Message
from flask import current_app
import datetime

DEBUG = True


# 创建数据库连接
def connect_db():
    conn = psycopg2.connect(
        database='something',
        user='postgres',
        password='wsj1989',
        host=os.environ['POSTGRES_HOST'],
        port=os.environ['POSTGRES_PORT'])
    return conn


# 返回数据格式，code是枚举Code的值
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
        else:
            return json.JSONEncoder.default(self, obj)
