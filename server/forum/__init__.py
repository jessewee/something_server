# -*- coding: utf-8 -*-
import logging
from flask import Blueprint, request, session
from pub import *
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
file_handler = logging.FileHandler(f'{PRIVATE_FILE_DIR}logs/forum.log')
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


# 获取关注人列表，简略信息
@forum.route('/get_followings', methods=['GET'])
def get_followings():
    target_user_id = request.values.get('target_user_id')
    search_content = request.values.get('search_content')
    db = connect_db()
    cursor = db.cursor()
    user_id = session['user_id']
    if is_empty_str(target_user_id):
        target_user_id = user_id
    if target_user_id == user_id:
        sql_part_followed = 'true AS followed'
    else:
        sql_part_followed = f'''
            (
                SELECT COUNT(id) FROM forum.following 
                WHERE to_user_id = f.to_user_id AND from_user_id = {user_id}
            ) > 0 AS followed
            '''
    sql_text = f'''
    SELECT u.id,name,avatar,avatar_thumb,gender,{sql_part_followed}
    FROM forum.following f
    LEFT JOIN public.user u ON f.to_user_id = u.id
    WHERE f.from_user_id = {target_user_id}
    '''
    if is_not_empty_str(search_content):
        sql_text += f''' AND name LIKE '%{search_content}%' '''
    cursor.execute(sql_text)
    rows = cursor.fetchall()
    users = []
    if is_not_empty_collection(rows):
        for r in rows:
            users.append({
                'id': r[0],
                'name': r[1],
                'avatar': r[2],
                'avatar_thumb': r[3],
                'gender': r[4],
                'followed': r[5]
            })
    db.close()
    return response_json(Codes.SUCCESS, users)


# 获取粉丝列表，简略信息
@forum.route('/get_followers', methods=['GET'])
def get_followers():
    target_user_id = request.values.get('target_user_id')
    search_content = request.values.get('search_content')
    data_idx = int(request.values.get('data_idx'))
    data_count = int(request.values.get('data_count'))
    db = connect_db()
    cursor = db.cursor()
    user_id = session['user_id']
    if target_user_id == None:
        target_user_id = user_id
    sql_text = f'''
    SELECT 
        u.id,
        name,
        avatar,
        avatar_thumb,
        gender,
        (
            SELECT COUNT(id) FROM forum.following 
            WHERE to_user_id = f.from_user_id AND from_user_id = {user_id}
        ) > 0 AS followed
    FROM forum.following f
    LEFT JOIN public.user u ON f.from_user_id = u.id
    WHERE f.to_user_id = {target_user_id}
    LIMIT {data_count} OFFSET {data_idx}
    '''
    if is_not_empty_str(search_content):
        sql_text += f''' AND name LIKE '%{search_content}%' '''
    cursor.execute(sql_text)
    rows = cursor.fetchall()
    users = []
    if is_not_empty_collection(rows):
        for r in rows:
            users.append({
                'id': r[0],
                'name': r[1],
                'avatar': r[2],
                'avatar_thumb': r[3],
                'gender': r[4],
                'followed': r[5]
            })
    # 查总数
    cursor.execute(
        f'SELECT COUNT(id) FROM forum.following WHERE to_user_id = {target_user_id}')
    rows = cursor.fetchall()
    total_cnt = rows[0][0]
    db.close()
    return response_json(Codes.SUCCESS, {
        'list': users,
        'total_count': total_cnt,
        'last_data_index': int(data_idx)
    })


