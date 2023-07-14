# -*- coding: UTF-8 -*-
import concurrent.futures
import math
import os
import re
import string
import typing
import random
import jvav
import asyncio
import threading
import langdetect
import lxml  # for bs4
import telebot
from pyrogram import Client
from telebot import apihelper, types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from logger import Logger
from config import BotConfig
from database import BotFileDb, BotCacheDb
from flask import Flask, request
from jvav import TransUtil

# Initialize Flask app
app = Flask(__name__)

# TG 地址
BASE_URL_TG = "https://t.me"
# MissAv 地址
BASE_URL_MISS_AV = "https://missav.com"
# 项目地址
PROJECT_ADDRESS = "https://github.com/akynazh/tg-jav-bot"
# 默认使用官方机器人: https://t.me/PikPak6_Bot
PIKPAK_BOT_NAME = "PikPak6_Bot"
# 联系作者
CONTACT_AUTHOR = f"{BASE_URL_TG}/jackbryant286"
# 文件存储目录位置
PATH_ROOT = f'{os.path.expanduser("~")}/.tg_jav_bot'
# 日志文件位置
PATH_LOG_FILE = f"{PATH_ROOT}/log.txt"
# 记录文件位置
PATH_RECORD_FILE = f"{PATH_ROOT}/record.json"
# my_account.session 文件位置
PATH_SESSION_FILE = f"{PATH_ROOT}/my_account"
# 配置文件位置
PATH_CONFIG_FILE = f"config.yaml"
# 正则匹配 AV
AV_PAT = re.compile(r"[a-z0-9]+[-_](?:ppv-)?[a-z0-9]+")
# 帮助消息
MSG_HELP = f"""Hey, I am an Powerful AV Resource Bot!


/help - Need any help!
/stars - View favorite actors.
/avs - View favorite product codes.
/nice - Get a random highly rated product.
/new - Get a random latest product.
/rank - Get the DMM actress ranking.
/record - Get the favorite records file.
/star [actor name]
/av [product code]

⚠️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ Jᴀᴠ Bʟᴀsᴛᴇʀ
"""
BOT_CMDS = {
    "help": "View command help",
    "stars": "View favorite actors",
    "avs": "View favorite AV codes",
    "nice": "Get a random high-rated AV",
    "new": "Get a random latest AV",
    "rank": "Get DMM actress ranking",
    "record": "Get favorite records file",
    "star": "Followed by actor's name to search for the actor",
    "av": "Followed by AV code to search for the AV",
}


if not os.path.exists(PATH_ROOT):
    os.makedirs(PATH_ROOT)
LOG = Logger(path_log_file=PATH_LOG_FILE).logger
BOT_CFG = BotConfig(PATH_CONFIG_FILE)
apihelper.proxy = BOT_CFG.proxy_json
BOT = telebot.TeleBot(BOT_CFG.tg_bot_token)
BOT_DB = BotFileDb(PATH_RECORD_FILE)
BOT_CACHE_DB = BotCacheDb(
    host=BOT_CFG.redis_host, port=BOT_CFG.redis_port, use_cache=BOT_CFG.use_cache
)
BASE_UTIL = jvav.BaseUtil(BOT_CFG.proxy_addr)
DMM_UTIL = jvav.DmmUtil(BOT_CFG.proxy_addr_dmm)
JAVBUS_UTIL = jvav.JavBusUtil(BOT_CFG.proxy_addr)
JAVLIB_UTIL = jvav.JavLibUtil(BOT_CFG.proxy_addr)
SUKEBEI_UTIL = jvav.SukebeiUtil(BOT_CFG.proxy_addr)
TRANS_UTIL = jvav.TransUtil(BOT_CFG.proxy_addr)
WIKI_UTIL = jvav.WikiUtil(BOT_CFG.proxy_addr)
AVGLE_UTIL = jvav.AvgleUtil(BOT_CFG.proxy_addr)


class BotKey:
    """回调按键值"""

    KEY_GET_SAMPLE_BY_ID = "k0_0"
    KEY_GET_MORE_MAGNETS_BY_ID = "k0_1"
    KEY_SEARCH_STAR_BY_NAME = "k0_2"
    KEY_GET_TOP_STARS = "k0_3"
    KEY_WATCH_PV_BY_ID = "k1_0"
    KEY_WATCH_FV_BY_ID = "k1_1"
    KEY_GET_AV_BY_ID = "k2_0"
    KEY_RANDOM_GET_AV_BY_STAR_ID = "k2_1"
    KEY_RANDOM_GET_AV_NICE = "k2_2"
    KEY_RANDOM_GET_AV_NEW = "k2_3"
    KEY_GET_NEW_AVS_BY_STAR_NAME_ID = "k2_4"
    KEY_GET_NICE_AVS_BY_STAR_NAME = "k2_5"
    KEY_RECORD_STAR_BY_STAR_NAME_ID = "k3_0"
    KEY_RECORD_AV_BY_ID_STAR_IDS = "k3_1"
    KEY_GET_STARS_RECORD = "k3_2"
    KEY_GET_AVS_RECORD = "k3_3"
    KEY_GET_STAR_DETAIL_RECORD_BY_STAR_NAME_ID = "k3_4"
    KEY_GET_AV_DETAIL_RECORD_BY_ID = "k3_5"
    KEY_UNDO_RECORD_STAR_BY_STAR_NAME_ID = "k3_6"
    KEY_UNDO_RECORD_AV_BY_ID = "k3_7"
    KEY_DEL_AV_CACHE = "k4_1"


