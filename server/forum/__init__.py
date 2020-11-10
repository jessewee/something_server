# -*- coding: utf-8 -*-
import logging
from flask import Blueprint, request
__all__ = ['forum']


forum = Blueprint(
    'forum',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# 设置日志相关
logger = logging.getLogger('forum')
file_handler = logging.FileHandler('data/logs/forum.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logI = lambda *msgs: logger.info(msgs)
logW = lambda *msgs: logger.warning(msgs)
logE = lambda *msgs: logger.error(msgs)


# 测试连接接口
@forum.route('/', methods=['GET', 'POST'])
def test_api():
    if request.method == 'GET':
        content = request.args['param']
    elif request.method == 'POST':
        content = request.values['param']
    else:
        content = '未知的method'
    logI(f'你发送到forum的内容是{content}')
    return f'你发送到forum的内容是{content}'
