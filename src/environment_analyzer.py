#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
环境分析器模块
负责聚合和分析环境状态参数，包括亮度、噪音等
"""

import time
import logging
import threading
import numpy as np
from queue import Queue
from datetime import datetime

logger = logging.getLogger("MoodSense.EnvironmentAnalyzer")

class EnvironmentAnalyzer:
    """环境分析器类，负责整合各种环境数据"""
    
    def __init__(self, update_interval=1.0):
        """
        初始化环境分析器
        
        Args:
            update_interval: 更新间隔（秒）
        """
        self.update_interval = update_interval
        self.running = False
        self.result_queue = Queue(maxsize=10)
        
        # 环境数据
        self.brightness = 0.0       # 亮度水平 (0-1)
        self.noise_level = 0.0      # 噪音水平 (0-1)
        self.motion_level = 0.0     # 运动水平 (0-1)
        self.room_activity = 0.0    # 房间活动水平 (0-1)
        self.time_of_day = None     # 当天时间
        self.environment_type = "未知" # 环境类型 (安静、嘈杂等)
        
        # 用于计算变化率的历史数据
        self.history = {
            'brightness': [],
            'noise_level': [],
            'motion_level': [],
            'room_activity': []
        }
        self.max_history = 30  # 保存30个历史点
        
        logger.info("环境分析器初始化完成")
    
    def start(self):
        """启动环境分析"""
        if self.running:
            logger.warning("环境分析器已在运行")
            return
        
        logger.info("启动环境分析器...")
        self.running = True
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("环境分析器已启动")
    
    def stop(self):
        """停止环境分析"""
        if not self.running:
            return
        
        logger.info("正在停止环境分析器...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'analysis_thread'):
            self.analysis_thread.join(timeout=1.0)
        
        logger.info("环境分析器已停止")
    
    def update_data(self, data_type, value):
        """
        更新特定类型的环境数据
        
        Args:
            data_type: 数据类型 (brightness, noise_level, motion_level, room_activity)
            value: 数据值 (0-1)
        """
        if data_type == 'brightness':
            self.brightness = value
        elif data_type == 'noise_level':
            self.noise_level = value
        elif data_type == 'motion_level':
            self.motion_level = value
        elif data_type == 'room_activity':
            self.room_activity = value
        
        # 更新历史数据
        if data_type in self.history:
            self.history[data_type].append(value)
            # 保持历史数据长度
            if len(self.history[data_type]) > self.max_history:
                self.history[data_type].pop(0)
    
    def get_analysis_results(self):
        """获取分析结果"""
        # 更新时间信息
        now = datetime.now()
        hour = now.hour
        
        # 根据时间确定时段
        if 5 <= hour < 12:
            time_of_day = "上午"
        elif 12 <= hour < 18:
            time_of_day = "下午"
        elif 18 <= hour < 22:
            time_of_day = "晚上"
        else:
            time_of_day = "夜间"
        
        # 确定环境类型
        if self.noise_level < 0.2 and self.motion_level < 0.2:
            environment_type = "安静环境"
        elif self.noise_level > 0.6 or self.motion_level > 0.6:
            environment_type = "嘈杂环境"
        else:
            environment_type = "常规环境"
        
        # 计算变化率
        changes = {}
        for key in self.history:
            if len(self.history[key]) > 5:  # 至少需要5个点来计算
                changes[key] = self._calculate_change_rate(self.history[key])
            else:
                changes[key] = 0.0
        
        return {
            'brightness': self.brightness,
            'noise_level': self.noise_level,
            'motion_level': self.motion_level,
            'room_activity': self.room_activity,
            'time_of_day': time_of_day,
            'environment_type': environment_type,
            'changes': changes,
            'timestamp': now.isoformat()
        }
    
    def _analysis_loop(self):
        """环境分析循环"""
        while self.running:
            try:
                # 计算综合房间活动水平
                self.room_activity = 0.5 * self.motion_level + 0.3 * self.noise_level + 0.2 * self.brightness
                
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
                
                # 等待下一个更新周期
                time.sleep(self.update_interval)
                
            except Exception as e:
                if self.running:  # 只在运行时记录错误
                    logger.error(f"环境分析错误: {str(e)}")
                time.sleep(0.1)
    
    def _calculate_change_rate(self, data_list):
        """计算变化率"""
        if len(data_list) < 2:
            return 0.0
        
        # 使用线性回归斜率估计变化率
        x = np.arange(len(data_list))
        y = np.array(data_list)
        
        # 计算斜率
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        # 标准化到-1到1范围
        max_possible_slope = 1.0 / len(data_list)
        normalized_slope = np.clip(slope / max_possible_slope, -1.0, 1.0)
        
        return float(normalized_slope)