class BotUtils:
    """机器人工具"""

    def __init__(self):
        pass

    def send_action_typing(self):
        """显示机器人正在处理消息"""
        BOT.send_chat_action(chat_id=BOT_CFG.tg_chat_id, action="typing")

    def send_msg(self, msg: str, pv=False, markup=None):
        """发送消息

        :param str msg: 消息文本内容
        :param bool pv: 是否展现预览, 默认不展示
        :param InlineKeyboardMarkup markup: 标记, 默认没有
        """
        BOT.send_message(
            chat_id=BOT_CFG.tg_chat_id,
            text=msg,
            disable_web_page_preview=not pv,
            parse_mode="HTML",
            reply_markup=markup,
        )

    def send_msg_code_op(self, code: int, op: str):
        """根据状态码和操作描述发送消息

        :param int code: 状态码
        :param str op: 执行的操作描述
        """
        if code == 200:
            self.send_msg(
                f"""执行操作: {op}
执行结果: 成功 ^_^"""
            )
        elif code == 404:
            self.send_msg(
                f"""执行操作: {op}
执行结果: 未查找到结果 Q_Q"""
            )
        elif code == 500:
            self.send_msg(
                f"""执行操作: {op}
执行结果: 服务器出错, 请重试或检查日志 Q_Q"""
            )
        elif code == 502:
            self.send_msg(
                f"""执行操作: {op}
执行结果: 网络请求失败, 请重试或检查网络 Q_Q"""
            )

    def send_msg_success_op(self, op: str):
        """根据操作描述发送执行成功的消息

        :param str op: 执行的操作描述
        """
        self.send_msg(
            f"""执行操作: {op}
执行结果: 成功 ^_^"""
        )

    def send_msg_fail_reason_op(self, reason: str, op: str):
        """根据失败原因和操作描述发送执行失败的消息

        :param str reason: 失败原因
        :param str op: 执行的操作描述
        """
        self.send_msg(
            f"""执行操作: {op}
执行结果: 失败, {reason} Q_Q"""
        )

    def check_success(self, code: int, op: str) -> bool:
        """检查状态码, 确认请求是否成功

        :param int code: 状态码
        :param str op: 执行的操作描述
        :return bool: 请求成功与否
        """
        if code == 200:
            return True
        if code == 404:
            self.send_msg_code_op(code=404, op=op)
        elif code == 500:
            self.send_msg_code_op(code=500, op=op)
        elif code == 502:
            self.send_msg_code_op(code=502, op=op)
        return False

    def create_btn_by_key(self, key_type: str, obj) -> InlineKeyboardButton:
        """根据按钮种类创建按钮

        :param str key_type: 按钮种类
        :param any obj: 数据对象
        :return InlineKeyboardButton: 按钮对象
        """
        if key_type == BotKey.KEY_GET_STAR_DETAIL_RECORD_BY_STAR_NAME_ID:
            return InlineKeyboardButton(
                text=obj["name"], callback_data=f'{obj["name"]}|{obj["id"]}:{key_type}'
            )
        elif key_type == BotKey.KEY_GET_AV_DETAIL_RECORD_BY_ID:
            return InlineKeyboardButton(text=obj, callback_data=f"{obj}:{key_type}")
        elif key_type == BotKey.KEY_SEARCH_STAR_BY_NAME:
            return InlineKeyboardButton(text=obj, callback_data=f"{obj}:{key_type}")
        elif key_type == BotKey.KEY_GET_AV_BY_ID:
            return InlineKeyboardButton(
                text=f'{obj["id"]} | {obj["rate"]}',
                callback_data=f'{obj["id"]}:{key_type}',
            )

    def send_msg_btns(
        self,
        max_btn_per_row: int,
        max_row_per_msg: int,
        key_type: str,
        title: str,
        objs: list,
        extra_btns=[],
        page_btns=[],
    ):
        """发送按钮消息

        :param int max_btn_per_row: 每行最大按钮数量
        :param int max_row_per_msg: 每条消息最多行数
        :param str key_type: 按钮种类
        :param str title: 消息标题
        :param list objs: 数据对象数组
        :param list extra_btns: 附加按钮列表, 二维数组, 对应于实际的按钮排布, 附加在每条消息尾部, 默认为空
        :param list page_btns: 分页块
        """
        # 初始化数据
        markup = InlineKeyboardMarkup()
        row_count = 0
        btns = []
        # 开始生成按钮和发送消息
        for obj in objs:
            btns.append(self.create_btn_by_key(key_type, obj))
            # 若一行按钮的数量达到 max_btn_per_row, 则加入行
            if len(btns) == max_btn_per_row:
                markup.row(*btns)
                row_count += 1
                btns = []
            # 若消息中行数达到 max_row_per_msg, 则发送消息
            if row_count == max_row_per_msg:
                for extra_btn in extra_btns:
                    markup.row(*extra_btn)
                if page_btns != []:
                    markup.row(*page_btns)
                self.send_msg(msg=title, markup=markup)
                row_count = 0
                markup = InlineKeyboardMarkup()
        # 若当前行按钮数量不为 0, 则加入行
        if btns != []:
            markup.row(*btns)
            row_count += 1
        # 若当前行数不为 0, 则发送消息
        if row_count != 0:
            for extra_btn in extra_btns:
                markup.row(*extra_btn)
            if page_btns != []:
                markup.row(*page_btns)
            self.send_msg(msg=title, markup=markup)

    def get_page_elements(
        self, objs: list, page: int, col: int, row: int, key_type: str
    ) -> typing.Tuple[list, list, str]:
        """获取当前页对象列表, 分页按钮列表, 数量标题

        :param list objs: 所有对象
        :param int page: 当前页
        :param int col: 当前页列数
        :param int row: 当前页行数
        :param str key_type: 按键类型
        :return tuple[list, list, str]: 当前页对象列表, 分页按钮列表, 数量标题
        """
        # 记录总数
        record_count_total = len(objs)
        # 每页记录数
        record_count_per_page = col * row
        # 页数
        if record_count_per_page > record_count_total:
            page_count = 1
        else:
            page_count = math.ceil(record_count_total / record_count_per_page)
        # 如果要获取的页大于总页数, 那么获取的页设为最后一页
        if page > page_count:
            page = page_count
        # 获取当前页对象字典
        start_idx = (page - 1) * record_count_per_page
        objs = objs[start_idx : start_idx + record_count_per_page]
        # 获取按键列表
        if page == 1:
            to_previous = 1
        else:
            to_previous = page - 1
        if page == page_count:
            to_next = page_count
        else:
            to_next = page + 1
        btn_to_first = InlineKeyboardButton(text="<<", callback_data=f"1:{key_type}")
        btn_to_previous = InlineKeyboardButton(
            text="<", callback_data=f"{to_previous}:{key_type}"
        )
        btn_to_current = InlineKeyboardButton(
            text=f"-{page}-", callback_data=f"{page}:{key_type}"
        )
        btn_to_next = InlineKeyboardButton(
            text=">", callback_data=f"{to_next}:{key_type}"
        )
        btn_to_last = InlineKeyboardButton(
            text=">>", callback_data=f"{page_count}:{key_type}"
        )
        # 获取数量标题
        title = f"Total: <b>{record_count_total} Pages</b>, on Page: <b>{page_count}</b>"
        return (
            objs,
            [btn_to_first, btn_to_previous, btn_to_current, btn_to_next, btn_to_last],
            title,
        )

    def get_stars_record(self, page=1):
        """获取演员收藏记录

        :param int page: 第几页, 默认第一页
        """
        # 初始化数据
        record, is_star_exists, _ = BOT_DB.check_has_record()
        if not record or not is_star_exists:
            self.send_msg_fail_reason_op(reason="尚无演员收藏记录", op="获取演员收藏记录")
            return
        stars = record["stars"]
        stars.reverse()
        col, row = 4, 5
        objs, page_btns, title = self.get_page_elements(
            objs=stars,
            page=page,
            col=col,
            row=row,
            key_type=BotKey.KEY_GET_STARS_RECORD,
        )
        # 发送按钮消息
        self.send_msg_btns(
            max_btn_per_row=col,
            max_row_per_msg=row,
            key_type=BotKey.KEY_GET_STAR_DETAIL_RECORD_BY_STAR_NAME_ID,
            title="<b>收藏的演员: </b>" + title,
            objs=objs,
            page_btns=page_btns,
        )

    def get_star_detail_record_by_name_id(self, star_name: str, star_id: str):
        """根据演员名称和编号获取该演员更多信息

        :param str star_name: 演员名称
        :param str star_id: 演员编号
        """
        # 初始化数据
        record, is_stars_exists, is_avs_exists = BOT_DB.check_has_record()
        if not record:
            self.send_msg(reason="尚无该演员收藏记录", op=f"获取演员 <code>{star_name}</code> 的更多信息")
            return
        avs = []
        star_avs = []
        cur_star_exists = False
        if is_avs_exists:
            avs = record["avs"]
            avs.reverse()
            for av in avs:
                # 如果演员编号在该 av 的演员编号列表中
                if star_id in av["stars"]:
                    star_avs.append(av["id"])
        if is_stars_exists:
            stars = record["stars"]
            for star in stars:
                if star["id"].lower() == star_id.lower():
                    cur_star_exists = True
        # 发送按钮消息
        extra_btn1 = InlineKeyboardButton(
            text=f"Random AV",
            callback_data=f"{star_name}|{star_id}:{BotKey.KEY_RANDOM_GET_AV_BY_STAR_ID}",
        )
        extra_btn2 = InlineKeyboardButton(
            text=f"Latest AV",
            callback_data=f"{star_name}|{star_id}:{BotKey.KEY_GET_NEW_AVS_BY_STAR_NAME_ID}",
        )
        extra_btn3 = InlineKeyboardButton(
            text=f"High Rated AV",
            callback_data=f"{star_name}:{BotKey.KEY_GET_NICE_AVS_BY_STAR_NAME}",
        )
        if cur_star_exists:
            extra_btn4 = InlineKeyboardButton(
                text=f"Cancel Record",
                callback_data=f"{star_name}|{star_id}:{BotKey.KEY_UNDO_RECORD_STAR_BY_STAR_NAME_ID}",
            )
        else:
            extra_btn4 = InlineKeyboardButton(
                text=f"Record Actor by ID",
                callback_data=f"{star_name}|{star_id}:{BotKey.KEY_RECORD_STAR_BY_STAR_NAME_ID}",
            )
        title = f'<code>{star_name}</code> | <a href="{WIKI_UTIL.BASE_URL_JAPAN_WIKI}/{star_name}">Wiki</a> | <a href="{JAVBUS_UTIL.BASE_URL_SEARCH_BY_STAR_ID}/{star_id}">Javbus</a>'
        if len(star_avs) == 0:  # 没有该演员对应 av 收藏记录
            markup = InlineKeyboardMarkup()
            markup.row(extra_btn1, extra_btn2, extra_btn3, extra_btn4)
            self.send_msg(msg=title, markup=markup)
            return
        self.send_msg_btns(
            max_btn_per_row=4,
            max_row_per_msg=10,
            key_type=BotKey.KEY_GET_AV_DETAIL_RECORD_BY_ID,
            title=title,
            objs=star_avs,
            extra_btns=[[extra_btn1, extra_btn2, extra_btn3, extra_btn4]],
        )

    def get_avs_record(self, page=1):
        """获取番号收藏记录

        :param int page: 第几页, 默认第一页
        """
        # 初始化数据
        record, _, is_avs_exists = BOT_DB.check_has_record()
        if not record or not is_avs_exists:
            self.send_msg_fail_reason_op(reason="尚无番号收藏记录", op="获取番号收藏记录")
            return
        avs = [av["id"] for av in record["avs"]]
        avs.reverse()
        # 发送按钮消息
        extra_btn1 = InlineKeyboardButton(
            text="Random High Rating AV", callback_data=f"0:{BotKey.KEY_RANDOM_GET_AV_NICE}"
        )
        extra_btn2 = InlineKeyboardButton(
            text="Random Latest AV", callback_data=f"0:{BotKey.KEY_RANDOM_GET_AV_NEW}"
        )
        col, row = 4, 10
        objs, page_btns, title = self.get_page_elements(
            objs=avs, page=page, col=col, row=row, key_type=BotKey.KEY_GET_AVS_RECORD
        )
        self.send_msg_btns(
            max_btn_per_row=col,
            max_row_per_msg=row,
            key_type=BotKey.KEY_GET_AV_DETAIL_RECORD_BY_ID,
            title="<b>Record ID: </b>" + title,
            objs=objs,
            extra_btns=[[extra_btn1, extra_btn2]],
            page_btns=page_btns,
        )

    def get_av_detail_record_by_id(self, id: str):
        """根据番号获取该番号更多信息

        :param str id: 番号
        """
        record, _, is_avs_exists = BOT_DB.check_has_record()
        avs = record["avs"]
        cur_av_exists = False
        for av in avs:
            if id.lower() == av["id"].lower():
                cur_av_exists = True
        markup = InlineKeyboardMarkup()
        btn = InlineKeyboardButton(
            text=f"Related AV", callback_data=f"{id}:{BotKey.KEY_GET_AV_BY_ID}"
        )
        if cur_av_exists:
            markup.row(
                btn,
                InlineKeyboardButton(
                    text=f"Cancel Record",
                    callback_data=f"{id}:{BotKey.KEY_UNDO_RECORD_AV_BY_ID}",
                ),
            )
        else:
            markup.row(btn)
        self.send_msg(msg=f"<code>{id}</code>", markup=markup)

    def get_av_by_id(
        self,
        id: str,
        send_to_pikpak=False,
        is_nice=True,
        is_uncensored=True,
        magnet_max_count=3,
        not_send=False,
    ) -> dict:
        """根据番号获取 av

        :param str id: 番号
        :param bool send_to_pikpak: 是否发给 pikpak, 默认不发送
        :param bool is_nice: 是否过滤出高清, 有字幕磁链, 默认是
        :param bool is_uncensored: 是否过滤出无码磁链, 默认是
        :param int magnet_max_count: 过滤后磁链的最大数目, 默认为 3
        :param not_send: 是否不发送 av 结果, 默认发送
        :return dict: 当不发送 av 结果时, 返回得到的 av(如果有)
        """
        # 获取 av
        op_get_av_by_id = f"Search ID <code>{id}</code>"
        av = BOT_CACHE_DB.get_cache(key=id, type=BotCacheDb.TYPE_AV)
        av_score = None
        is_cache = False
        futures = {}
        if not av or not_send:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                if not not_send:
                    futures[
                        executor.submit(DMM_UTIL.get_score_by_id, id)
                    ] = 0  # 获取 av 评分
                futures[
                    executor.submit(
                        JAVBUS_UTIL.get_av_by_id,
                        id,
                        is_nice,
                        is_uncensored,
                        magnet_max_count,
                    )
                ] = 1  # 通过 javbus 获取 av
                futures[
                    executor.submit(
                        SUKEBEI_UTIL.get_av_by_id,
                        id,
                        is_nice,
                        is_uncensored,
                        magnet_max_count,
                    )
                ] = 2  # 通过 sukebei 获取 av
                for future in concurrent.futures.as_completed(futures):
                    future_type = futures[future]
                    if future_type == 0:
                        _, av_score = future.result()
                    elif future_type == 1:
                        code_javbus, av_javbus = future.result()
                    elif future_type == 2:
                        code_sukebei, av_sukebei = future.result()
            if code_javbus != 200 and code_sukebei != 200:
                if code_javbus == 502 or code_sukebei == 502:
                    self.send_msg_code_op(502, op_get_av_by_id)
                else:
                    self.send_msg_code_op(404, op_get_av_by_id)
                return
            if code_javbus == 200:  # 优先选择 javbus
                av = av_javbus
            elif code_sukebei == 200:
                av = av_sukebei
            av["score"] = av_score
            if not not_send:
                if len(av["magnets"]) == 0:
                    BOT_CACHE_DB.set_cache(
                        key=id, value=av, type=BotCacheDb.TYPE_AV, expire=3600 * 24 * 1
                    )
                else:
                    BOT_CACHE_DB.set_cache(key=id, value=av, type=BotCacheDb.TYPE_AV)
        else:
            av_score = av["score"]
            is_cache = True
        if not_send:
            return av
        # 提取数据
        av_id = id.upper()
        av_title = av["title"]
        av_img = av["img"]
        av_date = av["date"]
        av_tag = av["tags"]
        trans_util = TransUtil()
        av_tags = trans_util.trans(text=av_tag, from_lang="ja", to_lang="en")
        av_stars = av["stars"]
        av_magnets = av["magnets"]
        av_url = av["url"]
        # 拼接消息
        msg = ""
        # 标题
        if av_title != "":
            av_title_ch = TRANS_UTIL.trans(
                text=av_title, from_lang="ja", to_lang="en"
            )
            if av_title_ch:
                av_title = av_title_ch
            av_title = av_title.replace("<", "").replace(">", "")
            msg += f"""<code>{av_id}</code> | {av_title}
"""
        # 番号
        msg += f"""𝗣𝗿𝗼𝗱𝘂𝗰𝘁 𝗜𝗗: <code>{av_id}</code>
"""
        # 日期
        if av_date != "":
            msg += f"""𝗥𝗲𝗹𝗲𝗮𝘀𝗲 𝗗𝗮𝘁𝗲: <code>{av_date}</code>
"""
        # 评分
        if av_score:
            msg += f"""𝗥𝗮𝘁𝗶𝗻𝗴𝘀: <code>{av_score}/5</code>
"""
        # 演员
        if av_stars != []:
            show_star_name = av_stars[0]["name"]
            show_star_id = av_stars[0]["id"]
            stars_msg = BOT_CACHE_DB.get_cache(
                key=av_id, type=BotCacheDb.TYPE_STARS_MSG
            )
            if not stars_msg:
                stars_msg = ""
                futures = {}
                more_star_msg = ""
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    for i, star in enumerate(av_stars):
                        # 如果个数大于 5 则退出
                        if i >= 5:
                            more_star_msg = f"""【演员】<a href="{av_url}">查看更多......</a>
"""
                            break
                        # 获取搜索名
                        name = star["name"]
                        other_name_start = name.find("(")  # 删除别名
                        if other_name_start != -1:
                            name = name[:other_name_start]
                            star["name"] = name
                        # 从日文维基获取中文维基
                        futures[
                            executor.submit(
                                WIKI_UTIL.get_wiki_page_by_lang, name, "ja", "zh"
                            )
                        ] = i
                    for future in concurrent.futures.as_completed(futures):
                        future_type = futures[future]
                        wiki_json = future.result()
                        wiki = f"{WIKI_UTIL.BASE_URL_JAPAN_WIKI}/{name}"
                        nam = av_stars[future_type]["name"]
                        trans_util = TransUtil()
                        name = trans_util.trans(text=nam, from_lang="ja", to_lang="en")
                        link = f'{JAVBUS_UTIL.BASE_URL_SEARCH_BY_STAR_ID}/{av_stars[future_type]["id"]}'
                        if wiki_json and wiki_json["lang"] == "zh":
                            name_z = wiki_json["title"]
                            trans_util = TransUtil()
                            name_zh = trans_util.trans(text=name_z, from_lang="ja", to_lang="en")
                            wiki_zh = wiki_json["url"]
                            stars_msg += f"""<code>{name_zh}</code>
"""
                        else:
                            stars_msg += f"""<code>{name}</code>
"""
                if more_star_msg != "":
                    stars_msg += more_star_msg
                BOT_CACHE_DB.set_cache(
                    key=av_id, value=stars_msg, type=BotCacheDb.TYPE_STARS_MSG
                )
            msg += "𝗔𝗰𝘁𝗼𝗿: " + stars_msg
        # 标签
        if av_tags != "":
            av_tags = av_tags.replace("<", "").replace(">", "")
            av_tags = av_tags.replace(" ", "")
            av_tags = av_tags.replace("#", " #")
            msg += f"""𝗚𝗲𝗻𝗿𝗲𝘀:{av_tags}
"""
        # 其它
        #msg += f"""Others: <a href="{BASE_URL_TG}/{PIKPAK_BOT_NAME}">Pikpak</a> | <a href="{PROJECT_ADDRESS}">项目</a> | <a href="{CONTACT_AUTHOR}">作者</a>"""
        # 磁链
        magnet_send_to_pikpak = ""
        for i, magnet in enumerate(av_magnets):
            if i == 0:
                magnet_send_to_pikpak = magnet["link"]
            magnet_tags = ""
            if magnet["uc"] == "1":
                magnet_tags += " UNCENSORED "
            if magnet["hd"] == "1":
                magnet_tags += "HD"
            if magnet["zm"] == "1":
                magnet_tags += " SUBTITLES "
            msg_tmp = f"""[{magnet_tags} {magnet["size"]}] >>> <code>{magnet["link"]}</code>
"""
            if len(msg + msg_tmp) >= 2000:
                break
            #msg += msg_tmp
        # 生成回调按钮
        # 第一排按钮
        pv_btn = InlineKeyboardButton(
            text="Preview", callback_data=f"{av_id}:{BotKey.KEY_WATCH_PV_BY_ID}"
        )
        fv_btn = InlineKeyboardButton(
            text="Watch", callback_data=f"{av_id}:{BotKey.KEY_WATCH_FV_BY_ID}"
        )
        sample_btn = InlineKeyboardButton(
            text="Screens", callback_data=f"{av_id}:{BotKey.KEY_GET_SAMPLE_BY_ID}"
        )
        more_btn = InlineKeyboardButton(
            text="More", callback_data=f"{av_id}:{BotKey.KEY_GET_MORE_MAGNETS_BY_ID}"
        )
        if len(av_magnets) != 0:
            markup = InlineKeyboardMarkup().row(sample_btn, pv_btn, fv_btn, more_btn)
        else:
            markup = InlineKeyboardMarkup().row(sample_btn, pv_btn, fv_btn)
        # 第二排按钮
        # 收藏演员按钮
        star_record_btn = None
        if len(av_stars) == 1:
            if BOT_DB.check_star_exists_by_id(star_id=show_star_id):
                star_record_btn = InlineKeyboardButton(
                    text=f"Actor Collection Information",
                    callback_data=f"{show_star_name}|{show_star_id}:{BotKey.KEY_GET_STAR_DETAIL_RECORD_BY_STAR_NAME_ID}",
                )
            else:
                star_record_btn = InlineKeyboardButton(
                    text=f"Record {show_star_name}",
                    callback_data=f"{show_star_name}|{show_star_id}:{BotKey.KEY_RECORD_STAR_BY_STAR_NAME_ID}",
                )
        star_ids = ""
        for i, star in enumerate(av_stars):
            star_ids += star["id"] + "|"
            if i >= 5:
                star_ids += "...|"
                break
        if star_ids != "":
            star_ids = star_ids[: len(star_ids) - 1]
        # 收藏番号按钮
        av_record_btn = None
        if BOT_DB.check_id_exists(id=av_id):
            av_record_btn = InlineKeyboardButton(
                text=f"ID Collection Information",
                callback_data=f"{av_id}:{BotKey.KEY_GET_AV_DETAIL_RECORD_BY_ID}",
            )
        else:
            av_record_btn = InlineKeyboardButton(
                text=f"Record {av_id}",
                callback_data=f"{av_id}|{star_ids}:{BotKey.KEY_RECORD_AV_BY_ID_STAR_IDS}",
            )
        # 重新获取按钮
        renew_btn = None
        if is_cache:
            renew_btn = InlineKeyboardButton(
                text="Renew", callback_data=f"{av_id}:{BotKey.KEY_DEL_AV_CACHE}"
            )
        if star_record_btn and renew_btn:
            markup.row(av_record_btn, star_record_btn, renew_btn)
        elif star_record_btn:
            markup.row(av_record_btn, star_record_btn)
        elif renew_btn:
            markup.row(av_record_btn, renew_btn)
        else:
            markup.row(av_record_btn)
        # 发送消息
        if av_img == "":
            self.send_msg(msg=msg, markup=markup)
        else:
            try:
                BOT.send_photo(
                    chat_id=BOT_CFG.tg_chat_id,
                    photo=av_img,
                    caption=msg,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            except Exception:  # 少数图片可能没法发送
                self.send_msg(msg=msg, markup=markup)
        # 发给pikpak
        if BOT_CFG.use_pikpak == "1" and magnet_send_to_pikpak != "" and send_to_pikpak:
            self.send_magnet_to_pikpak(magnet_send_to_pikpak, av_id)

    def send_magnet_to_pikpak(self, magnet: str, id: str):
        """发送磁链到pikpak

        :param str magnet: 磁链
        :param str id: 磁链对应的番号
        """
        name = PIKPAK_BOT_NAME
        op_send_magnet_to_pikpak = f"发送番号 {id} 的磁链 A: <code>{magnet}</code> 到 pikpak"
        if self.send_msg_to_pikpak(magnet):
            self.send_msg_success_op(op_send_magnet_to_pikpak)
        else:
            self.send_msg_fail_reason_op(
                reason="Please check the network or logs yourself", op=op_send_magnet_to_pikpak
            )

    def get_sample_by_id(self, id: str):
        """根据番号获取 av 截图

        :param str id: 番号
        """
        op_get_sample = f"According to ID <code>{id}</code> get AV Screenshot"
        # 获取截图
        samples = BOT_CACHE_DB.get_cache(key=id, type=BotCacheDb.TYPE_SAMPLE)
        if not samples:
            code, samples = JAVBUS_UTIL.get_samples_by_id(id)
            if not self.check_success(code, op_get_sample):
                return
            BOT_CACHE_DB.set_cache(key=id, value=samples, type=BotCacheDb.TYPE_SAMPLE)
        # 发送图片列表
        samples_imp = []
        sample_error = False
        for sample in samples:
            samples_imp.append(InputMediaPhoto(sample))
            if len(samples_imp) == 10:  # 图片数目达到 10 张则发送一次
                try:
                    BOT.send_media_group(chat_id=BOT_CFG.tg_chat_id, media=samples_imp)
                    samples_imp = []
                except Exception:
                    sample_error = True
                    self.send_msg_fail_reason_op(reason="Image parsing failed", op=op_get_sample)
                    break
        if samples_imp != [] and not sample_error:
            try:
                BOT.send_media_group(chat_id=BOT_CFG.tg_chat_id, media=samples_imp)
            except Exception:
                self.send_msg_fail_reason_op(reason="Image parsing failed", op=op_get_sample)

    def watch_av_by_id(self, id: str, type: str):
        """获取番号对应视频

        :param str id: 番号
        :param str type: 0 预览视频 | 1 完整视频
        """
        id = id.lower()
        if id.find("fc2") != -1 and id.find("ppv") == -1:
            id = id.replace("fc2", "fc2-ppv")
        if type == 0:
            pv = BOT_CACHE_DB.get_cache(key=id, type=BotCacheDb.TYPE_PV)
            if not pv:
                op_watch_av = f"获取番号 <code>{id}</code> 对应 av 预览视频"
                futures = {}
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures[executor.submit(DMM_UTIL.get_pv_by_id, id)] = 1
                    futures[executor.submit(AVGLE_UTIL.get_pv_by_id, id)] = 2
                    for future in concurrent.futures.as_completed(futures):
                        if futures[future] == 1:
                            code_dmm, pv_dmm = future.result()
                        elif futures[future] == 2:
                            code_avgle, pv_avgle = future.result()
                if code_dmm != 200 and code_avgle != 200:
                    if code_dmm == 502 or code_avgle == 502:
                        self.send_msg_code_op(502, op_watch_av)
                    else:
                        self.send_msg_code_op(404, op_watch_av)
                    return
                from_site = ""
                pv_src = ""
                if code_dmm == 200:
                    from_site = "dmm"
                    pv_src = pv_dmm
                elif code_avgle == 200:
                    from_site = "avgle"
                    pv_src = pv_avgle
                pv_cache = {"from_site": from_site, "src": pv_src}
                BOT_CACHE_DB.set_cache(key=id, value=pv_cache, type=BotCacheDb.TYPE_PV)
            else:
                from_site = pv["from_site"]
                pv_src = pv["src"]
            if from_site == "dmm":  # 优先 dmm
                try:
                    # 获取更清晰的视频地址
                    pv_src_nice = DMM_UTIL.get_nice_pv_by_src(pv_src)
                    # 发送普通视频, 附带更清晰的视频链接
                    BOT.send_video(
                        chat_id=BOT_CFG.tg_chat_id,
                        video=pv_src,
                        caption=f'通过 DMM 搜索得到结果, <a href="{pv_src_nice}">在这里观看更清晰的版本</a>',
                        parse_mode="HTML",
                    )
                except Exception:
                    self.send_msg(
                        f'通过 DMM 搜索得到结果, 但视频解析失败: <a href="{pv_src_nice}">视频地址</a> Q_Q'
                    )
            elif from_site == "avgle":
                try:
                    BOT.send_video(
                        chat_id=BOT_CFG.tg_chat_id,
                        video=pv_src,
                        caption=f'通过 Avgle 搜索得到结果: <a href="{pv_src}">视频地址</a>',
                        parse_mode="HTML",
                    )
                except Exception:
                    self.send_msg(
                        f'通过 Avgle 搜索得到结果, 但视频解析失败: <a href="{pv_src}">视频地址</a> Q_Q'
                    )
        elif type == 1:
            video = BOT_CACHE_DB.get_cache(key=id, type=BotCacheDb.TYPE_FV)
            if not video:
                code, video = AVGLE_UTIL.get_fv_by_id(id)
                if code != 200:
                    self.send_msg(f"MissAv Video URL: {BASE_URL_MISS_AV}/{id}")
                    return
                BOT_CACHE_DB.set_cache(key=id, value=video, type=BotCacheDb.TYPE_FV)
            self.send_msg(
                f"""MissAv Video URL: {BASE_URL_MISS_AV}/{id}

Avgle Video URL: {video}
"""
            )

    def search_star_by_name(self, star_name: str) -> bool:
        """根据演员名称搜索演员

        :param str star_name: 演员名称
        """
        op_search_star = f"搜索演员 <code>{star_name}</code>"
        star = BOT_CACHE_DB.get_cache(key=star_name, type=BotCacheDb.TYPE_STAR)
        if not star:
            star_name_origin = star_name
            star_name = self.get_star_ja_name_by_zh_name(star_name)
            code, star = JAVBUS_UTIL.check_star_exists(star_name)
            if not self.check_success(code, op_search_star):
                return
            BOT_CACHE_DB.set_cache(key=star_name, value=star, type=BotCacheDb.TYPE_STAR)
            if star_name_origin != star_name:
                BOT_CACHE_DB.set_cache(
                    key=star_name_origin,
                    value=star,
                    type=BotCacheDb.TYPE_STAR,
                )
        star_id = star["star_id"]
        star_name = star["star_name"]
        if BOT_DB.check_star_exists_by_id(star_id=star_id):
            self.get_star_detail_record_by_name_id(star_name=star_name, star_id=star_id)
            return True
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                text="Random AV",
                callback_data=f"{star_name}|{star_id}:{BotKey.KEY_RANDOM_GET_AV_BY_STAR_ID}",
            ),
            InlineKeyboardButton(
                text="Latest AV",
                callback_data=f"{star_name}|{star_id}:{BotKey.KEY_GET_NEW_AVS_BY_STAR_NAME_ID}",
            ),
            InlineKeyboardButton(
                text=f"Most Rated AV",
                callback_data=f"{star_name}:{BotKey.KEY_GET_NICE_AVS_BY_STAR_NAME}",
            ),
            InlineKeyboardButton(
                text=f"Record {star_name}",
                callback_data=f"{star_name}|{star_id}:{BotKey.KEY_RECORD_STAR_BY_STAR_NAME_ID}",
            ),
        )
        star_wiki = f"{WIKI_UTIL.BASE_URL_CHINA_WIKI}/{star_name}"
        if langdetect.detect(star_name) == "ja":
            star_wiki = f"{WIKI_UTIL.BASE_URL_JAPAN_WIKI}/{star_name}"
        self.send_msg(
            msg=f'<code>{star_name}</code> | <a href="{star_wiki}">Wiki</a> | <a href="{JAVBUS_UTIL.BASE_URL_SEARCH_BY_STAR_NAME}/{star_name}">Javbus</a>',
            markup=markup,
        )
        return True

    def get_top_stars(self, page=1):
        """根据页数获取 DMM 女优排行榜, 每页 20 位女优

        :param int page: 第几页, 默认第一页
        """
        op_get_top_stars = f"获取 DMM 女优排行榜"
        stars = BOT_CACHE_DB.get_cache(key=page, type=BotCacheDb.TYPE_RANK)

        if not stars:
            code, stars = DMM_UTIL.get_top_stars(page)
            if not self.check_success(code, op_get_top_stars):
                return
            BOT_CACHE_DB.set_cache(key=page, value=stars, type=BotCacheDb.TYPE_RANK)
        stars_tmp = [None] * 80
        stars = stars_tmp[: ((page - 1) * 20)] + stars + stars_tmp[((page - 1) * 20) :]
        col, row = 4, 5
        objs, page_btns, title = self.get_page_elements(
            objs=stars, page=page, col=4, row=5, key_type=BotKey.KEY_GET_TOP_STARS
        )
        self.send_msg_btns(
            max_btn_per_row=col,
            max_row_per_msg=row,
            key_type=BotKey.KEY_SEARCH_STAR_BY_NAME,
            title="<b>DMM 女优排行榜: </b>" + title,
            objs=objs,
            page_btns=page_btns,
        )

    def send_msg_to_pikpak(self, msg):
        """发送消息到Pikpak机器人

        :param _type_ msg: 消息
        :return any: 如果失败则为 None
        """

        async def send():
            try:
                async with Client(
                    name=PATH_SESSION_FILE,
                    api_id=BOT_CFG.tg_api_id,
                    api_hash=BOT_CFG.tg_api_hash,
                    proxy=BOT_CFG.proxy_json_pikpak,
                ) as app:
                    return await app.send_message(PIKPAK_BOT_NAME, msg)
            except Exception as e:
                LOG.error(f"无法将消息发送到 pikpak: {e}")
                return None

        return asyncio.run(send())

    def get_more_magnets_by_id(self, id: str):
        """根据番号获取更多磁链

        :param id: 番号
        """
        magnets = BOT_CACHE_DB.get_cache(key=id, type=BotCacheDb.TYPE_MAGNET)
        if not magnets:
            av = self.get_av_by_id(
                id=id, is_nice=False, is_uncensored=False, not_send=True
            )
            if not av:
                return
            magnets = av["magnets"]
            BOT_CACHE_DB.set_cache(key=id, value=magnets, type=BotCacheDb.TYPE_MAGNET)
        msg = ""
        for magnet in magnets:
            magnet_tags = ""
            if magnet["uc"] == "1":
                magnet_tags += " UNCENSORED"
            if magnet["hd"] == "1":
                magnet_tags += " HD "
            if magnet["zm"] == "1":
                magnet_tags += " SUB "
            star_tag = ""
            if magnet["hd"] == "1" and magnet["zm"] == "1":
                star_tag = "*"
            msg_tmp = f"""【{star_tag}{magnet_tags}磁链 {magnet["size"]}】<code>{magnet["link"]}</code>
"""
            if len(msg + msg_tmp) >= 4000:
                self.send_msg(msg)
                msg = msg_tmp
            else:
                msg += msg_tmp
        if msg != "":
            self.send_msg(msg)

    def get_star_new_avs_by_name_id(self, star_name: str, star_id: str):
        """获取演员最新 av

        :param str star_name: 演员名称
        :param str star_id: 演员 id
        """
        op_get_star_new_avs = f"获取 <code>{star_name}</code> 最新 av"
        ids = BOT_CACHE_DB.get_cache(key=star_id, type=BotCacheDb.TYPE_NEW_AVS_OF_STAR)
        if not ids:
            code, ids = JAVBUS_UTIL.get_new_ids_by_star_id(star_id=star_id)
            if not self.check_success(code, op_get_star_new_avs):
                return
            BOT_CACHE_DB.set_cache(
                key=star_id, value=ids, type=BotCacheDb.TYPE_NEW_AVS_OF_STAR
            )
        title = f"<code>{star_name}</code> 最新 av"
        btns = [
            InlineKeyboardButton(
                text=id, callback_data=f"{id}:{BotKey.KEY_GET_AV_BY_ID}"
            )
            for id in ids
        ]
        if len(btns) <= 4:
            self.send_msg(msg=title, markup=InlineKeyboardMarkup().row(*btns))
        else:
            markup = InlineKeyboardMarkup()
            markup.row(*btns[:4])
            markup.row(*btns[4:])
            self.send_msg(msg=title, markup=markup)

    def get_star_ja_name_by_zh_name(self, star_name: str) -> str:
        """根据中文名字获取日文名字

        :param str star_name: 中文名字
        :return str: 日文名字 (如果查找到)
        """
        if langdetect.detect(star_name) == "ja":
            return star_name
        star_ja_name = BOT_CACHE_DB.get_cache(
            key=star_name, type=BotCacheDb.TYPE_STAR_JA_NAME
        )
        if star_ja_name:
            return star_ja_name
        wiki_json = WIKI_UTIL.get_wiki_page_by_lang(
            topic=star_name, from_lang="zh", to_lang="ja"
        )
        if wiki_json and wiki_json["lang"] == "ja":
            BOT_CACHE_DB.set_cache(
                key=star_name,
                value=wiki_json["title"],
                type=BotCacheDb.TYPE_STAR_JA_NAME,
            )
            return wiki_json["title"]
        return star_name


