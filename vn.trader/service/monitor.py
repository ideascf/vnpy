# encoding: utf-8
from __future__ import print_function
import os
import sys
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))

from datetime import datetime
import signal
from time import sleep
from vtClient import VtClient
import vtConstant
from eventEngine import *
from service import config


def printLog(content):
    """打印日志"""
    print(datetime.now().strftime("%H:%M:%S"), '\t', content)

class Monitor(object):
    def __init__(self, marketingAddr, strategyAddr, tradeAddr, eventEngine):
        self.marketingAddr = marketingAddr
        self.strategyAddr = strategyAddr
        self.tradeAddr = tradeAddr
        self.marketingCli = None
        self.strategyCli = None
        self.tradeCli = None
        self.eventEngine = eventEngine

        self.isRunning = False

    def start(self):
        self.eventEngine.start()

        if self.marketingAddr:
            self.marketingCli = VtClient('tcp://localhost:0', self.marketingAddr, self.eventEngine)
            self.marketingCli.subscribeTopic('')
            self.marketingCli.start()

        if self.strategyAddr:
            self.strategyCli = VtClient('tcp://localhost:0', self.strategyAddr, self.eventEngine)
            self.strategyCli.subscribeTopic('')
            self.strategyCli.start()

        if self.tradeAddr:
            self.tradeCli = VtClient('tcp://localhost:0', self.tradeAddr, self.eventEngine)
            self.tradeCli.subscribeTopic('')
            self.tradeCli.start()

        self.isRunning = True
        while self.isRunning:
            printLog(u'请输入Ctrl-C来关闭服务器')
            sleep(1)

        self.stop()

    def stop(self):
        if self.marketingCli:
            self.marketingCli.stop()
        if self.strategyCli:
            self.strategyCli.stop()
        if self.tradeCli:
            self.tradeCli.stop()

        self.eventEngine.stop()

g_monitor = None
def signal_handler(signum, frame):
    if signum in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
        if g_monitor is not None:
            g_monitor.isRunning = False

# ----------------------------------------------------------------------
def runServer():
    """运行服务器"""
    global g_monitor
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    def handler(event):
        print(event.__dict__)

    eventEngine = EventEngine2()
    eventEngine.registerGeneralHandler(handler)

    g_monitor = Monitor(
        config.MARKETING_PUB_ADDR,
        config.STRATEGY_PUB_ADDR,
        config.TRADE_PUB_ADDR,
        eventEngine,
    )
    g_monitor.start()


if __name__ == '__main__':
    runServer()