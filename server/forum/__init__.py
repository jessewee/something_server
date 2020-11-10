# -*- coding: utf-8 -*-
import logging
from flask import Blueprint, request, session
from pub import connect_db, response_json
from error_codes import Codes

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


# 获取帖子列表
@forum.route('/get_posts', methods=['GET'])
def get_posts():
    data_idx = int(request.values.get('data_idx'))
    data_count = int(request.values.get('data_count'))
    sort_by = int(request.values.get('sort_by'))
    search_content = request.values.get('search_content')
    labels = request.values.get('labels')
    users = request.values.get('users')
    user_id = session.get('user_id')
    # 查询帖子列表
    db = connect_db()
    cursor = db.cursor()
    # 用户已登录的话要查询登录人是否已关注发帖人，登录人对帖子的点赞状态
    sql_part_attitude_post_followed = None
    if user_id == None:
        sql_part_attitude_post_followed = 'NULL AS attitude,false AS poster_followed'
    else:
        sql_part_attitude_post_followed = f'''
               (SELECT attitude FROM forum.attitude_to_post WHERE post_base_id = p.id AND user_id = {user_id} LIMIT 1) AS attitude,
               (SELECT COUNT(id) FROM forum.following WHERE to_user_id = p.id AND from_user_id = {user_id}) > 0 AS poster_followed
        '''
    # 排序条件
    sql_part_sort = None
    if sort_by == 2:
        sql_part_sort = 'ORDER BY p.reply_count DESC'
    else:
        sql_part_sort = 'ORDER BY p.date DESC'
    # 筛选条件
    sql_part_condition = ''
    if search_content != None and len(search_content) > 0:
        sql_part_condition += f'''(WHERE text LIKE '%{search_content}%' OR name LIKE '%{search_content}%')'''
    if labels != None and len(labels) > 0:
        tmp = labels.replace(',', '\',\'')
        tmp = f'''label IN ('{tmp}')'''
        if len(sql_part_condition) > 0:
            sql_part_condition += f' AND {tmp}'
        else:
            sql_part_condition += f'WHERE {tmp}'
    if users != None and len(users) > 0:
        tmp = f'''poster_id IN ({users})'''
        if len(sql_part_condition) > 0:
            sql_part_condition += f' AND {tmp}'
        else:
            sql_part_condition += f'WHERE {tmp}'
    # 执行查询
    cursor.execute(f'''
    SELECT p.id,
           poster_id,
           date,
           text,
           medias,
           like_count,
           dislike_count,
           reply_count,
           name,
           avatar,
           avatar_thumb,
           label,
           {sql_part_attitude_post_followed}
    FROM forum.post p
    LEFT JOIN public.user u ON p.poster_id = u.id
    LEFT JOIN forum.post_label l ON p.label_id = l.id
    {sql_part_condition}
    {sql_part_sort}
    LIMIT {data_count} OFFSET {data_idx}
    ''')
    rows = cursor.fetchall()
    posts = []
    if rows != None and len(rows) > 0:
        for r in rows:
            # 查询图片视频
            tmp = r[4]
            medias = []
            c = db.cursor()
            c.execute(
                f'SELECT type,url,thumb_url,width,height FROM public.files WHERE id IN ({tmp})')
            tmp = c.fetchall()
            if tmp != None and len(tmp) > 0:
                for t in tmp:
                    medias.append({
                        'type': t[0],
                        'url': t[1],
                        'thumb_url': t[2],
                        'width': t[3],
                        'height': t[4]
                    })
            # 组装返回结果
            posts.append({
                'id': r[0],
                'poster_id': r[1],
                'date': r[2],
                'text': r[3],
                'medias': medias,
                'like_count': r[5],
                'dislike_count': r[6],
                'reply_count': r[7],
                'name': r[8],
                'avatar': r[9],
                'avatar_thumb': r[10],
                'label': r[11],
                'attitude': r[12],
                'poster_followed': r[13]
            })
    # 查总数
    cursor.execute('SELECT COUNT(id) FROM forum.post')
    rows = cursor.fetchall()
    total_cnt = rows[0][0]
    db.close()
    return response_json(Codes.SUCCESS, {
        'list': posts,
        'total_count': total_cnt,
        'last_data_index': data_idx
    })
