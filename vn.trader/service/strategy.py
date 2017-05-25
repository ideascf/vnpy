# encoding: utf-8
from __future__ import print_function
import os
import sys
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))

from datetime import datetime
import signal
from time import sleep
from vtServer import VtServer
from vtClient import VtClient, ClientEngine
import vtConstant
from vtEngine import MainEngine
from eventEngine import *
from service import config


def printLog(content):
    """打印日志"""
    print(datetime.now().strftime("%H:%M:%S"), '\t', content)


class Strategy(object):
    def __init__(self, marketingAddr, tradeAddr):
        """
        
        :param marketingAddr: 
        :type marketingAddr: 
        :param tradeAddr:  交易服务的rpc请求地址
        :type tradeAddr: 市场服务的publish地址
        """

        self.marketingAddr = marketingAddr
        self.tradeAddr = tradeAddr

        self.eventEngine = EventEngine2()
        self.cli = VtClient(self.tradeAddr, self.marketingAddr, self.eventEngine)
        self.cliEngine = ClientEngine(self.cli, self.eventEngine)

        self.isRunning = False


    def start(self):
        self.eventEngine.start(timer=True)
        self.cli.subscribeTopic('')
        self.cli.start()


        self.cliEngine.ctaEngine.loadStrategy({
            'name': 'KLineStrategy',
            'className': 'KLineStrategy',
            'vtSymbol': 'ETHCNY.CHBTC',
        })


        self.onStart()

        self.isRunning = True
        self.onRunging()

        self.stop()

    def stop(self):
        self.cliEngine.exit()


    def onStart(self):
        def handler(event):
            # print(event.type_, event.dict_)
            pass

        self.eventEngine.registerGeneralHandler(handler)

    def onRunging(self):
        cnt = 0
        while self.isRunning:
            if cnt >= 10:
                cnt = 0
                printLog(u'请输入Ctrl-C来关闭服务器')

            cnt += 1
            sleep(1)


g_strategy = None
def signal_handler(signum, frame):
    if signum in (signal.SIGINT, signal.SIGTERM):
        if g_strategy is not None:
            g_strategy.isRunning = False

# ----------------------------------------------------------------------
def runServer():
    """运行服务器"""
    global g_strategy
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    g_strategy = Strategy(
        config.MARKETING_PUB_ADDR,
        config.TRADE_REQ_ADDR,
    )
    g_strategy.start()


if __name__ == '__main__':
    runServer()