def handle_callback(call):
    """处理回调

    :param _type_ call
    """
    # 回显 typing...
    bot_utils = BotUtils()
    bot_utils.send_action_typing()
    LOG.info(f"处理回调: {call.data}")
    # 提取回调内容
    s = call.data.rfind(":")
    content = call.data[:s]
    key_type = call.data[s + 1 :]
    # 检查按键类型并处理
    if key_type == BotKey.KEY_WATCH_PV_BY_ID:
        bot_utils.watch_av_by_id(id=content, type=0)
    elif key_type == BotKey.KEY_WATCH_FV_BY_ID:
        bot_utils.watch_av_by_id(id=content, type=1)
    elif key_type == BotKey.KEY_GET_SAMPLE_BY_ID:
        bot_utils.get_sample_by_id(id=content)
    elif key_type == BotKey.KEY_GET_MORE_MAGNETS_BY_ID:
        bot_utils.get_more_magnets_by_id(id=content)
    elif key_type == BotKey.KEY_RANDOM_GET_AV_BY_STAR_ID:
        tmp = content.split("|")
        star_name = tmp[0]
        star_id = tmp[1]
        code, id = JAVBUS_UTIL.get_id_by_star_id(star_id=star_id)
        if bot_utils.check_success(code, f"随机获取演员 <code>{star_name}</code> 的 av"):
            bot_utils.get_av_by_id(id=id)
    elif key_type == BotKey.KEY_GET_NEW_AVS_BY_STAR_NAME_ID:
        tmp = content.split("|")
        star_name = tmp[0]
        star_id = tmp[1]
        bot_utils.get_star_new_avs_by_name_id(star_name=star_name, star_id=star_id)
    elif key_type == BotKey.KEY_RECORD_STAR_BY_STAR_NAME_ID:
        s = content.find("|")
        star_name = content[:s]
        star_id = content[s + 1 :]
        if BOT_DB.record_star_by_name_id(star_name=star_name, star_id=star_id):
            bot_utils.get_star_detail_record_by_name_id(
                star_name=star_name, star_id=star_id
            )
        else:
            bot_utils.send_msg_code_op(500, f"收藏演员 <code>{star_name}</code>")
    elif key_type == BotKey.KEY_RECORD_AV_BY_ID_STAR_IDS:
        res = content.split("|")
        id = res[0]
        stars = []
        if res[1] != "":
            stars = [s for s in res[1:]]
        if BOT_DB.record_id_by_id_stars(id=id, stars=stars):
            bot_utils.get_av_detail_record_by_id(id=id)
        else:
            bot_utils.send_msg_code_op(500, f"收藏番号 <code>{id}</code>")
    elif key_type == BotKey.KEY_GET_STARS_RECORD:
        bot_utils.get_stars_record(page=int(content))
    elif key_type == BotKey.KEY_GET_AVS_RECORD:
        bot_utils.get_avs_record(page=int(content))
    elif key_type == BotKey.KEY_GET_STAR_DETAIL_RECORD_BY_STAR_NAME_ID:
        s = content.find("|")
        bot_utils.get_star_detail_record_by_name_id(
            star_name=content[:s], star_id=content[s + 1 :]
        )
    elif key_type == BotKey.KEY_GET_AV_DETAIL_RECORD_BY_ID:
        bot_utils.get_av_detail_record_by_id(id=content)
    elif key_type == BotKey.KEY_GET_AV_BY_ID:
        bot_utils.get_av_by_id(id=content)
    elif key_type == BotKey.KEY_RANDOM_GET_AV_NICE:
        code, id = JAVLIB_UTIL.get_random_id_from_rank(0)
        if bot_utils.check_success(code, "随机获取高分 av"):
            bot_utils.get_av_by_id(id=id)
    elif key_type == BotKey.KEY_RANDOM_GET_AV_NEW:
        code, id = JAVLIB_UTIL.get_random_id_from_rank(1)
        if bot_utils.check_success(code, "随机获取最新 av"):
            bot_utils.get_av_by_id(id=id)
    elif key_type == BotKey.KEY_UNDO_RECORD_AV_BY_ID:
        op_undo_record_av = f"取消收藏番号 <code>{content}</code>"
        if BOT_DB.undo_record_id(id=content):
            bot_utils.send_msg_success_op(op_undo_record_av)
        else:
            bot_utils.send_msg_fail_reason_op(reason="文件解析出错", op=op_undo_record_av)
    elif key_type == BotKey.KEY_UNDO_RECORD_STAR_BY_STAR_NAME_ID:
        s = content.find("|")
        op_undo_record_star = f"取消收藏演员 <code>{content[:s]}</code>"
        if BOT_DB.undo_record_star_by_id(star_id=content[s + 1 :]):
            bot_utils.send_msg_success_op(op_undo_record_star)
        else:
            bot_utils.send_msg_fail_reason_op(reason="文件解析出错", op=op_undo_record_star)
    elif key_type == BotKey.KEY_SEARCH_STAR_BY_NAME:
        star_name = content
        star_name_alias = ""
        idx_alias = star_name.find("（")
        if idx_alias != -1:
            star_name_alias = star_name[idx_alias + 1 : -1]
            star_name = star_name[:idx_alias]
        if not bot_utils.search_star_by_name(star_name) and star_name_alias != "":
            bot_utils.send_msg(f"尝试搜索演员{star_name}的别名{star_name_alias}......")
            bot_utils.search_star_by_name(star_name_alias)
    elif key_type == BotKey.KEY_GET_TOP_STARS:
        bot_utils.get_top_stars(page=int(content))
    elif key_type == BotKey.KEY_GET_NICE_AVS_BY_STAR_NAME:
        star_name_ori = content
        avs = BOT_CACHE_DB.get_cache(
            key=star_name_ori, type=BotCacheDb.TYPE_NICE_AVS_OF_STAR
        )
        if not avs:
            star_name_ja = bot_utils.get_star_ja_name_by_zh_name(star_name_ori)
            code, avs = DMM_UTIL.get_nice_avs_by_star_name(star_name=star_name_ja)
            if bot_utils.check_success(code, f"获取演员 {star_name_ori} 的高分 av"):
                avs = avs[:60]
                BOT_CACHE_DB.set_cache(
                    key=star_name_ori,
                    value=avs,
                    type=BotCacheDb.TYPE_NICE_AVS_OF_STAR,
                )
                if star_name_ja != star_name_ori:
                    BOT_CACHE_DB.set_cache(
                        key=star_name_ja,
                        value=avs,
                        type=BotCacheDb.TYPE_NICE_AVS_OF_STAR,
                    )
            else:
                return
        bot_utils.send_msg_btns(
            max_btn_per_row=3,
            max_row_per_msg=20,
            key_type=BotKey.KEY_GET_AV_BY_ID,
            title=f"<b>Actor {star_name_ori} Highest Rating AV</b>",
            objs=avs,
        )
    elif key_type == BotKey.KEY_DEL_AV_CACHE:
        BOT_CACHE_DB.remove_cache(key=content, type=BotCacheDb.TYPE_AV)
        BOT_CACHE_DB.remove_cache(key=content, type=BotCacheDb.TYPE_STARS_MSG)
        bot_utils.get_av_by_id(id=content)


