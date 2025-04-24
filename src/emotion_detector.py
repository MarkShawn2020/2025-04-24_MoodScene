#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
情绪识别器模块
负责分析用户的情绪状态，基于面部表情、语音和行为模式
"""

import time
import logging
import threading
import numpy as np
from queue import Queue
from collections import deque
import cv2
from deepface import DeepFace

logger = logging.getLogger("MoodSense.EmotionDetector")

class EmotionDetector:
    """情绪识别器类，负责分析用户情绪"""
    
    def __init__(self, update_interval=1.0, emotion_memory=10):
        """
        初始化情绪识别器
        
        Args:
            update_interval: 更新间隔（秒）
            emotion_memory: 情绪记忆长度（用于平滑情绪变化）
        """
        self.update_interval = update_interval
        self.emotion_memory_size = emotion_memory
        self.running = False
        self.result_queue = Queue(maxsize=10)
        
        # 情绪数据
        self.current_emotion = "neutral"  # 当前情绪
        self.emotion_confidence = 0.0     # 情绪置信度
        self.emotion_intensity = 0.0      # 情绪强度
        self.valence = 0.0                # 情绪效价 (-1到1，负面到正面)
        self.arousal = 0.0                # 情绪唤醒度 (0到1，低到高)
        
        # 情绪历史记录，用于平滑结果
        self.emotion_history = deque(maxlen=emotion_memory)
        self.valence_history = deque(maxlen=emotion_memory)
        self.arousal_history = deque(maxlen=emotion_memory)
        
        # 情绪模型
        self.emotion_categories = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
        
        # 情绪效价和唤醒度映射
        self.emotion_mappings = {
            "angry":    {"valence": -0.8, "arousal": 0.8},
            "disgust":  {"valence": -0.6, "arousal": 0.4},
            "fear":     {"valence": -0.7, "arousal": 0.7},
            "happy":    {"valence": 0.8, "arousal": 0.5},
            "sad":      {"valence": -0.6, "arousal": 0.2},
            "surprise": {"valence": 0.4, "arousal": 0.8},
            "neutral":  {"valence": 0.0, "arousal": 0.0}
        }
        
        # 多模态输入
        self.face_emotion = "neutral"      # 从面部表情识别的情绪
        self.voice_emotion = "neutral"     # 从语音识别的情绪
        self.behavior_emotion = "neutral"  # 从行为模式识别的情绪
        
        logger.info("情绪识别器初始化完成")
    
    def start(self):
        """启动情绪识别"""
        if self.running:
            logger.warning("情绪识别器已在运行")
            return
        
        logger.info("启动情绪识别器...")
        self.running = True
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("情绪识别器已启动")
    
    def stop(self):
        """停止情绪识别"""
        if not self.running:
            return
        
        logger.info("正在停止情绪识别器...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'analysis_thread'):
            self.analysis_thread.join(timeout=1.0)
        
        logger.info("情绪识别器已停止")
    
    def update_face_emotion(self, frame):
        """
        更新基于面部表情的情绪
        
        Args:
            frame: 视频帧
        """
        try:
            # 使用DeepFace分析情绪
            result = DeepFace.analyze(
                img_path=frame, 
                actions=['emotion'],
                enforce_detection=False,
                silent=True
            )
            
            # 提取情绪信息
            emotions = result[0]['emotion']
            dominant_emotion = result[0]['dominant_emotion']
            
            # 更新情绪
            self.face_emotion = dominant_emotion
            
            # 记录情绪强度
            confidence = emotions[dominant_emotion] / 100.0  # 转换为0-1范围
            
            # 更新效价和唤醒度
            valence = 0.0
            arousal = 0.0
            
            for emotion, score in emotions.items():
                # 将分数转换为0-1范围
                normalized_score = score / 100.0
                
                # 只考虑概率大于5%的情绪
                if normalized_score > 0.05 and emotion in self.emotion_mappings:
                    valence += normalized_score * self.emotion_mappings[emotion]["valence"]
                    arousal += normalized_score * self.emotion_mappings[emotion]["arousal"]
            
            # 融合情绪结果
            self._integrate_emotions("face", dominant_emotion, confidence, valence, arousal)
            
            return dominant_emotion
        except Exception as e:
            logger.debug(f"面部情绪检测错误: {str(e)}")
            return None
    
    def update_voice_emotion(self, audio_features):
        """
        更新基于语音的情绪
        
        Args:
            audio_features: 语音特征字典，包含音量、音高等
        """
        try:
            # 简单启发式规则来估计语音情绪
            volume = audio_features.get('volume', 0)
            pitch = audio_features.get('pitch', 0)
            is_speaking = audio_features.get('is_speaking', False)
            
            # 默认为中性
            dominant_emotion = "neutral"
            confidence = 0.5
            valence = 0.0
            arousal = 0.0
            
            # 只有在说话时才分析情绪
            if is_speaking:
                # 大声说话 + 高音调 = 可能兴奋或生气
                if volume > 0.7 and pitch > 200:
                    if pitch > 300:  # 非常高的音调通常表示惊讶
                        dominant_emotion = "surprise"
                        valence = 0.3
                        arousal = 0.8
                    else:  # 否则可能是生气
                        dominant_emotion = "angry"
                        valence = -0.8
                        arousal = 0.8
                    confidence = min(0.7, volume)
                
                # 大声说话 + 中等音调 = 可能开心
                elif volume > 0.6 and 150 < pitch < 250:
                    dominant_emotion = "happy"
                    valence = 0.7
                    arousal = 0.6
                    confidence = min(0.65, volume)
                
                # 小声说话 + 低音调 = 可能悲伤
                elif volume < 0.3 and pitch < 150:
                    dominant_emotion = "sad"
                    valence = -0.6
                    arousal = 0.2
                    confidence = 0.6
                
                # 中等音量 + 稳定音调 = 中性
                else:
                    dominant_emotion = "neutral"
                    valence = 0.0
                    arousal = 0.3
                    confidence = 0.5
            
            # 更新语音情绪
            self.voice_emotion = dominant_emotion
            
            # 融合情绪结果
            self._integrate_emotions("voice", dominant_emotion, confidence, valence, arousal)
            
            return dominant_emotion
        except Exception as e:
            logger.debug(f"语音情绪检测错误: {str(e)}")
            return None
    
    def update_behavior_emotion(self, motion_level, typing_speed, typing_errors, focus_level):
        """
        更新基于行为模式的情绪
        
        Args:
            motion_level: 运动水平 (0-1)
            typing_speed: 打字速度 (字符/分钟)
            typing_errors: 打字错误率 (0-1)
            focus_level: 专注水平 (0-1)
        """
        try:
            # 行为特征的权重
            weights = {
                "motion": 0.3,
                "typing_speed": 0.3,
                "typing_errors": 0.2,
                "focus": 0.2
            }
            
            # 默认为中性
            dominant_emotion = "neutral"
            confidence = 0.5
            valence = 0.0
            arousal = motion_level * 0.5  # 运动水平直接影响唤醒度
            
            # 剧烈运动 + 快速打字 + 低错误率 = 兴奋/开心
            if motion_level > 0.6 and typing_speed > 300 and typing_errors < 0.2:
                dominant_emotion = "happy"
                valence = 0.7
                confidence = 0.65
            
            # 剧烈运动 + 快速打字 + 高错误率 = 生气/焦虑
            elif motion_level > 0.6 and typing_speed > 300 and typing_errors > 0.3:
                dominant_emotion = "angry"
                valence = -0.6
                confidence = 0.6
            
            # 低运动 + 慢速打字 = 悲伤/疲惫
            elif motion_level < 0.2 and typing_speed < 150:
                dominant_emotion = "sad"
                valence = -0.4
                confidence = 0.55
            
            # 中等运动 + 专注度高 = 中性/专注
            elif 0.3 < motion_level < 0.5 and focus_level > 0.7:
                dominant_emotion = "neutral"
                valence = 0.2
                confidence = 0.7
            
            # 其他情况，根据运动和专注度加权计算
            else:
                # 积极指数
                positivity = focus_level * 0.6 - typing_errors * 0.4
                
                if positivity > 0.3:
                    dominant_emotion = "happy"
                    valence = positivity
                    confidence = 0.5
                elif positivity < -0.2:
                    dominant_emotion = "sad"
                    valence = positivity
                    confidence = 0.5
                else:
                    dominant_emotion = "neutral"
                    valence = positivity
                    confidence = 0.6
            
            # 更新行为情绪
            self.behavior_emotion = dominant_emotion
            
            # 融合情绪结果
            self._integrate_emotions("behavior", dominant_emotion, confidence, valence, arousal)
            
            return dominant_emotion
        except Exception as e:
            logger.debug(f"行为情绪检测错误: {str(e)}")
            return None
    
    def get_analysis_results(self):
        """获取情绪分析结果"""
        # 计算平均效价和唤醒度
        avg_valence = sum(self.valence_history) / len(self.valence_history) if self.valence_history else 0.0
        avg_arousal = sum(self.arousal_history) / len(self.arousal_history) if self.arousal_history else 0.0
        
        # 情绪标签计数
        emotion_counts = {}
        for emotion in self.emotion_history:
            if emotion in emotion_counts:
                emotion_counts[emotion] += 1
            else:
                emotion_counts[emotion] = 1
        
        # 找出最常见的情绪
        if emotion_counts:
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            emotion_confidence = emotion_counts[dominant_emotion] / len(self.emotion_history)
        else:
            dominant_emotion = "neutral"
            emotion_confidence = 0.0
        
        # 确定情绪强度基于唤醒度
        emotion_intensity = abs(avg_valence) * avg_arousal
        
        return {
            'emotion': dominant_emotion,
            'confidence': emotion_confidence,
            'intensity': emotion_intensity,
            'valence': avg_valence,
            'arousal': avg_arousal,
            'face_emotion': self.face_emotion,
            'voice_emotion': self.voice_emotion,
            'behavior_emotion': self.behavior_emotion,
            'emotion_distribution': emotion_counts
        }
    
    def _integrate_emotions(self, source, emotion, confidence, valence, arousal):
        """
        整合不同来源的情绪信息
        
        Args:
            source: 情绪来源 ('face', 'voice', 'behavior')
            emotion: 情绪标签
            confidence: 置信度 (0-1)
            valence: 效价 (-1到1)
            arousal: 唤醒度 (0-1)
        """
        # 基于置信度的权重
        if source == 'face':
            weight = 0.5 * confidence
        elif source == 'voice':
            weight = 0.3 * confidence
        elif source == 'behavior':
            weight = 0.2 * confidence
        else:
            weight = 0.0
        
        # 如果权重太小，不进行整合
        if weight < 0.1:
            return
        
        # 添加到历史记录
        self.emotion_history.append(emotion)
        self.valence_history.append(valence)
        self.arousal_history.append(arousal)
        
        # 更新当前情绪状态 (直接由get_analysis_results计算)
    
    def _analysis_loop(self):
        """情绪分析循环"""
        while self.running:
            try:
                # 获取分析结果
                result = self.get_analysis_results()
                
                # 更新当前情绪状态
                self.current_emotion = result['emotion']
                self.emotion_confidence = result['confidence']
                self.emotion_intensity = result['intensity']
                self.valence = result['valence']
                self.arousal = result['arousal']
                
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
                    logger.error(f"情绪分析错误: {str(e)}")
                time.sleep(0.1)
