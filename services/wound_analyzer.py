# services/wound_analyzer.py - 伤口智能分析核心服务
import os
import json
import hashlib
import numpy as np
from datetime import datetime, date
from flask import current_app
from services.baidu_ai import BaiduAIService
from utils.image_processor import ImageProcessor
from utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────── 感染启发式默认阈值 ────────────────────────────
# 若 Flask 应用上下文不可用（如单元测试），使用以下默认值
_DEFAULT_RED_THRESHOLD = 0.15
_DEFAULT_YG_THRESHOLD = 0.08
_DEFAULT_SAT_THRESHOLD = 0.20
_DEFAULT_RISK_THRESHOLD = 0.45
_DEFAULT_W_RED = 0.40
_DEFAULT_W_YG = 0.40
_DEFAULT_W_SAT = 0.20

# 伤口特征关键词映射表（基于百度图像识别标签做语义映射）
WOUND_FEATURE_KEYWORDS = {
    # 炎症期特征
    'inflammation_keywords': [
        '红肿', '充血', '炎症', '红斑', '水肿', '肿胀',
        'redness', 'swelling', 'inflammation', 'edema'
    ],
    # 增生期特征
    'proliferation_keywords': [
        '肉芽', '愈合', '结痂', '新生', '组织', '收缩',
        'granulation', 'healing', 'scab', 'tissue'
    ],
    # 成熟期特征  
    'maturation_keywords': [
        '瘢痕', '愈合', '皮肤', '闭合', '平整',
        'scar', 'healed', 'skin', 'closed'
    ],
    # 异常特征
    'abnormal_keywords': [
        '渗出', '脓液', '化脓', '裂开', '坏死', '感染', '异常',
        '分泌物', '出血', 'discharge', 'pus', 'infection',
        'necrosis', 'dehiscence', 'bleeding'
    ],
    # 伤口类型
    'cesarean_keywords': ['剖腹', '腹部', '切口', '横切', '纵切', 'incision', 'abdomen'],
    'perineal_keywords': ['会阴', '外阴', '阴道', '撕裂', 'perineum', 'laceration']
}

# 异常类型中文映射
ANOMALY_TYPE_MAP = {
    'infection': '伤口感染',
    'dehiscence': '伤口裂开',
    'hematoma': '血肿',
    'seroma': '血清肿',
    'necrosis': '组织坏死',
    'excessive_discharge': '异常分泌物',
    'bleeding': '出血',
    'allergic_reaction': '过敏反应'
}