# 关注用户
@forum.route('/follow', methods=['PUT'])
def follow():
    user_id = session['user_id']
    target_user_id = request.values.get('user_id')
    follow = request.values.get('follow')
    if is_empty_str(target_user_id) or is_empty_str(follow):
        return response_json(Codes.PARAM_INCORRECT)
    if follow == 'true':
        follow = True
    elif follow == 'false':
        follow = False
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(f'''
        SELECT id 
        FROM forum.following 
        WHERE from_user_id = {user_id} AND to_user_id = {target_user_id}
        ''')
    existed = is_not_empty_collection(cursor.fetchall())
    # 添加关注
    if follow == True and existed != True:
        db.cursor().execute(f'''
            INSERT INTO forum.following(from_user_id,to_user_id)
            VALUES({user_id},{target_user_id})
        ''')
        db.cursor().execute(f'''
            INSERT INTO forum.user_forum_info(user_id,follower_count) VALUES({target_user_id},1)
            ON CONFLICT(user_id) DO UPDATE SET follower_count = forum.user_forum_info.follower_count+1 
            ''')
        db.cursor().execute(f'''
            INSERT INTO forum.user_forum_info(user_id,following_count) VALUES({user_id},1)
            ON CONFLICT(user_id) DO UPDATE SET following_count = forum.user_forum_info.following_count+1 
            ''')
    # 删除关注
    elif existed == True:
        db.cursor().execute(f'''
            DELETE FROM forum.following 
            WHERE from_user_id = {user_id} AND to_user_id = {target_user_id}
            ''')
        db.cursor().execute(f'''
            INSERT INTO forum.user_forum_info(user_id,follower_count) VALUES({target_user_id},1)
            ON CONFLICT(user_id) DO UPDATE SET follower_count = forum.user_forum_info.follower_count-1 
            ''')
        db.cursor().execute(f'''
            INSERT INTO forum.user_forum_info(user_id,following_count) VALUES({user_id},1)
            ON CONFLICT(user_id) DO UPDATE SET following_count = forum.user_forum_info.following_count-1 
            ''')
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS)


# 获取帖子标签列表
@forum.route('/get_post_labels', methods=['GET'])
def get_post_labels():
    search_content = request.values.get('search_content')
    db = connect_db()
    cursor = db.cursor()
    sql_text = 'SELECT id,label,usage FROM forum.post_label'
    if is_not_empty_str(search_content):
        sql_text += f''' WHERE label LIKE '%{search_content}%' '''
    cursor.execute(sql_text)
    rows = cursor.fetchall()
    labels = []
    if is_not_empty_collection(rows):
        for r in rows:
            labels.append({
                'id': r[0],
                'label': r[1],
                'usage': r[2]
            })
    # 增加label使用次数记录
    cursor.execute(f'''
        UPDATE forum.post_label 
        SET usage = usage+1 
        WHERE label = '{search_content}'
        ''')
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS, labels)


