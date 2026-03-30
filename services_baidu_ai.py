# services/baidu_ai.py - 百度AI接口封装
import requests
import base64
import json
import time
from datetime import datetime, timedelta
from flask import current_app
from utils.logger import get_logger

logger = get_logger(__name__)

class BaiduAIService:
    """百度智能云AI服务封装，含access_token缓存管理"""
    
    _token_cache = {}  # 类级别token缓存 {api_key: (token, expire_time)}
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or current_app.config.get('BAIDU_API_KEY')
        self.secret_key = secret_key or current_app.config.get('BAIDU_SECRET_KEY')
        self.token_url = 'https://aip.baidubce.com/oauth/2.0/token'
        
    def get_access_token(self) -> str:
        """获取百度API access_token，带缓存机制"""
        cache_key = self.api_key
        now = datetime.now()
        
        # 检查缓存是否有效
        if cache_key in self._token_cache:
            token, expire_time = self._token_cache[cache_key]
            if now < expire_time:
                return token
        
        # 请求新token
        try:
            params = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.secret_key
            }
            response = requests.get(self.token_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' not in data:
                raise ValueError(f"获取token失败: {data}")
            
            token = data['access_token']
            expire_seconds = data.get('expires_in', 2592000)  # 默认30天
            expire_time = now + timedelta(seconds=expire_seconds - 86400)  # 提前1天刷新
            
            self._token_cache[cache_key] = (token, expire_time)
            logger.info(f"百度API token获取成功，有效期至 {expire_time}")
            return token
            
        except Exception as e:
            logger.error(f"获取百度API token失败: {e}")
            raise
    
    def _image_to_base64(self, image_path: str) -> str:
        """图像文件转base64编码"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _image_bytes_to_base64(self, image_bytes: bytes) -> str:
        """图像bytes转base64编码"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def general_image_classify(self, image_path: str = None, image_bytes: bytes = None) -> dict:
        """
        通用物体和场景识别（高级版）
        接口文档: https://cloud.baidu.com/doc/IMAGERECOGNITION/s/Nk3bcxdux
        返回: 分类结果列表，含关键词、置信度
        """
        try:
            token = self.get_access_token()
            url = f'https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general?access_token={token}'
            
            if image_path:
                image_data = self._image_to_base64(image_path)
            elif image_bytes:
                image_data = self._image_bytes_to_base64(image_bytes)
            else:
                raise ValueError("image_path 或 image_bytes 至少提供一个")
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'image': image_data, 'baike_num': 0}
            
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'error_code' in result:
                logger.error(f"百度API错误 [{result.get('error_code')}]: {result.get('error_msg')}")
                return {'success': False, 'error': result.get('error_msg'), 'raw': result}
            
            logger.info(f"图像分类成功，识别到 {len(result.get('result', []))} 个标签")
            return {'success': True, 'result': result.get('result', []), 'raw': result}
            
        except Exception as e:
            logger.error(f"图像分类API调用失败: {e}")
            return {'success': False, 'error': str(e), 'result': []}
    
    def image_quality_enhance(self, image_path: str = None, image_bytes: bytes = None) -> dict:
        """
        图像清晰度增强（预处理用）
        接口: /rest/2.0/image-process/v1/image_definition_enhance
        """
        try:
            token = self.get_access_token()
            url = f'https://aip.baidubce.com/rest/2.0/image-process/v1/image_definition_enhance?access_token={token}'
            
            if image_path:
                image_data = self._image_to_base64(image_path)
            elif image_bytes:
                image_data = self._image_bytes_to_base64(image_bytes)
            else:
                raise ValueError("需要提供图像数据")
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'image': image_data}
            
            response = requests.post(url, data=data, headers=headers, timeout=30)
            result = response.json()
            
            if 'image' in result:
                enhanced_bytes = base64.b64decode(result['image'])
                return {'success': True, 'enhanced_image': enhanced_bytes}
            
            return {'success': False, 'error': result.get('error_msg', '增强失败')}
            
        except Exception as e:
            logger.error(f"图像增强失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def body_attribute_detect(self, image_path: str = None, image_bytes: bytes = None) -> dict:
        """
        人体属性识别（辅助判断姿势/伤口区域可见性）
        接口: /rest/2.0/image-classify/v1/body_attr
        """
        try:
            token = self.get_access_token()
            url = f'https://aip.baidubce.com/rest/2.0/image-classify/v1/body_attr?access_token={token}'
            
            if image_path:
                image_data = self._image_to_base64(image_path)
            elif image_bytes:
                image_data = self._image_bytes_to_base64(image_bytes)
            else:
                raise ValueError("需要提供图像数据")
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'image': image_data}
            
            response = requests.post(url, data=data, headers=headers, timeout=30)
            result = response.json()
            
            return {
                'success': 'person_num' in result,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"人体属性识别失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_image_safe(self, image_path: str = None, image_bytes: bytes = None) -> dict:
        """
        图像内容安全检测（确保上传图像合规）
        接口: /rest/2.0/solution/v1/img_censor/v2/user_defined
        """
        try:
            token = self.get_access_token()
            url = f'https://aip.baidubce.com/rest/2.0/solution/v1/img_censor/v2/user_defined?access_token={token}'
            
            if image_path:
                image_data = self._image_to_base64(image_path)
            elif image_bytes:
                image_data = self._image_bytes_to_base64(image_bytes)
            else:
                raise ValueError("需要提供图像数据")
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'image': image_data}
            
            response = requests.post(url, data=data, headers=headers, timeout=30)
            result = response.json()
            
            # conclusionType: 1=合规, 2=不合规, 3=疑似, 4=审核失败
            return {
                'success': True,
                'is_safe': result.get('conclusionType', 1) in [1, 3],
                'conclusion': result.get('conclusion', '合规'),
                'raw': result
            }
            
        except Exception as e:
            logger.error(f"图像安全检测失败: {e}")
            return {'success': False, 'is_safe': True, 'error': str(e)}