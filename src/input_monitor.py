#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
输入监控模块
负责监控用户输入行为，如打字速度、鼠标移动等
"""

import time
import logging
import threading
from queue import Queue
from datetime import datetime
from collections import deque
import numpy as np
from pynput import keyboard, mouse
import pygetwindow as gw
import cv2
from PIL import ImageGrab

logger = logging.getLogger("MoodSense.InputMonitor")

class InputMonitor:
    """输入监控类，负责监控用户的输入行为"""
    
    def __init__(self, update_interval=1.0, typing_window=60):
        """
        初始化输入监控
        
        Args:
            update_interval: 更新间隔（秒）
            typing_window: 打字速度计算窗口（秒）
        """
        self.update_interval = update_interval
        self.typing_window = typing_window
        self.running = False
        self.result_queue = Queue(maxsize=10)
        
        # 输入数据
        self.keystroke_times = deque(maxlen=1000)  # 按键时间
        self.keystroke_chars = deque(maxlen=1000)  # 按键字符
        self.typing_speed = 0.0                    # 打字速度（字符/分钟）
        self.typing_errors = 0.0                   # 打字错误率
        self.backspace_rate = 0.0                  # 退格键使用率
        
        # 鼠标数据
        self.mouse_positions = deque(maxlen=1000)  # 鼠标位置
        self.mouse_clicks = deque(maxlen=100)      # 鼠标点击
        self.mouse_activity = 0.0                  # 鼠标活动水平
        self.click_frequency = 0.0                 # 点击频率
        
        # 窗口和屏幕数据
        self.active_window = None                  # 当前活动窗口
        self.window_switch_count = 0               # 窗口切换次数
        self.screen_content_changes = 0.0          # 屏幕内容变化率
        self.last_screenshot = None                # 上次屏幕截图
        
        # 计算专注度
        self.focus_level = 0.5                     # 专注水平（0-1）
        self.last_activity_time = time.time()      # 上次活动时间
        
        # 监听器
        self.keyboard_listener = None
        self.mouse_listener = None
        
        logger.info("输入监控器初始化完成")
    
    def start(self):
        """启动输入监控"""
        if self.running:
            logger.warning("输入监控器已在运行")
            return
        
        logger.info("启动输入监控器...")
        self.running = True
        
        # 启动键盘监听
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        
        # 启动鼠标监听
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("输入监控器已启动")
    
    def stop(self):
        """停止输入监控"""
        if not self.running:
            return
        
        logger.info("正在停止输入监控器...")
        self.running = False
        
        # 停止键盘监听
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        
        # 停止鼠标监听
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        # 等待线程结束
        if hasattr(self, 'analysis_thread'):
            self.analysis_thread.join(timeout=1.0)
        
        logger.info("输入监控器已停止")
    
    def get_analysis_results(self):
        """获取分析结果"""
        # 获取当前活动窗口
        try:
            active_window = gw.getActiveWindow()
            # 确保 active_window_title 是字符串，而不是方法对象
            active_window_title = str(active_window.title) if active_window else "未知"
        except Exception as e:
            logger.error(f"获取活动窗口出错: {e}")
            active_window_title = "未知"
        
        return {
            'typing_speed': self.typing_speed,
            'typing_errors': self.typing_errors,
            'backspace_rate': self.backspace_rate,
            'mouse_activity': self.mouse_activity,
            'click_frequency': self.click_frequency,
            'active_window': active_window_title,
            'window_switch_count': self.window_switch_count,
            'screen_content_changes': self.screen_content_changes,
            'focus_level': self.focus_level,
            'idle_time': time.time() - self.last_activity_time
        }
    
    def _on_key_press(self, key):
        """按键按下回调"""
        current_time = time.time()
        self.last_activity_time = current_time
        
        try:
            # 尝试将键转换为字符
            char = key.char
        except:
            # 特殊键
            if key == keyboard.Key.backspace:
                char = "[BACKSPACE]"
            elif key == keyboard.Key.space:
                char = " "
            elif key == keyboard.Key.enter:
                char = "[ENTER]"
            else:
                char = str(key)
        
        # 记录按键时间和字符
        self.keystroke_times.append(current_time)
        self.keystroke_chars.append(char)
    
    def _on_key_release(self, key):
        """按键释放回调"""
        # 仅用于检测退出条件
        if key == keyboard.Key.esc and not self.running:
            # 停止监听器
            return False
        return True
    
    def _on_mouse_move(self, x, y):
        """鼠标移动回调"""
        current_time = time.time()
        self.last_activity_time = current_time
        
        # 记录鼠标位置
        self.mouse_positions.append((current_time, x, y))
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击回调"""
        current_time = time.time()
        self.last_activity_time = current_time
        
        if pressed:
            # 记录鼠标点击
            self.mouse_clicks.append((current_time, x, y, button))
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚动回调"""
        current_time = time.time()
        self.last_activity_time = current_time
        
        # 可以在这里添加滚动事件处理
    
    def _calculate_typing_speed(self):
        """计算打字速度"""
        if len(self.keystroke_times) < 2:
            return 0.0, 0.0, 0.0  # 返回三元素元组：打字速度、错误率、退格率
        
        # 获取当前时间
        current_time = time.time()
        
        # 找出过去typing_window秒内的按键
        recent_times = [t for t in self.keystroke_times if current_time - t <= self.typing_window]
        
        # 安全地获取相应数量的字符
        try:
            if recent_times:
                # 确保不会取超过队列长度
                char_count = min(len(recent_times), len(self.keystroke_chars))
                recent_chars = list(self.keystroke_chars)[-char_count:] if char_count > 0 else []
            else:
                recent_chars = []        
        except Exception as e:
            logger.error(f"计算打字速度错误: {e}")
            recent_chars = []
        
        if not recent_times:
            return 0.0
        
        # 计算总字符数 (不包括特殊键)
        char_count = sum(1 for c in recent_chars if len(c) == 1)
        
        # 计算退格键数量
        backspace_count = sum(1 for c in recent_chars if c == "[BACKSPACE]")
        
        # 计算总时间（分钟）
        if len(recent_times) > 1:
            time_span = (recent_times[-1] - recent_times[0]) / 60.0
        else:
            time_span = self.typing_window / 60.0
        
        # 计算打字速度（字符/分钟）
        if time_span > 0:
            typing_speed = char_count / time_span
        else:
            typing_speed = 0.0
        
        # 计算退格率
        if char_count + backspace_count > 0:
            backspace_rate = backspace_count / (char_count + backspace_count)
        else:
            backspace_rate = 0.0
        
        # 简单的错误率估计
        typing_errors = backspace_rate
        
        return typing_speed, typing_errors, backspace_rate
    
    def _calculate_mouse_activity(self):
        """计算鼠标活动水平"""
        if len(self.mouse_positions) < 2:
            return 0.0, 0.0
        
        # 获取当前时间
        current_time = time.time()
        
        # 找出过去5秒内的鼠标位置
        recent_positions = [(t, x, y) for t, x, y in self.mouse_positions if current_time - t <= 5.0]
        
        if len(recent_positions) < 2:
            return 0.0, 0.0
        
        # 计算鼠标移动距离
        total_distance = 0.0
        for i in range(1, len(recent_positions)):
            _, x1, y1 = recent_positions[i-1]
            _, x2, y2 = recent_positions[i]
            distance = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            total_distance += distance
        
        # 标准化距离到0-1范围 (假设1000像素/秒是最大)
        mouse_activity = min(1.0, total_distance / 5000.0)
        
        # 计算点击频率 (每秒点击次数)
        recent_clicks = [t for t, _, _, _ in self.mouse_clicks if current_time - t <= 5.0]
        click_frequency = len(recent_clicks) / 5.0 if recent_clicks else 0.0
        
        return mouse_activity, click_frequency
    
    def _check_active_window(self):
        """检查当前活动窗口"""
        try:
            active_window = gw.getActiveWindow()
            
            if active_window is None:
                return None
            
            # 如果活动窗口改变，增加计数
            if self.active_window is not None and active_window.title != self.active_window:
                self.window_switch_count += 1
            
            # 更新当前活动窗口
            self.active_window = active_window.title
            
            return active_window.title
        except:
            return None
    
    def _capture_screen_changes(self):
        """捕获屏幕变化"""
        try:
            # 获取屏幕截图
            screenshot = ImageGrab.grab()
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            screenshot = cv2.resize(screenshot, (320, 180))  # 缩小以提高性能
            
            # 如果没有上一帧，保存当前帧并返回
            if self.last_screenshot is None:
                self.last_screenshot = screenshot
                return 0.0
            
            # 计算帧差
            frame_diff = cv2.absdiff(screenshot, self.last_screenshot)
            change_ratio = np.mean(frame_diff) / 255.0
            
            # 更新上一帧
            self.last_screenshot = screenshot
            
            return change_ratio
        except:
            return 0.0
    
    def _calculate_focus_level(self, typing_speed, mouse_activity, idle_time):
        """计算用户专注度"""
        # 空闲时间权重
        idle_weight = 0.5
        # 打字速度权重
        typing_weight = 0.3
        # 鼠标活动权重
        mouse_weight = 0.2
        
        # 归一化打字速度 (300字符/分钟为满分)
        norm_typing = min(1.0, typing_speed / 300.0)
        
        # 归一化空闲时间 (超过30秒视为不专注)
        if idle_time > 30.0:
            norm_idle = 0.0
        else:
            norm_idle = max(0.0, 1.0 - idle_time / 30.0)
        
        # 计算专注度
        focus = (
            idle_weight * norm_idle + 
            typing_weight * norm_typing + 
            mouse_weight * mouse_activity
        )
        
        # 应用平滑因子
        smoothing = 0.7  # 70%旧值，30%新值
        self.focus_level = smoothing * self.focus_level + (1 - smoothing) * focus
        
        return self.focus_level
    
    def _analysis_loop(self):
        """分析循环"""
        while self.running:
            try:
                # 计算打字速度和错误率
                typing_results = self._calculate_typing_speed()
                self.typing_speed, self.typing_errors, self.backspace_rate = typing_results
                
                # 计算鼠标活动水平
                mouse_results = self._calculate_mouse_activity()
                self.mouse_activity, self.click_frequency = mouse_results
                
                # 检查活动窗口
                self._check_active_window()
                
                # 捕获屏幕变化
                self.screen_content_changes = self._capture_screen_changes()
                
                # 计算空闲时间
                idle_time = time.time() - self.last_activity_time
                
                # 计算专注度
                self.focus_level = self._calculate_focus_level(
                    self.typing_speed, 
                    self.mouse_activity, 
                    idle_time
                )
                
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
                    logger.error(f"输入监控错误: {str(e)}")
                time.sleep(0.1)
