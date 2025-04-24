#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频分析器模块
负责捕获和分析音频流，检测音量、音调和环境声音特征
"""

import time
import logging
import threading
import numpy as np
import pyaudio
import librosa
import queue
from collections import deque

logger = logging.getLogger("MoodSense.AudioAnalyzer")

class AudioAnalyzer:
    """音频分析器类，负责音频捕获和分析"""
    
    def __init__(self, 
                 rate=44100, 
                 channels=1, 
                 chunk_size=1024, 
                 format=pyaudio.paFloat32,
                 buffer_seconds=5):
        """
        初始化音频分析器
        
        Args:
            rate: 采样率，默认44.1kHz
            channels: 通道数，默认1（单声道）
            chunk_size: 每次读取的帧数，默认1024
            format: 音频格式，默认为Float32
            buffer_seconds: 音频缓冲区大小（秒）
        """
        self.rate = rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = format
        self.buffer_size = int(buffer_seconds * rate / chunk_size)
        
        self.audio = None
        self.stream = None
        self.running = False
        
        # 音频缓冲区
        self.audio_buffer = deque(maxlen=self.buffer_size)
        self.audio_queue = queue.Queue(maxsize=100)
        self.result_queue = queue.Queue(maxsize=10)
        
        # 分析结果
        self.volume = 0.0
        self.is_speaking = False
        self.pitch = 0.0
        self.spectral_centroid = 0.0
        self.noise_level = 0.0
        self.frequency_distribution = None
        
        logger.info("音频分析器初始化完成")
    
    def start(self):
        """启动音频分析"""
        if self.running:
            logger.warning("音频分析器已在运行")
            return
        
        logger.info("启动音频分析器...")
        self.running = True
        
        # 初始化PyAudio
        self.audio = pyaudio.PyAudio()
        
        # 打开音频流
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("音频分析器已启动")
    
    def stop(self):
        """停止音频分析"""
        if not self.running:
            return
        
        logger.info("正在停止音频分析器...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'analysis_thread'):
            self.analysis_thread.join(timeout=1.0)
        
        # 关闭音频流
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # 终止PyAudio
        if self.audio is not None:
            self.audio.terminate()
            self.audio = None
        
        logger.info("音频分析器已停止")
    
    def get_analysis_results(self):
        """获取分析结果"""
        return {
            'volume': self.volume,
            'is_speaking': self.is_speaking,
            'pitch': self.pitch,
            'spectral_centroid': self.spectral_centroid,
            'noise_level': self.noise_level
        }
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频流回调函数"""
        # 将二进制数据转换为numpy数组
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        # 如果队列已满，移除最旧的数据
        if self.audio_queue.full():
            try:
                self.audio_queue.get_nowait()
            except:
                pass
        
        # 放入新数据
        try:
            self.audio_queue.put(audio_data, block=False)
        except:
            pass
        
        return (in_data, pyaudio.paContinue)
    
    def _analysis_loop(self):
        """音频分析循环"""
        while self.running:
            try:
                # 获取音频数据
                audio_data = self.audio_queue.get(timeout=1.0)
                
                # 添加到缓冲区
                self.audio_buffer.append(audio_data)
                
                # 只有当缓冲区达到一定大小时才进行分析
                if len(self.audio_buffer) >= self.buffer_size / 2:
                    # 合并缓冲区数据
                    buffer_data = np.concatenate(list(self.audio_buffer))
                    
                    # 分析音量
                    self.volume = self._analyze_volume(buffer_data)
                    
                    # 判断是否有人说话
                    self.is_speaking = self.volume > 0.05  # 阈值可调整
                    
                    # 如果音量足够大，分析其他特征
                    if self.is_speaking:
                        # 分析音高
                        self.pitch = self._analyze_pitch(buffer_data)
                        
                        # 分析光谱质心
                        self.spectral_centroid = self._analyze_spectral_centroid(buffer_data)
                    
                    # 分析噪音水平
                    self.noise_level = self._analyze_noise_level(buffer_data)
                    
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
                
            except queue.Empty:
                # 队列为空，继续
                continue
            except Exception as e:
                if self.running:  # 只在运行时记录错误
                    logger.error(f"音频分析错误: {str(e)}")
                time.sleep(0.1)
    
    def _analyze_volume(self, audio_data):
        """分析音量水平 (RMS)"""
        # 计算RMS并标准化到0-1范围
        rms = np.sqrt(np.mean(np.square(audio_data)))
        # 应用非线性映射使其更接近人类感知
        normalized_rms = np.tanh(3 * rms)
        return float(normalized_rms)
    
    def _analyze_pitch(self, audio_data):
        """分析音高 (使用librosa)"""
        try:
            # 计算基频
            pitches, magnitudes = librosa.piptrack(
                y=audio_data, 
                sr=self.rate,
                n_fft=2048,
                hop_length=self.chunk_size // 4,
                fmin=50,
                fmax=1000
            )
            
            # 找到每帧中幅度最大的pitch
            pitch = 0.0
            for i in range(magnitudes.shape[1]):
                index = magnitudes[:, i].argmax()
                if magnitudes[index, i] > 0:  # 确保有足够的信号
                    pitch = pitches[index, i]
                    break
            
            return float(pitch)
        except:
            return 0.0
    
    def _analyze_spectral_centroid(self, audio_data):
        """分析光谱质心 (使用librosa)"""
        try:
            centroid = librosa.feature.spectral_centroid(
                y=audio_data, 
                sr=self.rate,
                n_fft=2048,
                hop_length=self.chunk_size
            )
            
            # 取平均值
            return float(np.mean(centroid))
        except:
            return 0.0
    
    def _analyze_noise_level(self, audio_data):
        """估计环境噪音水平"""
        # 使用低通滤波器分离背景噪音
        try:
            # 计算短时傅里叶变换
            S = np.abs(librosa.stft(audio_data, n_fft=2048, hop_length=self.chunk_size))
            
            # 计算频谱的中值作为噪音估计
            noise_estimate = np.median(S, axis=1)
            
            # 将噪音水平标准化到0-1范围
            noise_level = np.mean(noise_estimate) / np.max(S)
            return float(noise_level)
        except:
            return 0.0
    
    def _compute_frequency_distribution(self, audio_data):
        """计算频率分布"""
        try:
            # 计算FFT
            n_fft = 2048
            fft = np.abs(np.fft.rfft(audio_data, n=n_fft))
            
            # 生成频率刻度
            freqs = np.fft.rfftfreq(n_fft, 1/self.rate)
            
            # 合并到频带
            n_bands = 10
            bands = np.logspace(np.log10(20), np.log10(20000), n_bands+1)
            band_energies = np.zeros(n_bands)
            
            for i in range(n_bands):
                band_mask = (freqs >= bands[i]) & (freqs < bands[i+1])
                band_energies[i] = np.sum(fft[band_mask]) if np.any(band_mask) else 0
            
            # 归一化
            if np.sum(band_energies) > 0:
                band_energies = band_energies / np.sum(band_energies)
            
            return band_energies.tolist()
        except:
            return [0.0] * 10