def handle_message(message):
    """处理消息

    :param _type_ message
    """
    # 回显 typing...
    bot_utils = BotUtils()
    bot_utils.send_action_typing()
    # 拦截请求
    chat_id = str(message.chat.id)
    if chat_id.lower() != BOT_CFG.tg_chat_id.lower():
        LOG.info(f"拦截到非目标用户请求, id: {chat_id}")
        BOT.send_message(
            chat_id=chat_id,
            text=f'This robot is for private use only, if you want to use it, please deploy it yourself: <a href="{PROJECT_ADDRESS}">Project</a>',
            parse_mode="HTML",
        )
        return
    bot_utils = BotUtils()
    # 获取消息文本内容
    if message.content_type != "text":
        msg = message.caption
    else:
        msg = message.text
    if not msg:
        return
    LOG.info(f'Received Moves: "{msg}"')
    msg = msg.lower().strip()
    msgs = msg.split(" ", 1)  # 划分为两部分
    # 消息命令
    msg_cmd = msgs[0]
    # 消息参数
    msg_param = ""
    if len(msgs) > 1:  # 有参数
        msg_param = msgs[1].strip()
    # 处理消息
    if msg_cmd == "/help" or msg_cmd == "/start":
        bot_utils.send_msg(MSG_HELP)
    elif msg_cmd == "/nice":
        page = random.randint(1, JAVLIB_UTIL.MAX_RANK_PAGE)
        ids = BOT_CACHE_DB.get_cache(key=page, type=BotCacheDb.TYPE_JLIB_PAGE_NICE_AVS)
        if not ids:
            code, ids = JAVLIB_UTIL.get_random_ids_from_rank_by_page(
                page=page, list_type=0
            )
            if bot_utils.check_success(code, "随机获取高分 av"):
                BOT_CACHE_DB.set_cache(
                    key=page,
                    value=ids,
                    type=BotCacheDb.TYPE_JLIB_PAGE_NICE_AVS,
                )
            else:
                return
        bot_utils.get_av_by_id(id=random.choice(ids))
    elif msg_cmd == "/new":
        page = random.randint(1, JAVLIB_UTIL.MAX_RANK_PAGE)
        ids = BOT_CACHE_DB.get_cache(key=page, type=BotCacheDb.TYPE_JLIB_PAGE_NEW_AVS)
        if not ids:
            code, ids = JAVLIB_UTIL.get_random_ids_from_rank_by_page(
                page=page, list_type=1
            )
            if bot_utils.check_success(code, "随机获取最新 av"):
                BOT_CACHE_DB.set_cache(
                    key=page,
                    value=ids,
                    type=BotCacheDb.TYPE_JLIB_PAGE_NEW_AVS,
                )
            else:
                return
        bot_utils.get_av_by_id(id=random.choice(ids))
    elif msg_cmd == "/stars":
        bot_utils.get_stars_record()
    elif msg_cmd == "/avs":
        bot_utils.get_avs_record()
    elif msg_cmd == "/record":
        if os.path.exists(PATH_RECORD_FILE):
            BOT.send_document(
                chat_id=BOT_CFG.tg_chat_id, document=types.InputFile(PATH_RECORD_FILE)
            )
        else:
            bot_utils.send_msg_fail_reason_op(reason="尚无收藏记录", op="获取收藏记录文件")
    elif msg_cmd == "/rank":
        bot_utils.get_top_stars(1)
    elif msg_cmd == "/star":
        if msg_param != "":
            bot_utils.send_msg(f"搜索演员: <code>{msg_param}</code> ......")
            bot_utils.search_star_by_name(msg_param)
    elif msg_cmd == "/av":
        if msg_param:
            bot_utils.send_msg(f"搜索番号: <code>{msg_param}</code> ......")
            bot_utils.get_av_by_id(id=msg_param, send_to_pikpak=True)
    else:
        ids = AV_PAT.findall(msg)
        if not ids or len(ids) == 0:
            bot_utils.send_msg(
                "消息似乎不存在符合规则的番号, 可尝试通过“<code>/av</code> 番号”进行查找, 通过 /help 命令可获得帮助 ~"
            )
        else:
            ids = [id.lower() for id in ids]
            ids = set(ids)
            ids_msg = ", ".join(ids)
            bot_utils.send_msg(f"ID Detected: {ids_msg}, Searching...")
            for i, id in enumerate(ids):
                threading.Thread(target=bot_utils.get_av_by_id, args=(id,)).start()


