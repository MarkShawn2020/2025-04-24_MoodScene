#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MoodSense - 环境识别与情绪感知系统
主程序入口
"""

import os
import time
import logging
import threading
from dotenv import load_dotenv

# 设置OpenCV摄像头权限环境变量
os.environ['OPENCV_AVFOUNDATION_SKIP_AUTH'] = '1'

# 导入核心模块
from src.video_analyzer import VideoAnalyzer
from src.audio_analyzer import AudioAnalyzer
from src.environment_analyzer import EnvironmentAnalyzer
from src.emotion_detector import EmotionDetector
from src.input_monitor import InputMonitor
from src.data_integrator import DataIntegrator
from src.dashboard import Dashboard

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/moodsense.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MoodSense")

# 加载环境变量
load_dotenv()

class MoodSense:
    """MoodSense主应用类"""
    
    def __init__(self):
        """初始化MoodSense系统"""
        logger.info("初始化MoodSense系统...")
        
        # 创建各个分析器实例
        self.video_analyzer = VideoAnalyzer()
        self.audio_analyzer = AudioAnalyzer()
        self.environment_analyzer = EnvironmentAnalyzer()
        self.emotion_detector = EmotionDetector()
        self.input_monitor = InputMonitor()
        
        # 创建数据整合器
        self.data_integrator = DataIntegrator()
        
        # 创建仪表盘
        self.dashboard = Dashboard()
        
        # 线程列表
        self.threads = []
        
        # 运行标志
        self.running = False
        
        logger.info("MoodSense系统初始化完成")
    
    def start(self):
        """启动MoodSense系统"""
        logger.info("启动MoodSense系统...")
        self.running = True
        
        # 创建并启动各个模块的线程
        threads = [
            threading.Thread(target=self.video_analyzer.start, daemon=True),
            threading.Thread(target=self.audio_analyzer.start, daemon=True),
            threading.Thread(target=self.environment_analyzer.start, daemon=True),
            threading.Thread(target=self.emotion_detector.start, daemon=True),
            threading.Thread(target=self.input_monitor.start, daemon=True),
            threading.Thread(target=self.data_integrator.start, daemon=True),
        ]
        
        # 启动所有线程
        for thread in threads:
            thread.start()
            self.threads.append(thread)
        
        # 启动仪表盘（主线程）
        self.dashboard.start()
        
        logger.info("MoodSense系统已启动")
    
    def stop(self):
        """停止MoodSense系统"""
        logger.info("正在停止MoodSense系统...")
        self.running = False
        
        # 停止各个模块
        self.video_analyzer.stop()
        self.audio_analyzer.stop()
        self.environment_analyzer.stop()
        self.emotion_detector.stop()
        self.input_monitor.stop()
        self.data_integrator.stop()
        self.dashboard.stop()
        
        # 等待所有线程结束
        for thread in self.threads:
            thread.join(timeout=2.0)
        
        logger.info("MoodSense系统已停止")

if __name__ == "__main__":
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)
    
    try:
        # 创建并启动MoodSense系统
        mood_sense = MoodSense()
        mood_sense.start()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止...")
        if 'mood_sense' in locals():
            mood_sense.stop()
    except Exception as e:
        logger.exception(f"发生错误: {e}")
