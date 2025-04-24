#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
仪表盘启动脚本 - 仅启动Web界面
"""

import os
import logging
import time
from src.dashboard import Dashboard

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MoodSense.Runner")

if __name__ == "__main__":
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)
    
    try:
        # 创建并启动仪表盘
        logger.info("启动仪表盘...")
        dashboard = Dashboard(host='0.0.0.0', port=8080, debug=False)
        dashboard.start()
        
        # 保持主线程运行
        logger.info("仪表盘已启动，按Ctrl+C停止")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止...")
        if 'dashboard' in locals():
            dashboard.stop()
    except Exception as e:
        logger.exception(f"发生错误: {e}")
