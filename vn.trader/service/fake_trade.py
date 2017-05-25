# encoding: utf-8
from __future__ import print_function
import os
import sys
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))

from datetime import datetime
import signal
import functools
from time import sleep
from vtServer import VtServer
import vtConstant
from service import config
from service.trade import Trade
from vtEngine import EventEngine2
from collections import defaultdict


def printLog(content):
    """打印日志"""
    print(datetime.now().strftime("%H:%M:%S"), '\t', content)

class FakeMainEngine(object):
    def __init__(self, enableCtaEngine=True, enableDrEngine=True, enableRmEngine=True):
        """Constructor"""
        # 记录今日日期
        self.todayDate = datetime.now().strftime('%Y%m%d')

        # 创建事件引擎
        self.eventEngine = EventEngine2()
        self.eventEngine.start()

        # 创建数据引擎
        self.dataEngine = None

        # MongoDB数据库相关
        self.dbClient = None  # MongoDB客户端对象

        # 调用一个个初始化函数
        self.initGateway()

        # 扩展模块
        self.ctaEngine = None
        self.drEngine = None
        self.rmEngine = None
        self.gatewayDict = defaultdict(int)

    def __getattr__(self, item):
        def stub(*args, **kwargs):
            print(item, args, kwargs)
            return None

        stub.__name__ = item

        return stub

g_trade = None
def signal_handler(signum, frame):
    if signum in (signal.SIGINT, signal.SIGTERM):
        if g_trade is not None:
            g_trade.isRunning = False

# ----------------------------------------------------------------------
def runServer():
    """运行服务器"""
    global g_trade
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    g_trade = Trade(
        config.TRADE_REQ_ADDR,
        config.TRADE_PUB_ADDR,
    )
    g_trade.start([
        vtConstant.EXCHANGE_CHBTC,
    ], FakeMainEngine())


if __name__ == '__main__':
    runServer()