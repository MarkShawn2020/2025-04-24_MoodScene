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
        
        # 创建数据集成线程
        self.data_sync_thread = threading.Thread(target=self._data_sync_loop, daemon=True)
        self.data_sync_thread.start()
        self.threads.append(self.data_sync_thread)
        
        # 启动仪表盘（主线程）
        self.dashboard.start()
        
        logger.info("MoodSense系统已启动")
    
    def _data_sync_loop(self):
        """数据同步循环，将各个模块的数据同步到数据整合器和仪表盘"""
        logger.info("数据同步循环已启动")
        
        while self.running:
            try:
                # 获取视频分析结果
                video_data = self.video_analyzer.get_analysis_results()
                self.data_integrator.update_video_data(video_data)
                
                # 获取音频分析结果
                audio_data = self.audio_analyzer.get_analysis_results()
                self.data_integrator.update_audio_data(audio_data)
                
                # 获取环境分析结果
                # 先更新环境数据
                self.environment_analyzer.update_data('brightness', video_data['brightness'])
                self.environment_analyzer.update_data('noise_level', audio_data.get('noise_level', 0.0))
                self.environment_analyzer.update_data('motion_level', video_data['motion_level'])
                
                # 获取环境分析结果
                environment_data = self.environment_analyzer.get_analysis_results()
                self.data_integrator.update_environment_data(environment_data)
                
                # 获取情绪状态
                # 先更新情绪数据
                if video_data.get('face_detected', False):
                    # 如果检测到人脸，更新情绪状态
                    self.emotion_detector.update_face_emotion(self.video_analyzer.last_frame)
                
                self.emotion_detector.update_voice_emotion(audio_data)
                
                # 获取输入状态
                input_data = self.input_monitor.get_analysis_results()
                self.data_integrator.update_input_data(input_data)
                
                # 更新情绪状态
                self.emotion_detector.update_behavior_emotion(
                    video_data['motion_level'],
                    input_data.get('typing_speed', 0.0),
                    input_data.get('typing_errors', 0.0),
                    input_data.get('focus_level', 0.5)
                )
                
                # 获取情绪分析结果
                emotion_data = self.emotion_detector.get_analysis_results()
                self.data_integrator.update_emotion_data(emotion_data)
                
                # 获取整合数据
                integrated_data = self.data_integrator.get_analysis_results()
                
                # 更新仪表盘数据
                self.dashboard.update_data(integrated_data)
                
                # 在控制台打印视频帧状态
                has_frame = 'frame_data' in video_data
                logger.debug(f"调试: 视频帧存在状态: {has_frame}")
                
                # 等待一小段时间
                time.sleep(0.1)  # 100ms更新一次
                
            except Exception as e:
                logger.error(f"数据同步循环出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(1.0)  # 出错时等待1秒再继续
    
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
