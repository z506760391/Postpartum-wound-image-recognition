import io
import os
import uuid
import hashlib
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图像处理功能受限")

# 魔术字节签名
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89\x50\x4e\x47': 'png',
    b'\x42\x4d': 'bmp',
    b'\x52\x49\x46\x46': 'webp',
}

MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_DIMENSION = 1920


class ImageProcessor:
    """图像预处理工具类"""

    def preprocess(self, image_path: str) -> bytes:
        """
        图像预处理：修正EXIF方向，调整尺寸，转换为JPEG字节
        
        Args:
            image_path: 图像文件路径
        Returns:
            JPEG格式的图像字节数据
        """
        if not PIL_AVAILABLE:
            with open(image_path, 'rb') as f:
                return f.read()

        try:
            img = Image.open(image_path)

            # 修正EXIF方向
            img = self._fix_exif_orientation(img)

            # 转换为RGB（处理RGBA、P等模式）
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 按比例缩放，不超过MAX_DIMENSION
            w, h = img.size
            if w > MAX_DIMENSION or h > MAX_DIMENSION:
                ratio = min(MAX_DIMENSION / w, MAX_DIMENSION / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=75, optimize=True)
            return buf.getvalue()

        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            with open(image_path, 'rb') as f:
                return f.read()

    def _fix_exif_orientation(self, img):
        """根据EXIF信息修正图像方向"""
        if not PIL_AVAILABLE:
            return img
        try:
            exif = img._getexif()
            if exif is None:
                return img
            orientation_key = next(
                (k for k, v in ExifTags.TAGS.items() if v == 'Orientation'), None
            )
            if orientation_key is None or orientation_key not in exif:
                return img
            orientation = exif[orientation_key]
            rotations = {3: 180, 6: 270, 8: 90}
            if orientation in rotations:
                img = img.rotate(rotations[orientation], expand=True)
        except Exception:
            pass
        return img

    def validate_image(self, file) -> tuple:
        """
        通过魔术字节验证图像合法性及大小
        
        Args:
            file: FileStorage 对象（Flask上传文件）
        Returns:
            (is_valid: bool, error_message: str)
        """
        try:
            header = file.read(8)
            file.seek(0)

            # 检查魔术字节
            matched = False
            for magic, fmt in MAGIC_BYTES.items():
                if header[:len(magic)] == magic:
                    matched = True
                    break
            if not matched:
                return False, "不支持的图像格式，请上传 JPEG/PNG/BMP/WEBP 图像"

            # 检查文件大小
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            if size > MAX_IMAGE_SIZE:
                return False, f"图像文件超过20MB限制（当前{size // 1024 // 1024}MB）"

            return True, ""
        except Exception as e:
            logger.error(f"图像验证失败: {e}")
            return False, f"图像验证出错: {e}"

    def save_upload(self, file, upload_folder: str, patient_id: int) -> str:
        """
        保存上传的图像文件，使用UUID文件名，按日期组织子目录
        
        Args:
            file: FileStorage 对象
            upload_folder: 上传根目录
            patient_id: 产妇ID
        Returns:
            保存后的相对文件路径
        """
        today = datetime.now().strftime('%Y%m%d')
        sub_dir = os.path.join(upload_folder, f'patient_{patient_id}', today)
        os.makedirs(sub_dir, exist_ok=True)

        ext = 'jpg'
        if file.filename:
            orig_ext = file.filename.rsplit('.', 1)[-1].lower()
            if orig_ext in ('jpg', 'jpeg', 'png', 'bmp', 'webp'):
                ext = orig_ext

        filename = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(sub_dir, filename)
        file.save(save_path)
        logger.info(f"图像已保存: {save_path}")
        return save_path

    def compute_hash(self, image_path: str) -> str:
        """
        计算图像MD5哈希值
        
        Args:
            image_path: 图像文件路径
        Returns:
            MD5哈希字符串
        """
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"计算哈希失败: {e}")
            return ''
