#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频分析器模块
负责捕获和分析视频流，检测人脸、姿态和动作
"""

import cv2
import time
import logging
import numpy as np
import threading
import mediapipe as mp
from queue import Queue

logger = logging.getLogger("MoodSense.VideoAnalyzer")

class VideoAnalyzer:
    """视频分析器类，负责视频捕获和分析"""
    
    def __init__(self, camera_id=0, resolution=(640, 480), fps=30):
        """
        初始化视频分析器
        
        Args:
            camera_id: 摄像头ID，默认为0（第一个摄像头）
            resolution: 视频分辨率，默认为640x480
            fps: 帧率，默认为30fps
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.fps = fps
        self.cap = None
        self.running = False
        self.frame_queue = Queue(maxsize=10)
        self.result_queue = Queue(maxsize=10)
        
        # 初始化MediaPipe解决方案
        self.mp_face = mp.solutions.face_detection
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # 创建检测器
        self.face_detector = self.mp_face.FaceDetection(min_detection_confidence=0.5)
        self.pose_detector = self.mp_pose.Pose(min_detection_confidence=0.5)
        self.hands_detector = self.mp_hands.Hands(min_detection_confidence=0.5)
        
        # 亮度分析结果
        self.brightness = 0
        self.motion_level = 0
        self.last_frame = None
        self.face_detected = False
        self.face_location = None
        self.pose_landmarks = None
        self.hands_landmarks = None
        
        logger.info("视频分析器初始化完成")
    
    def start(self):
        """启动视频分析"""
        if self.running:
            logger.warning("视频分析器已在运行")
            return
        
        logger.info("启动视频分析器...")
        self.running = True
        
        # 初始化摄像头
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 检查摄像头是否成功打开
            if not self.cap.isOpened():
                logger.warning("无法打开摄像头，尝试打开虚拟摄像头")
                # 创建虚拟视频源 - 一个黑色背景
                self.using_virtual_camera = True
                self.last_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
            else:
                self.using_virtual_camera = False
        except Exception as e:
            logger.error(f"初始化摄像头时出错: {str(e)}")
            # 创建虚拟视频源
            self.using_virtual_camera = True
            self.last_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        
        # 启动视频捕获线程
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("视频分析器已启动")
    
    def stop(self):
        """停止视频分析"""
        if not self.running:
            return
        
        logger.info("正在停止视频分析器...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        if hasattr(self, 'analysis_thread'):
            self.analysis_thread.join(timeout=1.0)
        
        # 释放摄像头
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        logger.info("视频分析器已停止")
    
    def get_latest_frame(self):
        """获取最新的视频帧"""
        return self.last_frame
    
    def get_analysis_results(self):
        """获取分析结果"""
        return {
            'brightness': self.brightness,
            'motion_level': self.motion_level,
            'face_detected': self.face_detected,
            'face_location': self.face_location,
            'pose_landmarks': self.pose_landmarks,
            'hands_landmarks': self.hands_landmarks
        }
    
    def _capture_loop(self):
        """视频捕获循环"""
        frame_count = 0
        start_time = time.time()
        
        while self.running:
            if hasattr(self, 'using_virtual_camera') and self.using_virtual_camera:
                # 模拟虚拟摄像头 - 创建动态内容
                virtual_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
                
                # 添加一些动态内容（比如移动的圆形）
                current_time = time.time()
                radius = 30
                x = int(self.resolution[0]/2 + radius * np.sin(current_time))
                y = int(self.resolution[1]/2 + radius * np.cos(current_time))
                
                # 绘制圆形
                cv2.circle(virtual_frame, (x, y), 20, (0, 165, 255), -1)  # 橙色圆形
                
                # 添加文字
                cv2.putText(virtual_frame, "Virtual Camera Mode", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(virtual_frame, f"Time: {time.strftime('%H:%M:%S')}", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 存储帧
                self.last_frame = virtual_frame.copy()
                frame = virtual_frame
                ret = True
            else:
                # 正常摄像头模式
                ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("无法从摄像头读取帧，切换到虚拟摄像头模式")
                self.using_virtual_camera = True
                time.sleep(0.1)
                continue
            
            # 如果队列已满，移除最旧的帧
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            
            # 放入新帧
            try:
                self.frame_queue.put(frame, block=False)
            except:
                pass
            
            # 控制帧率
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed > 1:
                actual_fps = frame_count / elapsed
                frame_count = 0
                start_time = time.time()
                
                if abs(actual_fps - self.fps) > 5:
                    logger.debug(f"实际帧率: {actual_fps:.1f} fps")
    
    def _analysis_loop(self):
        """视频分析循环"""
        while self.running:
            try:
                # 获取帧
                frame = self.frame_queue.get(timeout=1.0)
                self.last_frame = frame.copy()
                
                # 分析亮度
                self.brightness = self._analyze_brightness(frame)
                
                # 分析运动
                self.motion_level = self._analyze_motion(frame)
                
                # 分析人脸
                self.face_detected, self.face_location = self._detect_face(frame)
                
                # 分析姿态
                self.pose_landmarks = self._detect_pose(frame)
                
                # 分析手势
                self.hands_landmarks = self._detect_hands(frame)
                
                # 如果结果队列已满，移除最旧的结果
                if self.result_queue.full():
                    try:
                        self.result_queue.get_nowait()
                    except:
                        pass
                
                # 放入新结果
                result = self.get_analysis_results()
                try:
                    self.result_queue.put(result, block=False)
                except:
                    pass
                
            except Exception as e:
                if self.running:  # 只在运行时记录错误
                    logger.error(f"视频分析错误: {str(e)}")
                time.sleep(0.1)
    
    def _analyze_brightness(self, frame):
        """分析帧的亮度水平"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) / 255.0  # 标准化到0-1范围
    
    def _analyze_motion(self, frame):
        """分析帧间运动水平"""
        if self.last_frame is None:
            return 0
        
        # 转换为灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
        
        # 计算帧差
        frame_diff = cv2.absdiff(gray, prev_gray)
        motion = np.mean(frame_diff) / 255.0  # 标准化到0-1范围
        
        return motion
    
    def _detect_face(self, frame):
        """检测人脸"""
        # 转换为RGB (MediaPipe需要RGB输入)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 检测人脸
        results = self.face_detector.process(rgb_frame)
        
        face_detected = False
        face_location = None
        
        if results.detections:
            face_detected = True
            # 获取第一个检测到的人脸的位置
            detection = results.detections[0]
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = frame.shape
            face_location = {
                'xmin': int(bboxC.xmin * iw),
                'ymin': int(bboxC.ymin * ih),
                'width': int(bboxC.width * iw),
                'height': int(bboxC.height * ih)
            }
        
        return face_detected, face_location
    
    def _detect_pose(self, frame):
        """检测姿态"""
        # 转换为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 检测姿态
        results = self.pose_detector.process(rgb_frame)
        
        landmarks = None
        if results.pose_landmarks:
            # 转换landmarks为字典
            landmarks = {}
            for i, landmark in enumerate(results.pose_landmarks.landmark):
                landmarks[f"landmark_{i}"] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
        
        return landmarks
    
    def _detect_hands(self, frame):
        """检测手势"""
        # 转换为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 检测手势
        results = self.hands_detector.process(rgb_frame)
        
        landmarks = None
        if results.multi_hand_landmarks:
            # 转换landmarks为字典
            landmarks = []
            for hand_landmarks in results.multi_hand_landmarks:
                hand_dict = {}
                for i, landmark in enumerate(hand_landmarks.landmark):
                    hand_dict[f"landmark_{i}"] = {
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    }
                landmarks.append(hand_dict)
        
        return landmarks
