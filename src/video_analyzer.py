#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频分析器模块
负责从摄像头捕获视频，分析视频内容，识别人脸和表情
"""

import os
import time
import logging
import threading
import base64
from io import BytesIO
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("MoodSense.VideoAnalyzer")

class VideoAnalyzer:
    """
    视频分析器类，负责从摄像头捕获视频帧并进行分析
    
    功能：
    1. 捕获摄像头视频流
    2. 检测人脸和面部表情
    3. 分析视频亮度和运动水平
    4. 提供帧数据给仪表盘展示
    """
    
    def __init__(self, camera_id=0, frame_width=640, frame_height=480, fps=15):
        """
        初始化视频分析器
        
        Args:
            camera_id: 摄像头ID，默认为0（第一个摄像头）
            frame_width: 帧宽度
            frame_height: 帧高度
            fps: 每秒帧数
        """
        self.camera_id = camera_id
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps
        self.running = False
        
        # 存储最近的帧和分析结果
        self.last_frame = None
        self.last_gray_frame = None
        self.previous_gray_frame = None
        self.face_detected = False
        self.face_location = None
        self.brightness = 0.0
        self.motion_level = 0.0
        
        # 用于人脸检测的级联分类器
        try:
            # 使用 OpenCV 预训练的人脸检测器
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            logger.info(f"加载人脸检测模型: {face_cascade_path}")
        except Exception as e:
            logger.error(f"无法加载人脸检测模型: {e}")
            self.face_cascade = None
        
        # 视频捕获对象
        self.cap = None
        
        # 线程锁，保护共享数据
        self.lock = threading.Lock()
        
        # 视频分析线程
        self.capture_thread = None
        
        logger.info("视频分析器初始化完成")
    
    def start(self):
        """
        启动视频分析器，开始捕获和分析视频
        """
        if self.running:
            logger.warning("视频分析器已在运行")
            return
        
        logger.info("启动视频分析器...")
        self.running = True
        
        # 在单独的线程中启动视频捕获
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info("视频分析器已启动")
    
    def stop(self):
        """
        停止视频分析器
        """
        if not self.running:
            return
        
        logger.info("正在停止视频分析器...")
        self.running = False
        
        # 等待线程结束
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        
        # 释放摄像头资源
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
        
        logger.info("视频分析器已停止")
    
    def _capture_loop(self):
        """
        视频捕获和分析循环
        """
        logger.info("开始视频捕获循环")
        
        # 尝试打开摄像头
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 检查摄像头是否成功打开
            if not self.cap.isOpened():
                logger.error(f"无法打开摄像头ID {self.camera_id}")
                self.running = False
                return
            
            logger.info(f"成功打开摄像头 ID {self.camera_id}")
            
            # 初始化时间追踪
            frame_count = 0
            start_time = time.time()
            
            # 主循环
            while self.running:
                # 读取一帧
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    logger.warning("无法读取视频帧")
                    time.sleep(0.1)
                    continue
                
                # 更新帧计数
                frame_count += 1
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # 每秒计算一次FPS
                if elapsed_time > 1.0:
                    fps = frame_count / elapsed_time
                    logger.debug(f"当前FPS: {fps:.2f}")
                    frame_count = 0
                    start_time = current_time
                
                # 处理帧
                with self.lock:
                    # 保存原始帧
                    self.last_frame = frame.copy()
                    
                    # 转换为灰度图用于分析
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # 保存上一帧和当前帧用于运动检测
                    if self.last_gray_frame is not None:
                        self.previous_gray_frame = self.last_gray_frame.copy()
                    self.last_gray_frame = gray_frame.copy()
                    
                    # 分析亮度
                    self.brightness = self._analyze_brightness(gray_frame)
                    
                    # 分析运动
                    if self.previous_gray_frame is not None:
                        self.motion_level = self._analyze_motion(self.previous_gray_frame, gray_frame)
                    
                    # 检测人脸
                    self._detect_faces(frame, gray_frame)
                
                # 帧率控制，避免CPU使用率过高
                time.sleep(max(0, 1.0/self.fps - (time.time() - current_time)))
                
        except Exception as e:
            logger.error(f"视频捕获过程中出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 确保资源被释放
            if self.cap and self.cap.isOpened():
                self.cap.release()
                self.cap = None
            
            logger.info("视频捕获循环已结束")
    
    def _analyze_brightness(self, gray_frame):
        """
        分析帧的亮度水平
        
        Args:
            gray_frame: 灰度图像帧
            
        Returns:
            亮度值 (0.0-1.0)
        """
        # 计算平均像素值并归一化到 0-1 范围
        mean_brightness = np.mean(gray_frame) / 255.0
        return float(mean_brightness)
    
    def _analyze_motion(self, prev_frame, curr_frame):
        """
        分析两帧之间的运动水平
        
        Args:
            prev_frame: 前一帧(灰度图)
            curr_frame: 当前帧(灰度图)
            
        Returns:
            运动水平 (0.0-1.0)
        """
        # 使用帧差法检测运动
        frame_diff = cv2.absdiff(prev_frame, curr_frame)
        motion_score = np.mean(frame_diff) / 255.0
        
        # 应用平滑因子
        return float(min(1.0, motion_score * 5.0))  # 放大效果并限制最大值为1.0
    
    def _detect_faces(self, frame, gray_frame):
        """
        检测帧中的人脸
        
        Args:
            frame: 原始彩色帧
            gray_frame: 灰度图帧
        """
        if self.face_cascade is None:
            self.face_detected = False
            return
        
        # 使用Haar级联分类器检测人脸
        faces = self.face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        if len(faces) > 0:
            # 保存最大的人脸位置
            self.face_detected = True
            # 找出最大的人脸
            max_face = max(faces, key=lambda f: f[2] * f[3])
            self.face_location = max_face
            
            # 在帧上标记人脸(可选)
            x, y, w, h = max_face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        else:
            self.face_detected = False
            self.face_location = None
    
    def get_analysis_results(self):
        """
        获取最新的视频分析结果
        
        Returns:
            包含分析结果和原始帧的字典
        """
        with self.lock:
            results = {
                'timestamp': time.time(),
                'brightness': self.brightness,
                'motion_level': self.motion_level,
                'face_detected': self.face_detected,
            }
            
            # 如果有人脸，添加人脸位置信息
            if self.face_detected and self.face_location is not None:
                x, y, w, h = self.face_location
                results['face_location'] = {
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h)
                }
            
            # 添加当前帧的base64编码(优化图像大小)
            if self.last_frame is not None:
                # 调整帧大小，减小数据量
                small_frame = cv2.resize(self.last_frame, (320, 240))
                
                # 转换为JPEG格式并编码为base64
                _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                jpeg_bytes = buffer.tobytes()
                base64_frame = base64.b64encode(jpeg_bytes).decode('utf-8')
                
                # 将其添加到结果中
                results['frame_data'] = base64_frame
            
            return results