EXECUTOR = concurrent.futures.ThreadPoolExecutor()


@BOT.callback_query_handler(func=lambda call: True)
def my_callback_handler(call):
    """消息回调处理器

    :param _type_ call
    """
    EXECUTOR.submit(handle_callback, call)


@BOT.message_handler(content_types=["text", "photo", "animation", "video", "document"])
def my_message_handler(message):
    """消息处理器

    :param _type_ message: 消息
    """
    EXECUTOR.submit(handle_message, message)


def pyrogram_auth():
    if BOT_CFG.use_pikpak == "1" and not os.path.exists(f"{PATH_SESSION_FILE}.session"):
        LOG.info(f"Perform pyrogram login authentication......")
        try:
            BotUtils().send_msg_to_pikpak("pyrogram 登录认证")
            LOG.info(f"pyrogram login authentication succeeded")
        except BaseException as e:
            LOG.error(f"pyrogram login authentication failed: {e}")


@app.route('/')
def hello():
    return "JAV BLASTER BOT is Alive!"

def main():
    pyrogram_auth()
    try:
        bot_info = BOT.get_me()
        LOG.info(f"Connected to robot: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        LOG.error(f"Can't connect to robot: {e}")
        return

    BOT.set_my_commands([types.BotCommand(cmd, BOT_CMDS[cmd]) for cmd in BOT_CMDS])

    # Start the Flask app in a separate thread
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}).start()

    BOT.infinity_polling()

if __name__ == "__main__":
    main()