# 点赞
@forum.route('/change_like_state', methods=['PUT'])
def change_like_state():
    post_id = request.values.get('post_id')
    floor_id = request.values.get('floor_id')
    inner_floor_id = request.values.get('inner_floor_id')
    if is_all_empty_str(post_id, floor_id, inner_floor_id):
        return response_json(Codes.PARAM_INCORRECT)
    like = request.values.get('like')
    if like == 'true':
        like = True
    elif like == 'false':
        like = False
    user_id = session['user_id']
    db = connect_db()
    cursor = db.cursor()
    attitude_table_name = None
    post_base_id = None
    post_base_table_name = None
    # 帖子点赞
    if is_not_empty_str(post_id):
        attitude_table_name = 'attitude_to_post'
        post_base_id = post_id
        post_base_table_name = 'post'
    # 楼层点赞
    elif is_not_empty_str(floor_id):
        attitude_table_name = 'attitude_to_floor'
        post_base_id = floor_id
        post_base_table_name = 'floor'
    # 层内点赞
    elif is_not_empty_str(inner_floor_id):
        attitude_table_name = 'attitude_to_inner_floor'
        post_base_id = inner_floor_id
        post_base_table_name = 'inner_floor'
    # 统一处理逻辑
    cursor.execute(f'''
        SELECT attitude 
        FROM forum.{attitude_table_name} 
        WHERE user_id = {user_id} AND post_base_id = {post_base_id}
        ''')
    old_attitude = None
    existed_attitude_result = cursor.fetchall()
    if is_not_empty_collection(existed_attitude_result):
        old_attitude = existed_attitude_result[0][0]
    # 状态没变的话不需要操作
    if old_attitude == like:
        return response_json(Codes.SUCCESS)
    # 之前有点赞点踩现在是取消的情况
    if old_attitude != None and like == None:
        # 删除点赞点踩信息
        cursor.execute(f'''
            DELETE FROM forum.{attitude_table_name}
            WHERE user_id = {user_id} AND post_base_id = {post_base_id}
            ''')
        # 更新对应post或floor或inner_floor的点赞点踩计数
        colume_name = 'like_count' if old_attitude == True else 'dislike_count'
        cursor.execute(f'''
            UPDATE forum.{post_base_table_name} 
            SET {colume_name} = {colume_name}-1 
            WHERE id = {post_base_id}
        ''')
    # 之前没有点赞点踩现在是添加的情况
    elif old_attitude == None and like != None:
        # 添加点赞点踩信息
        cursor.execute(f'''
            INSERT INTO forum.{attitude_table_name}(user_id,post_base_id,attitude)
            VALUES({user_id},{post_base_id},{like})
            ''')
        # 更新对应post或floor或inner_floor的点赞点踩计数
        colume_name = 'like_count' if like == True else 'dislike_count'
        cursor.execute(f'''
            UPDATE forum.{post_base_table_name} 
            SET {colume_name} = {colume_name}+1 
            WHERE id = {post_base_id}
        ''')
    # 之前有点赞点踩现在是改变的情况（上边已经判断了新旧态度一样的情况，所以这里else就可以）
    else:
        # 改变点赞点踩信息
        cursor.execute(f'''
            UPDATE forum.{attitude_table_name}
            SET attitude = {like}
            WHERE user_id = {user_id} AND post_base_id = {post_base_id}
            ''')
        # 更新对应post或floor或inner_floor的点赞点踩计数
        lm = '+' if like == True else '-'
        dm = '-' if like == True else '+'
        cursor.execute(f'''
            UPDATE forum.{post_base_table_name} 
            SET like_count = like_count{lm}1 , dislike_count = dislike_count{dm}1
            WHERE id = {post_base_id}
        ''')
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS)


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
               (
                   SELECT attitude FROM forum.attitude_to_post 
                   WHERE post_base_id = p.id AND user_id = {user_id} LIMIT 1
                ) AS attitude,
               (
                   SELECT COUNT(id) FROM forum.following 
                   WHERE to_user_id = p.poster_id AND from_user_id = {user_id}
                ) > 0 AS poster_followed
        '''
    # 排序条件
    sql_part_sort = None
    if sort_by == 2:
        sql_part_sort = 'ORDER BY p.reply_count DESC'
    else:
        sql_part_sort = 'ORDER BY p.date DESC'
    # 筛选条件
    sql_part_condition = ''
    if is_not_empty_str(search_content):
        sql_part_condition += f'''WHERE text LIKE '%{search_content}%' OR name LIKE '%{search_content}%' '''
    if is_not_empty_str(labels):
        tmp = labels.replace(',', '\',\'')
        tmp = f'''label IN ('{tmp}')'''
        if len(sql_part_condition) > 0:
            sql_part_condition += f' AND {tmp}'
        else:
            sql_part_condition += f'WHERE {tmp}'
        # 增加label使用次数记录
        cursor.execute(f'''
            UPDATE forum.post_label 
            SET usage = usage+1 
            WHERE {tmp}
            ''')
        db.commit()
    if is_not_empty_str(users):
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
    if is_not_empty_collection(rows):
        for r in rows:
            # 组装返回结果
            posts.append({
                'id': r[0],
                'poster_id': r[1],
                'date': r[2],
                'text': r[3],
                'medias': map_medias(db, r[4]),
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
        'last_data_index': int(data_idx)
    })


# 获取楼层列表
@forum.route('/get_floors', methods=['GET'])
def get_floors():
    post_id = request.values.get('post_id')
    data_idx = request.values.get('data_idx')
    data_count = request.values.get('data_count')
    floor_start_idx = request.values.get('floor_start_idx')
    floor_end_idx = request.values.get('floor_end_idx')
    sort_by = request.values.get('sort_by')
    user_id = session.get('user_id')
    # 查询数据库
    db = connect_db()
    cursor = db.cursor()
    # 排序条件
    sql_part_sort = None
    if sort_by != None and int(sort_by) == 2:
        sql_part_sort = 'ORDER BY f.reply_count DESC'
    else:
        sql_part_sort = 'ORDER BY f.floor DESC'
    # 筛选条件
    sql_part_condition = f'WHERE f.post_id = {post_id}'
    if is_not_empty_str(floor_start_idx) and is_not_empty_str(floor_end_idx):
        sql_part_condition += f' AND f.floor >= {floor_start_idx} AND f.floor <= {floor_end_idx}'
        # 查下一页索引位置
        cursor.execute(
            f'SELECT COUNT(id) FROM forum.floor WHERE floor <= {floor_end_idx}')
        cnt_data = cursor.fetchall()
        if is_empty_collection(cnt_data):
            data_idx = 0
        else:
            data_idx = len(cnt_data)
    else:
        sql_part_sort += f' LIMIT {data_count} OFFSET {data_idx}'
    # 用户已登录的话要查询登录人对帖子的点赞状态
    sql_part_attitude = None
    if user_id == None:
        sql_part_attitude = 'NULL AS attitude'
    else:
        sql_part_attitude = f'''
               (
                   SELECT attitude FROM forum.attitude_to_floor 
                   WHERE post_base_id = f.id AND user_id = {user_id} LIMIT 1
               ) AS attitude
        '''
    cursor.execute(f'''
        SELECT f.id,
            poster_id,
            date,
            text,
            medias,
            floor,
            like_count,
            dislike_count,
            reply_count,
            name,
            avatar,
            avatar_thumb,
            {sql_part_attitude},
            post_id
        FROM forum.floor f
        LEFT JOIN public.user u ON f.poster_id = u.id
        {sql_part_condition}
        {sql_part_sort}
        ''')
    rows = cursor.fetchall()
    floors = []
    if is_not_empty_collection(rows):
        for r in rows:
            # 组装返回结果
            floors.append({
                'id': r[0],
                'poster_id': r[1],
                'date': r[2],
                'text': r[3],
                'medias': map_medias(db, r[4]),
                'floor': r[5],
                'like_count': r[6],
                'dislike_count': r[7],
                'reply_count': r[8],
                'name': r[9],
                'avatar': r[10],
                'avatar_thumb': r[11],
                'attitude': r[12],
                'post_id': r[13]
            })
    # 查总数
    cursor.execute(f'SELECT COUNT(id) FROM forum.floor WHERE post_id = {post_id}')
    rows = cursor.fetchall()
    total_cnt = rows[0][0]
    # 结果
    db.close()
    return response_json(Codes.SUCCESS, {
        'list': floors,
        'total_count': total_cnt,
        'last_data_index': int(data_idx) if type(data_idx) == str else data_idx
    })


# 获取层内回复列表
@forum.route('/get_inner_floors', methods=['GET'])
def get_inner_floors():
    floor_id = request.values.get('floor_id')
    data_idx = request.values.get('data_idx')
    data_count = request.values.get('data_count')
    user_id = session.get('user_id')
    # 查询数据库
    db = connect_db()
    cursor = db.cursor()
    # 用户已登录的话要查询登录人对帖子的点赞状态
    sql_part_attitude = None
    if user_id == None:
        sql_part_attitude = 'NULL AS attitude'
    else:
        sql_part_attitude = f'''
               (
                   SELECT attitude FROM forum.attitude_to_inner_floor 
                   WHERE post_base_id = i.id AND user_id = {user_id} LIMIT 1
                ) AS attitude
        '''
    cursor.execute(f'''
        SELECT i.id,
            poster_id,
            date,
            text,
            medias,
            inner_floor,
            target_id,
            tu.name AS target_name,
            like_count,
            dislike_count,
            u.name,
            u.avatar,
            u.avatar_thumb,
            {sql_part_attitude},
            post_id,
            floor_id
        FROM forum.inner_floor i
        LEFT JOIN public.user u ON i.poster_id = u.id
        LEFT JOIN public.user tu ON i.target_id = tu.id
        WHERE i.floor_id = {floor_id} 
        ORDER BY i.inner_floor DESC
        LIMIT {data_count} OFFSET {data_idx}
        ''')
    rows = cursor.fetchall()
    inner_floors = []
    if is_not_empty_collection(rows):
        for r in rows:
            # 组装返回结果
            inner_floors.append({
                'id': r[0],
                'poster_id': r[1],
                'date': r[2],
                'text': r[3],
                'medias': map_medias(db, r[4]),
                'inner_floor': r[5],
                'target_id': r[6],
                'target_name': r[7],
                'like_count': r[8],
                'dislike_count': r[9],
                'name': r[10],
                'avatar': r[11],
                'avatar_thumb': r[12],
                'attitude': r[13],
                'post_id': r[14],
                'floor_id': r[15]
            })
    # 查总数
    cursor.execute(f'SELECT COUNT(id) FROM forum.inner_floor WHERE floor_id = {floor_id}')
    rows = cursor.fetchall()
    total_cnt = rows[0][0]
    # 结果
    db.close()
    return response_json(Codes.SUCCESS, {
        'list': inner_floors,
        'total_count': total_cnt,
        'last_data_index': int(data_idx)
    })


# post、floor、inner_floor中查出来的medias是files表里的id的列表，这个转换成对应数据
def map_medias(db, src):
    if is_empty_collection(src):
        return []
    medias = []
    cursor = db.cursor()
    cursor.execute(f'''
        SELECT type,url,thumb_url,width,height 
        FROM public.files 
        WHERE id IN ({','.join('%s' %id for id in src)})
        ''')
    rows = cursor.fetchall()
    if is_not_empty_collection(rows):
        for r in rows:
            medias.append({
                'type': r[0],
                'url': r[1],
                'thumb_url': r[2],
                'width': r[3],
                'height': r[4]
            })
    return medias


# 回复post、floor、inner_floor
@forum.route('/reply', methods=['POST'])
def reply():
    post_id = request.values.get('post_id')
    floor_id = request.values.get('floor_id')
    inner_floor_id = request.values.get('inner_floor_id')
    if is_all_empty_str(post_id, floor_id, inner_floor_id):
        return response_json(Codes.PARAM_INCORRECT)
    # 回复层主时post_id也必须有
    if is_not_empty_str(floor_id) and is_empty_str(post_id):
        return response_json(Codes.PARAM_INCORRECT)
    # 层内回复时post_id和floor_id也必须有
    if is_not_empty_str(inner_floor_id) and is_all_empty_str(post_id, floor_id):
        return response_json(Codes.PARAM_INCORRECT)
    user_id = session.get('user_id')
    text = request.values.get('text')
    medias_tmp = request.values.getlist('medias[]')
    if is_empty_str(text) and is_empty_collection(medias_tmp):
        return response_json(Codes.PARAM_INCORRECT)
    medias = None
    if is_not_empty_collection(medias_tmp):
        medias = 'array[' + ','.join(medias_tmp) + ']'
    resp_data = {}
    db = connect_db()
    cursor = db.cursor()
    # 层内回复
    if is_not_empty_str(inner_floor_id):
        # 查找对应的floor_id,target_id
        cursor.execute(
            f'SELECT floor_id,poster_id FROM forum.inner_floor WHERE id = {inner_floor_id}')
        tmp = cursor.fetchall()
        floor_id = tmp[0][0]
        target_id = tmp[0][1]
        # 添加数据
        cursor.execute(f'''
            WITH max_inner_floor AS (
                SELECT max(inner_floor) 
                FROM forum.inner_floor 
                WHERE floor_id = {floor_id}
            )
            INSERT INTO forum.inner_floor(
                poster_id,
                text,
                {'' if medias == None else 'medias,'}
                inner_floor,
                target_id,
                post_id,
                floor_id
            )
            VALUES(
                {user_id},
                '{text}',
                {'' if medias == None else medias + ','}
                (SELECT (CASE WHEN max IS NULL THEN 1 ELSE max+1 END) FROM max_inner_floor),
                {target_id},
                {post_id},
                {floor_id}
            )
            RETURNING id,inner_floor
            ''')
        id_inner_floor = cursor.fetchone()
        resp_data['inner_floor_id'] = id_inner_floor[0]
        resp_data['inner_floor'] = id_inner_floor[1]
        # 楼层信息里增加回复的计数
        db.cursor().execute(f'''
            UPDATE forum.floor 
            SET reply_count = reply_count+1 
            WHERE id = {floor_id}
            ''')
        # 帖子信息里增加回复的计数
        db.cursor().execute(f'''
            UPDATE forum.post 
            SET reply_count = reply_count+1 
            WHERE id = {post_id}
            ''')
    # 回复楼层
    if is_not_empty_str(floor_id):
        cursor.execute(f'''
            WITH max_inner_floor AS (SELECT max(inner_floor) FROM forum.inner_floor WHERE floor_id = {floor_id})
            INSERT INTO forum.inner_floor(
                poster_id,
                text,
                {'' if medias == None else 'medias,'}
                inner_floor,
                post_id,
                floor_id
            )
            VALUES(
                {user_id},
                '{text}',
                {'' if medias == None else medias + ','}
                (SELECT (CASE WHEN max IS NULL THEN 1 ELSE max+1 END) FROM max_inner_floor),
                {post_id},
                {floor_id}
            )
            RETURNING id,inner_floor
            ''')
        id_inner_floor = cursor.fetchone()
        resp_data['inner_floor_id'] = id_inner_floor[0]
        resp_data['inner_floor'] = id_inner_floor[1]
        # 楼层信息里增加回复的计数
        db.cursor().execute(f'''
            UPDATE forum.floor 
            SET reply_count = reply_count+1 
            WHERE id = {floor_id}
            ''')
        # 帖子信息里增加回复的计数
        db.cursor().execute(f'''
            UPDATE forum.post 
            SET reply_count = reply_count+1 
            WHERE id = {post_id}
            ''')
    # 回复帖子
    else:
        cursor.execute(f'''
            WITH max_floor AS (SELECT max(floor) FROM forum.floor WHERE post_id = {post_id})
            INSERT INTO forum.floor(
                poster_id,
                text,
                {'' if medias == None else 'medias,'}
                floor,
                post_id
            )
            VALUES(
                {user_id},
                '{text}',
                {'' if medias == None else medias + ','}
                (SELECT (CASE WHEN max IS NULL THEN 1 ELSE max+1 END) FROM max_floor),
                {post_id}
            )
            RETURNING id,floor
            ''')
        id_floor = cursor.fetchone()
        resp_data['floor_id'] = id_floor[0]
        resp_data['floor'] = id_floor[1]
        # 帖子信息里增加回复的计数
        db.cursor().execute(f'''
            UPDATE forum.post 
            SET reply_count = reply_count+1 
            WHERE id = {post_id}
            ''')
    # 添加回复计数
    db.cursor().execute(f'''
        INSERT INTO forum.user_forum_info(user_id,reply_count) VALUES({user_id},1)
        ON CONFLICT(user_id) DO UPDATE SET reply_count = forum.user_forum_info.reply_count+1 
        ''')
    # 结果
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS, resp_data)


# 发帖
@forum.route('/post', methods=['POST'])
def post():
    user_id = session.get('user_id')
    label = request.values.get('label')
    text = request.values.get('text')
    medias_tmp = request.values.getlist('medias[]')
    if is_empty_str(label):
        return response_json(Codes.PARAM_INCORRECT)
    if is_empty_str(text) and is_empty_collection(medias_tmp):
        return response_json(Codes.PARAM_INCORRECT)
    medias = None
    if is_not_empty_collection(medias_tmp):
        medias = 'array[' + ','.join(medias_tmp) + ']'
    resp_data = {}
    db = connect_db()
    cursor = db.cursor()
    # 先查看label
    label_id = None
    if is_not_empty_str(label):
        cursor.execute(
            f'''SELECT id FROM forum.post_label WHERE label = '{label}' LIMIT 1''')
        tmp = cursor.fetchall()
        if is_not_empty_collection(tmp):
            label_id = tmp[0][0]
            cursor.execute(
                f'''UPDATE forum.post_label SET usage = usage+1 WHERE id = {label_id}''')
        else:
            cursor.execute(f'''
            INSERT INTO forum.post_label(label) VALUES('{label}')
            RETURNING id
            ''')
            label_id = cursor.fetchone()[0]
    # 添加post数据
    cursor.execute(f'''
        INSERT INTO forum.post(
            poster_id,
            text,
            {'' if medias == None else 'medias,'}
            label_id
        )
        VALUES(
            {user_id},
            '{text}',
            {'' if medias == None else medias + ','}
            {label_id}
        )
        RETURNING id
        ''')
    resp_data = cursor.fetchone()[0]
    # 添加发帖计数
    db.cursor().execute(f'''
        INSERT INTO forum.user_forum_info(user_id,post_count) VALUES({user_id},1)
        ON CONFLICT(user_id) DO UPDATE SET post_count = forum.user_forum_info.post_count+1 
        ''')
    # 结果
    db.commit()
    db.close()
    return response_json(Codes.SUCCESS, resp_data)


# 获取用户信息
@forum.route('/get_user_info', methods=['GET'])
def get_user_info():
    target_user_id = request.values.get('user_id')
    target_user_name = request.values.get('user_name')
    if is_all_empty_str(target_user_id, target_user_name):
        return response_json(Codes.PARAM_INCORRECT)
    user_id = session.get('user_id')
    sql_part_followed = None
    if user_id == None:
        sql_part_followed = 'false AS followed'
    else:
        sql_part_followed = f'''
            (
                SELECT COUNT(id) FROM forum.following 
                WHERE to_user_id = u.id AND from_user_id = {user_id}
            ) > 0 AS followed
            '''
    sql_part_condition = None
    if is_not_empty_str(target_user_id):
        sql_part_condition = f'WHERE id = {target_user_id}'
    else:
        sql_part_condition = f'''WHERE name = '{target_user_name}' '''
    db = connect_db()
    cursor = db.cursor()
    sql = f'''
        SELECT 
            id,
            name,
            avatar,
            avatar_thumb,
            gender,
            birthday,
            register_date,
            email,
            remark,
            follower_count,
            following_count,
            {sql_part_followed},
            post_count,
            reply_count
        FROM public.user u
        LEFT JOIN forum.user_forum_info f ON f.user_id = u.id
        {sql_part_condition}
        '''
    cursor.execute(sql)
    rows = cursor.fetchall()
    if is_empty_collection(rows):
        db.close()
        return response_json(Codes.USER_NOT_EXIST)
    result = {
        'id': rows[0][0],
        'name': rows[0][1],
        'avatar': rows[0][2],
        'avatar_thumb': rows[0][3],
        'gender': rows[0][4],
        'birthday': rows[0][5],
        'register_date': rows[0][6],
        'email': rows[0][7],
        'remark': rows[0][8],
        'follower_count': rows[0][9],
        'following_count': rows[0][10],
        'followed': rows[0][11],
        'post_count': rows[0][12],
        'reply_count': rows[0][13]
    }
    db.close()
    return response_json(Codes.SUCCESS, result)