class WoundAnalyzer:
    """产后伤口智能分析器"""
    
    def __init__(self):
        self.baidu_ai = BaiduAIService()
        self.image_processor = ImageProcessor()
    
    def analyze(self, image_path: str, patient_info: dict) -> dict:
        """
        主分析流程：图像预处理 → AI识别 → 特征解析 → 结合患者信息综合评估
        
        Args:
            image_path: 图像文件路径
            patient_info: 产妇个人信息字典
        
        Returns:
            完整的分析结果字典
        """
        logger.info(f"开始分析图像: {image_path}")
        result = {
            'success': False,
            'wound_stage': 'unknown',
            'confidence_score': 0.0,
            'anomaly_detected': False,
            'anomaly_types': [],
            'urgency_level': 'normal',
            'feature_tags': [],
            'raw_api_result': None,
            'analysis_detail': {},
            'image_hash': self._compute_image_hash(image_path),
            'infection_risk_score': 0.0,
        }
        
        try:
            # 步骤1: 图像预处理
            processed_image_bytes = self.image_processor.preprocess(image_path)
            logger.info("图像预处理完成")

            # 步骤1b: 本地感染风险启发式评分（不依赖外部服务）
            infection_risk_score = self._compute_infection_risk_score(image_path)
            result['infection_risk_score'] = infection_risk_score
            
            # 步骤2: 调用百度图像分类API
            classify_result = self.baidu_ai.general_image_classify(image_bytes=processed_image_bytes)
            
            if not classify_result.get('success'):
                # 百度API失败时使用本地规则降级处理
                logger.warning("百度API调用失败，启用本地规则降级分析")
                return self._fallback_analysis(image_path, patient_info, result)
            
            api_tags = classify_result.get('result', [])
            result['raw_api_result'] = json.dumps(classify_result.get('raw', {}), ensure_ascii=False)
            result['feature_tags'] = [tag.get('keyword', '') for tag in api_tags[:10]]
            
            # 步骤3: 特征语义解析
            stage_scores = self._parse_stage_from_tags(api_tags)
            anomalies = self._detect_anomalies(api_tags)

            # 步骤3b: 融合本地感染风险评分
            anomalies, infection_risk_score = self._merge_infection_risk(
                anomalies, infection_risk_score
            )
            
            # 步骤4: 结合患者信息综合评估
            final_stage, confidence = self._integrate_patient_context(
                stage_scores, patient_info
            )
            
            # 步骤5: 确定紧急程度
            urgency = self._determine_urgency(anomalies, final_stage, patient_info)
            
            result.update({
                'success': True,
                'wound_stage': final_stage,
                'confidence_score': round(confidence, 3),
                'anomaly_detected': len(anomalies) > 0,
                'anomaly_types': anomalies,
                'urgency_level': urgency,
                'infection_risk_score': infection_risk_score,
                'analysis_detail': {
                    'stage_scores': stage_scores,
                    'days_postpartum': self._calc_days_postpartum(patient_info.get('delivery_date')),
                    'risk_factors': self._assess_risk_factors(patient_info),
                    'infection_risk_note': (
                        '感染风险评分为辅助参考，不能替代医生诊断。'
                        '如有疑虑请及时就医。'
                    )
                }
            })
            
            logger.info(f"分析完成: 阶段={final_stage}, 置信度={confidence:.3f}, 异常={anomalies}")
            return result
            
        except Exception as e:
            logger.error(f"伤口分析发生错误: {e}", exc_info=True)
            result['error'] = str(e)
            return result
    
    def _parse_stage_from_tags(self, api_tags: list) -> dict:
        """从百度API标签中解析伤口愈合阶段分数"""
        scores = {
            'inflammation': 0.0,
            'proliferation': 0.0,
            'maturation': 0.0,
            'abnormal': 0.0
        }
        
        for tag in api_tags:
            keyword = tag.get('keyword', '').lower()
            score = tag.get('score', 0.0)
            
            for kw in WOUND_FEATURE_KEYWORDS['inflammation_keywords']:
                if kw.lower() in keyword:
                    scores['inflammation'] += score * 0.8
                    break
            
            for kw in WOUND_FEATURE_KEYWORDS['proliferation_keywords']:
                if kw.lower() in keyword:
                    scores['proliferation'] += score * 0.8
                    break
            
            for kw in WOUND_FEATURE_KEYWORDS['maturation_keywords']:
                if kw.lower() in keyword:
                    scores['maturation'] += score * 0.8
                    break
            
            for kw in WOUND_FEATURE_KEYWORDS['abnormal_keywords']:
                if kw.lower() in keyword:
                    scores['abnormal'] += score * 1.2  # 异常权重加大
                    break
        
        # 归一化
        total = sum(scores.values()) or 1.0
        return {k: round(v / total, 3) for k, v in scores.items()}
    
    def _detect_anomalies(self, api_tags: list) -> list:
        """检测伤口异常类型"""
        detected = []
        keywords_str = ' '.join([tag.get('keyword', '').lower() for tag in api_tags])
        
        anomaly_checks = {
            'infection': ['感染', '化脓', '脓液', 'infection', 'pus', 'purulent'],
            'dehiscence': ['裂开', '开裂', 'dehiscence', 'wound opening'],
            'hematoma': ['血肿', '瘀血', 'hematoma', 'bruising'],
            'seroma': ['积液', '浆液', 'seroma', 'fluid'],
            'necrosis': ['坏死', '发黑', 'necrosis', 'necrotic'],
            'excessive_discharge': ['渗出', '分泌物', '流液', 'discharge', 'exudate'],
            'bleeding': ['出血', '渗血', 'bleeding', 'hemorrhage']
        }
        
        for anomaly_type, kw_list in anomaly_checks.items():
            for kw in kw_list:
                if kw in keywords_str:
                    detected.append(anomaly_type)
                    break
        
        return detected
    
    def _integrate_patient_context(self, stage_scores: dict, patient_info: dict) -> tuple:
        """结合患者个体差异综合判断愈合阶段"""
        days_postpartum = self._calc_days_postpartum(patient_info.get('delivery_date'))
        delivery_method = patient_info.get('delivery_method', 'vaginal')
        health_conditions = patient_info.get('health_conditions', '').lower()
        bmi = patient_info.get('bmi', 22.0)
        
        adjusted_scores = stage_scores.copy()
        
        # 1. 根据产后天数调整期望阶段
        if days_postpartum is not None:
            if 1 <= days_postpartum <= 5:
                adjusted_scores['inflammation'] *= 1.3
            elif 6 <= days_postpartum <= 21:
                adjusted_scores['proliferation'] *= 1.3
            elif days_postpartum > 21:
                adjusted_scores['maturation'] *= 1.3
        
        # 2. 糖尿病患者愈合较慢
        if '糖尿病' in health_conditions or 'diabetes' in health_conditions:
            if days_postpartum and days_postpartum > 5:
                adjusted_scores['inflammation'] *= 1.2
                adjusted_scores['maturation'] *= 0.8
        
        # 3. BMI过高影响愈合
        if bmi and bmi > 30:
            adjusted_scores['maturation'] *= 0.9
            adjusted_scores['abnormal'] *= 1.1
        
        # 4. 剖宫产伤口通常比会阴切开愈合略慢
        if delivery_method == 'cesarean':
            if days_postpartum and days_postpartum < 14:
                adjusted_scores['proliferation'] *= 1.1
        
        # 异常分数超过阈值直接判定
        if adjusted_scores.get('abnormal', 0) > 0.4:
            return 'abnormal', adjusted_scores['abnormal']
        
        # 取最高分的阶段
        best_stage = max(adjusted_scores, key=adjusted_scores.get)
        
        # 若所有分数极低（API未识别出明显特征），根据天数推断
        if adjusted_scores[best_stage] < 0.15 and days_postpartum is not None:
            if days_postpartum <= 5:
                best_stage, confidence = 'inflammation', 0.6
            elif days_postpartum <= 21:
                best_stage, confidence = 'proliferation', 0.6
            else:
                best_stage, confidence = 'maturation', 0.6
            return best_stage, confidence
        
        return best_stage, adjusted_scores[best_stage]
    
    def _determine_urgency(self, anomalies: list, stage: str, patient_info: dict) -> str:
        """确定紧急程度"""
        emergency_anomalies = {'infection', 'dehiscence', 'necrosis', 'bleeding'}
        high_anomalies = {'hematoma', 'excessive_discharge'}
        
        if stage == 'abnormal' and any(a in emergency_anomalies for a in anomalies):
            return 'emergency'
        elif any(a in emergency_anomalies for a in anomalies):
            return 'high'
        elif any(a in high_anomalies for a in anomalies) or stage == 'abnormal':
            return 'high'
        elif len(anomalies) > 0:
            return 'normal'
        else:
            return 'low'
    
    def _calc_days_postpartum(self, delivery_date) -> 'Optional[int]':
        """计算产后天数"""
        if not delivery_date:
            return None
        if isinstance(delivery_date, str):
            try:
                delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
            except Exception:
                return None
        if isinstance(delivery_date, datetime):
            delivery_date = delivery_date.date()
        return (date.today() - delivery_date).days
    
    def _assess_risk_factors(self, patient_info: dict) -> list:
        """评估风险因素列表"""
        risks = []
        health = patient_info.get('health_conditions', '').lower()
        bmi = patient_info.get('bmi', 22)
        age = patient_info.get('age', 30)
        
        if '糖尿病' in health or 'diabetes' in health:
            risks.append('糖尿病影响愈合速度')
        if '高血压' in health or 'hypertension' in health:
            risks.append('高血压需关注伤口血供')
        if bmi and bmi > 28:
            risks.append('超重可能影响伤口愈合')
        if age and age > 35:
            risks.append('高龄产妇需加强关注')
        if patient_info.get('parity', 1) >= 3:
            risks.append('多次分娩需注意组织弹性')
        
        return risks
    
    def _merge_infection_risk(self, anomalies: list, infection_risk_score: float) -> tuple:
        """
        将本地颜色启发式感染评分融入异常类型列表。

        当 infection_risk_score 超过配置阈值时，若尚未标记 infection 则自动添加，
        并将评分上调（确保后续 urgency 判断能感知）。

        注意：感染风险评分为辅助建议，不能替代医生诊断。

        Returns:
            (anomalies, infection_risk_score) 更新后的元组
        """
        try:
            cfg = current_app.config
            threshold = cfg.get('INFECTION_RISK_SCORE_THRESHOLD', _DEFAULT_RISK_THRESHOLD)
        except RuntimeError:
            threshold = _DEFAULT_RISK_THRESHOLD

        if infection_risk_score >= threshold and 'infection' not in anomalies:
            anomalies = list(anomalies) + ['infection']
            logger.info(
                f"本地感染风险评分 {infection_risk_score:.3f} ≥ 阈值 {threshold:.3f}，"
                "已标记 infection 异常（辅助参考，请医生确认）"
            )
        return anomalies, infection_risk_score


        """
        本地感染风险启发式评分（基于颜色特征，无需网络）。

        评估依据：
        - 红色区域（H∈[0,15]∪[160,180]）比例 → 炎症/充血
        - 黄绿色区域（H∈[25,85]，高饱和）比例 → 渗出/脓液
        - 全图高饱和（S>150）像素比例 → 异常局部特征

        Returns:
            float: 感染风险评分，范围 [0, 1]；
                   值越大表示感染风险越高。
            注意：本评分为辅助参考，不能替代医生诊断。
        """
        try:
            import cv2

            img_bgr = cv2.imread(image_path)
            if img_bgr is None:
                logger.warning(f"感染风险评估：无法读取图像 {image_path}")
                return 0.0

            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            total_pixels = img_hsv.shape[0] * img_hsv.shape[1]
            if total_pixels == 0:
                return 0.0

            h, s, v = img_hsv[:, :, 0], img_hsv[:, :, 1], img_hsv[:, :, 2]

            # ── 红色区域（H ∈ [0,15] 或 [160,180]）──
            red_mask = ((h <= 15) | (h >= 160)) & (s > 80) & (v > 60)
            red_ratio = float(np.count_nonzero(red_mask)) / total_pixels

            # ── 黄绿色（化脓）区域（H ∈ [25,85]，高饱和）──
            yg_mask = ((h >= 25) & (h <= 85)) & (s > 100) & (v > 60)
            yg_ratio = float(np.count_nonzero(yg_mask)) / total_pixels

            # ── 全图高饱和区域（S > 150）──
            sat_mask = s > 150
            sat_ratio = float(np.count_nonzero(sat_mask)) / total_pixels

            # 读取配置阈值（Flask 上下文不可用时使用默认值）
            try:
                cfg = current_app.config
                w_red = cfg.get('INFECTION_WEIGHT_RED', _DEFAULT_W_RED)
                w_yg = cfg.get('INFECTION_WEIGHT_YELLOW_GREEN', _DEFAULT_W_YG)
                w_sat = cfg.get('INFECTION_WEIGHT_HIGH_SATURATION', _DEFAULT_W_SAT)
                red_thr = cfg.get('INFECTION_RED_RATIO_THRESHOLD', _DEFAULT_RED_THRESHOLD)
                yg_thr = cfg.get('INFECTION_YELLOW_GREEN_RATIO_THRESHOLD', _DEFAULT_YG_THRESHOLD)
                sat_thr = cfg.get('INFECTION_HIGH_SATURATION_THRESHOLD', _DEFAULT_SAT_THRESHOLD)
            except RuntimeError:
                w_red, w_yg, w_sat = _DEFAULT_W_RED, _DEFAULT_W_YG, _DEFAULT_W_SAT
                red_thr, yg_thr, sat_thr = _DEFAULT_RED_THRESHOLD, _DEFAULT_YG_THRESHOLD, _DEFAULT_SAT_THRESHOLD

            # 各分量归一化得分（超过阈值即满分；低于阈值线性缩放）
            score_red = min(red_ratio / max(red_thr, 1e-6), 1.0)
            score_yg = min(yg_ratio / max(yg_thr, 1e-6), 1.0)
            score_sat = min(sat_ratio / max(sat_thr, 1e-6), 1.0)

            infection_risk = w_red * score_red + w_yg * score_yg + w_sat * score_sat
            infection_risk = min(round(infection_risk, 3), 1.0)

            logger.debug(
                f"感染风险评估: red={red_ratio:.3f}, yg={yg_ratio:.3f}, "
                f"sat={sat_ratio:.3f} → risk={infection_risk:.3f}"
            )
            return infection_risk

        except ImportError:
            logger.info("opencv-python 未安装，跳过本地感染风险评估")
            return 0.0
        except Exception as e:
            logger.warning(f"感染风险评估失败: {e}")
            return 0.0


        """计算图像MD5哈希"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ''
    
    def _fallback_analysis(self, image_path: str, patient_info: dict, base_result: dict) -> dict:
        """百度API不可用时的降级分析（基于产后天数推断）"""
        days = self._calc_days_postpartum(patient_info.get('delivery_date'))

        # 本地感染风险仍可计算
        infection_risk_score = self._compute_infection_risk_score(image_path)
        anomalies = []
        anomalies, infection_risk_score = self._merge_infection_risk(anomalies, infection_risk_score)
        base_result['infection_risk_score'] = infection_risk_score
        if anomalies:
            base_result['anomaly_detected'] = True
            base_result['anomaly_types'] = anomalies

        if days is None:
            base_result.update({
                'success': True,
                'wound_stage': 'inflammation',
                'confidence_score': 0.4,
                'urgency_level': 'normal',
                'analysis_detail': {
                    'fallback': True,
                    'reason': 'API不可用，使用规则推断',
                    'infection_risk_note': '感染风险评分为辅助参考，不能替代医生诊断。如有疑虑请及时就医。'
                }
            })
        elif days <= 5:
            base_result.update({'wound_stage': 'inflammation', 'confidence_score': 0.65})
        elif days <= 21:
            base_result.update({'wound_stage': 'proliferation', 'confidence_score': 0.65})
        else:
            base_result.update({'wound_stage': 'maturation', 'confidence_score': 0.65})

        base_result['success'] = True
        base_result.setdefault('analysis_detail', {})
        base_result['analysis_detail']['fallback'] = True
        if anomalies:
            urgency = self._determine_urgency(anomalies, base_result.get('wound_stage', 'inflammation'), patient_info)
            base_result['urgency_level'] = urgency
        return base_result