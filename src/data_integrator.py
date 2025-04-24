#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据整合器模块
负责整合各个模块的数据，提供综合分析结果
"""

import time
import logging
import threading
from queue import Queue
import numpy as np
import pandas as pd
from datetime import datetime
import json
import os

logger = logging.getLogger("MoodSense.DataIntegrator")

class DataIntegrator:
    """数据整合器类，负责整合和分析所有数据源"""
    
    def __init__(self, update_interval=1.0, history_length=3600):
        """
        初始化数据整合器
        
        Args:
            update_interval: 更新间隔（秒）
            history_length: 历史数据长度（数据点数量）
        """
        self.update_interval = update_interval
        self.history_length = history_length
        self.running = False
        self.result_queue = Queue(maxsize=10)
        
        # 各个模块的最新数据
        self.video_data = {}
        self.audio_data = {}
        self.environment_data = {}
        self.emotion_data = {}
        self.input_data = {}
        
        # 整合后的数据
        self.integrated_data = {}
        
        # 历史数据 (DataFrame格式)
        self.data_history = pd.DataFrame()
        
        # 状态评估
        self.productivity_score = 0.5  # 生产力得分 (0-1)
        self.wellbeing_score = 0.5     # 健康状态得分 (0-1)
        self.mood_score = 0.0          # 情绪得分 (-1到1)
        self.environment_score = 0.5   # 环境质量得分 (0-1)
        
        # 数据存储路径
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info("数据整合器初始化完成")
    
    def start(self):
        """启动数据整合"""
        if self.running:
            logger.warning("数据整合器已在运行")
            return
        
        logger.info("启动数据整合器...")
        self.running = True
        
        # 启动整合线程
        self.integration_thread = threading.Thread(target=self._integration_loop, daemon=True)
        self.integration_thread.start()
        
        logger.info("数据整合器已启动")
    
    def stop(self):
        """停止数据整合"""
        if not self.running:
            return
        
        logger.info("正在停止数据整合器...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'integration_thread'):
            self.integration_thread.join(timeout=1.0)
        
        # 在停止前保存数据
        self._save_data()
        
        logger.info("数据整合器已停止")
    
    def update_video_data(self, data):
        """更新视频数据"""
        self.video_data = data
    
    def update_audio_data(self, data):
        """更新音频数据"""
        self.audio_data = data
    
    def update_environment_data(self, data):
        """更新环境数据"""
        self.environment_data = data
    
    def update_emotion_data(self, data):
        """更新情绪数据"""
        self.emotion_data = data
    
    def update_input_data(self, data):
        """更新输入数据"""
        self.input_data = data
    
    def get_latest_data(self):
        """获取最新整合数据"""
        return self.integrated_data
    
    def get_history(self, timespan_seconds=300):
        """
        获取历史数据
        
        Args:
            timespan_seconds: 时间跨度（秒）
        
        Returns:
            DataFrame: 历史数据
        """
        if self.data_history.empty:
            return pd.DataFrame()
        
        # 获取当前时间
        now = datetime.now()
        
        # 计算时间阈值
        threshold = now.timestamp() - timespan_seconds
        
        # 过滤数据
        filtered_data = self.data_history[self.data_history['timestamp'] > threshold]
        
        return filtered_data
    
    def get_analysis_results(self):
        """获取分析结果"""
        # 整合最新数据
        integrated_data = self._integrate_data()
        
        # 添加评分
        integrated_data.update({
            'productivity_score': self.productivity_score,
            'wellbeing_score': self.wellbeing_score,
            'mood_score': self.mood_score,
            'environment_score': self.environment_score,
            'timestamp': datetime.now().isoformat()
        })
        
        return integrated_data
    
    def _integrate_data(self):
        """整合所有数据源"""
        integrated_data = {
            'video': self.video_data,
            'audio': self.audio_data,
            'environment': self.environment_data,
            'emotion': self.emotion_data,
            'input': self.input_data
        }
        
        # 提取关键特征到顶层
        brightness = self.video_data.get('brightness', 0.0)
        noise_level = self.audio_data.get('noise_level', 0.0)
        emotion = self.emotion_data.get('emotion', 'neutral')
        typing_speed = self.input_data.get('typing_speed', 0.0)
        focus_level = self.input_data.get('focus_level', 0.5)
        
        # 添加到整合数据
        integrated_data.update({
            'brightness': brightness,
            'noise_level': noise_level,
            'emotion': emotion,
            'typing_speed': typing_speed,
            'focus_level': focus_level
        })
        
        # 如果有视频帧数据，直接传递到整合数据的顶层
        if 'frame_data' in self.video_data:
            integrated_data['video']['frame_data'] = self.video_data['frame_data']
            # 打印视频帧信息（仅打印长度，不打印实际内容）
            frame_length = len(self.video_data['frame_data']) if isinstance(self.video_data['frame_data'], str) else 0
            logger.info(f"已整合视频帧数据，长度: {frame_length} 字节")
        
        return integrated_data
    
    def _calculate_scores(self):
        """计算各项评分"""
        # 提取关键指标
        brightness = self.integrated_data.get('brightness', 0.5)
        noise_level = self.integrated_data.get('noise_level', 0.0)
        motion_level = self.video_data.get('motion_level', 0.0)
        typing_speed = self.input_data.get('typing_speed', 0.0)
        focus_level = self.input_data.get('focus_level', 0.5)
        emotion = self.emotion_data.get('emotion', 'neutral')
        valence = self.emotion_data.get('valence', 0.0)
        arousal = self.emotion_data.get('arousal', 0.0)
        
        # 计算环境评分 (亮度和噪音适中的环境评分高)
        brightness_score = 1.0 - 2.0 * abs(brightness - 0.5)  # 0.5是理想亮度
        noise_score = 1.0 - noise_level  # 噪音越低越好
        self.environment_score = 0.6 * brightness_score + 0.4 * noise_score
        
        # 计算生产力评分
        # 打字速度归一化 (300字符/分钟为满分)
        norm_typing = min(1.0, typing_speed / 300.0)
        # 生产力评分 (专注度和打字速度的加权平均)
        self.productivity_score = 0.7 * focus_level + 0.3 * norm_typing
        
        # 计算情绪评分 (效价)
        self.mood_score = valence
        
        # 计算健康状态评分
        # 情绪正面性 (转换-1到1的效价到0到1)
        emotion_positivity = (valence + 1.0) / 2.0
        # 活动水平适度性 (中等活动水平最佳)
        activity_score = 1.0 - 2.0 * abs(motion_level - 0.5)
        # 健康状态评分 (情绪正面性和适度活动的加权平均)
        self.wellbeing_score = 0.6 * emotion_positivity + 0.4 * activity_score
    
    def _append_to_history(self):
        """将当前数据添加到历史记录"""
        # 创建新的数据点
        data_point = {
            'timestamp': datetime.now().timestamp(),
            'datetime': datetime.now(),
            'brightness': self.integrated_data.get('brightness', 0.0),
            'noise_level': self.integrated_data.get('noise_level', 0.0),
            'motion_level': self.video_data.get('motion_level', 0.0),
            'emotion': self.emotion_data.get('emotion', 'neutral'),
            'valence': self.emotion_data.get('valence', 0.0),
            'arousal': self.emotion_data.get('arousal', 0.0),
            'typing_speed': self.input_data.get('typing_speed', 0.0),
            'focus_level': self.input_data.get('focus_level', 0.5),
            'productivity_score': self.productivity_score,
            'wellbeing_score': self.wellbeing_score,
            'mood_score': self.mood_score,
            'environment_score': self.environment_score
        }
        
        # 转换为DataFrame
        data_df = pd.DataFrame([data_point])
        
        # 添加到历史记录
        if self.data_history.empty:
            self.data_history = data_df
        else:
            self.data_history = pd.concat([self.data_history, data_df], ignore_index=True)
        
        # 限制历史记录长度
        if len(self.data_history) > self.history_length:
            self.data_history = self.data_history.iloc[-self.history_length:]
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            # 保存历史数据
            if not self.data_history.empty:
                # 生成文件名 (基于当前时间)
                filename = f"moodsense_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(self.data_dir, filename)
                
                # 保存到CSV
                self.data_history.to_csv(filepath, index=False)
                logger.info(f"数据已保存到: {filepath}")
                
                # 保存最新快照为JSON
                snapshot_file = os.path.join(self.data_dir, "latest_snapshot.json")
                with open(snapshot_file, 'w', encoding='utf-8') as f:
                    # 转换datetime为字符串
                    latest_data = self.integrated_data.copy()
                    latest_data['timestamp'] = datetime.now().isoformat()
                    json.dump(latest_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存数据时出错: {str(e)}")
    
    def _integration_loop(self):
        """数据整合循环"""
        # 上次保存时间
        last_save_time = time.time()
        save_interval = 300  # 每5分钟保存一次
        
        while self.running:
            try:
                # 整合数据
                self.integrated_data = self._integrate_data()
                
                # 计算各项评分
                self._calculate_scores()
                
                # 添加到历史记录
                self._append_to_history()
                
                # 获取分析结果
                result = self.get_analysis_results()
                
                # 如果结果队列已满，移除最旧的结果
                if self.result_queue.full():
                    try:
                        self.result_queue.get_nowait()
                    except:
                        pass
                
                # 放入新结果
                try:
                    self.result_queue.put(result, block=False)
                except:
                    pass
                
                # 定期保存数据
                current_time = time.time()
                if current_time - last_save_time > save_interval:
                    self._save_data()
                    last_save_time = current_time
                
                # 等待下一个更新周期
                time.sleep(self.update_interval)
                
            except Exception as e:
                if self.running:  # 只在运行时记录错误
                    logger.error(f"数据整合错误: {str(e)}")
                time.sleep(0.1)
