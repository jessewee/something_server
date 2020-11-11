# -*- coding: utf-8 -*-
from enum import IntEnum, unique

# 返回给客户端的状态码对应的消息文本
code_messages = {
    # 失败
    -1: '操作失败',
    # 成功
    0: '操作成功',
    # refreshToken失效
    100: 'token失效，请重新登录',
    # token失效
    101: 'token失效，请重新登录',
    # 参数错误
    110: '参数错误',
    # 没有收到文件数据
    111: '没有收到文件数据',
    # 账号不能为空
    10010: '账号不能为空',
    # 账号不存在
    10011: '账号不存在',
    # 账号已存在
    10012: '账号已存在',
    # 密码不能为空
    10013: '密码不能为空',
    # 密码不正确
    10014: '密码不正确',
    # 邮箱不能为空
    10015: '邮箱不能为空',
    # 验证码不能为空
    10016: '验证码不能为空',
    # 验证码不正确
    10017: '验证码不正确'
}


# 返回给客户端的状态码
@unique
class Codes(IntEnum):
    # 失败
    FAIL = -1
    # 成功
    SUCCESS = 0
    # token失效
    TOKEN_INVALID = 101
    # refresh_token失效
    REFRESH_TOKEN_INVALID = 100
    # 参数错误
    PARAM_INCORRECT = 110
    # 没有收到文件数据
    NO_FILE_RECEIVED = 111
    # 账号不能为空
    ACCOUNT_EMPTY = 10010
    # 账号不存在
    ACCOUNT_NOT_EXIST = 10011
    # 账号已存在
    ACCOUNT_EXIST = 10012
    # 密码不能为空
    PWD_EMPTY = 10013
    # 密码不正确
    PWD_INCORRECT = 10014
    # 邮箱不能为空
    EMAIL_EMPTY = 10015
    # 验证码不能为空
    VF_CODE_EMPTY = 10016
    # 验证码不正确
    VF_CODE_INCORRECT = 10017

    def msg(self):
        msg = code_messages.get(self.value)
        if msg == None:
            msg = '未知错误'
        return msg
