# services/care_guidance.py - 个性化护理指导生成服务
from datetime import date, datetime
from utils.logger import get_logger

logger = get_logger(__name__)

# 各阶段基础护理指导模板
CARE_TEMPLATES = {
    'inflammation': {
        'title': '炎症期护理指导',
        'basic_care': [
            '保持伤口区域清洁干燥，每日用生理盐水或碘伏轻轻清洁1-2次',
            '按医嘱使用抗生素软膏，均匀涂抹于伤口表面',
            '佩戴宽松透气的内衣，减少对伤口的摩擦和压迫',
            '观察伤口颜色变化，轻微红肿属正常，无需过度担忧',
            '避免用手触碰伤口，防止继发感染',
            '若剧烈疼痛，可在医生指导下使用止痛药（需评估哺乳影响）'
        ],
        'diet_advice': [
            '多摄入高蛋白食物：鱼、蛋、豆制品、瘦肉',
            '补充维生素C（猕猴桃、柑橘类）促进胶原蛋白合成',
            '适量摄入锌元素（坚果、海鲜）加速组织修复',
            '避免辛辣刺激食物，减少炎症反应',
            '保持充足水分，每日饮水1500-2000ml'
        ],
        'alert_signs': [
            '⚠️ 伤口出现大量脓性分泌物',
            '⚠️ 发热超过38.5°C持续超过24小时',
            '⚠️ 伤口周围出现明显硬块',
            '⚠️ 疼痛程度持续加重而非减轻'
        ]
    },
    'proliferation': {
        'title': '增生期护理指导',
        'basic_care': [
            '继续保持伤口清洁，可逐渐减少消毒频率至每日1次',
            '结痂后不要强行撕除，让其自然脱落',
            '可适当进行轻度活动，但避免剧烈运动或长时间站立',
            '定期检查伤口愈合进度，如有异常及时就医',
            '保持伤口湿润环境（遵医嘱使用湿性愈合敷料）',
            '适当按摩伤口周围（不含开放创面），促进局部血液循环'
        ],
        'diet_advice': [
            '继续保持高蛋白饮食，增加胶原蛋白摄入',
            '适当补充维生素A（胡萝卜、菠菜）促进细胞增殖',
            '铁元素补充（红肉、菠菜）预防贫血',
            '保持均衡饮食，不刻意节食',
            '母乳喂养者需额外补充500大卡热量'
        ],
        'alert_signs': [
            '⚠️ 结痂处出现渗血或渗液增多',
            '⚠️ 伤口边缘出现裂开迹象',
            '⚠️ 出现异常瘙痒伴红肿',
            '⚠️ 会阴部位出现异常分泌物或异味'
        ]
    },
    'maturation': {
        'title': '成熟期护理指导',
        'basic_care': [
            '伤口基本愈合，继续保持局部清洁即可',
            '可使用硅酮凝胶或积雪苷霜预防瘢痕增生',
            '逐步恢复正常活动，循序渐进增加运动量',
            '避免阳光直射瘢痕部位，防止色素沉着',
            '如有瘢痕增生，可在医生指导下进行瘢痕治疗',
            '产后6周复查，评估盆底功能恢复情况'
        ],
        'diet_advice': [
            '均衡营养，无特殊限制',
            '继续补充维生素E（植物油、坚果）促进皮肤弹性',
            '适当减少高糖食物，维持健康体重',
            '保持规律饮食，促进整体康复'
        ],
        'alert_signs': [
            '⚠️ 瘢痕出现异常增厚、红肿或痒痛加剧',
            '⚠️ 剖宫产疤痕出现窦道或不明分泌物',
            '⚠️ 会阴部位出现性交疼痛或功能障碍'
        ]
    },
    'abnormal': {
        'title': '⚠️ 紧急护理指导',
        'basic_care': [
            '🔴 立即停止自行处理，请尽快就医',
            '保持伤口部位相对静止，减少活动',
            '用清洁纱布轻轻覆盖伤口，避免污染',
            '记录异常出现时间、程度和变化情况',
            '如有大量出血，立即按压并拨打急救电话',
            '就医时携带本次分析报告，告知医生具体情况'
        ],
        'diet_advice': [
            '就医前保持正常饮食，维持体力',
            '避免空腹就医，确保血糖稳定'
        ],
        'alert_signs': [
            '🔴 出血不止或大量出血——立即拨打120',
            '🔴 高热（≥39°C）伴伤口红肿——立即就医',
            '🔴 伤口完全裂开——紧急就医',
            '🔴 意识模糊或极度虚弱——立即拨打120'
        ]
    }
}

# 按分娩方式细化的额外指导
DELIVERY_SPECIFIC_CARE = {
    'cesarean': {
        'wound_location': '腹部横切口/纵切口',
        'specific_tips': [
            '术后早期下床活动时，用手轻按腹部伤口处以减轻牵拉感',
            '穿着高腰内裤或使用产后腹带，减轻切口张力',
            '淋浴时使用防水敷贴保护伤口，避免浸泡',
            '避免提重物（>5kg），一般需持续6-8周',
            '产后42天复查时请医生评估切口愈合情况',
            '再次妊娠间隔建议至少18-24个月'
        ]
    },
    'vaginal': {
        'wound_location': '会阴部切口/撕裂伤',
        'specific_tips': [
            '每次大小便后用温水或生理盐水冲洗会阴部，由前向后',
            '坐浴可用1:5000高锰酸钾溶液，每日1-2次，每次10-15分钟',
            '使用柔软的产妇专用卫生巾，勤于更换（每2-3小时一次）',
            '坐位时可使用会阴保护垫或甜甜圈坐垫减轻压力',
            '避免下蹲或剧烈用力，防止伤口裂开',
            '产后6-8周恢复性生活前，建议咨询医生评估愈合情况'
        ]
    }
}

# 特殊健康状况额外建议
SPECIAL_CONDITION_CARE = {
    '糖尿病': [
        '糖尿病患者愈合较慢，需严格控制血糖（空腹≤6.1mmol/L）',
        '增加伤口观察频率，每日至少检查2次',
        '血糖不稳定时及时就医，切勿自行判断愈合情况'
    ],
    '高血压': [
        '按时服用降压药，维持血压稳定',
        '避免情绪激动，保持平和心态',
        '注意休息，避免过度劳累影响血压'
    ],
    '贫血': [
        '积极补铁治疗，必要时输血',
        '营养支持加强，多摄入含铁食物',
        '贫血会延缓伤口愈合，需密切监测'
    ]
}


class CareGuidanceService:
    """个性化护理指导生成服务"""
    
    def generate(self, wound_stage: str, patient_info: dict, anomaly_types: list = None) -> dict:
        """
        生成完整的个性化护理指导
        
        Args:
            wound_stage: 伤口愈合阶段
            patient_info: 产妇个人信息
            anomaly_types: 检测到的异常类型列表
        
        Returns:
            包含完整护理指导的字典
        """
        logger.info(f"生成护理指导: 阶段={wound_stage}, 患者={patient_info.get('name', '未知')}")
        
        anomaly_types = anomaly_types or []
        delivery_method = patient_info.get('delivery_method', 'vaginal')
        
        # 获取基础护理模板
        template = CARE_TEMPLATES.get(wound_stage, CARE_TEMPLATES['inflammation'])
        
        # 获取分娩方式特定指导
        delivery_care = DELIVERY_SPECIFIC_CARE.get(delivery_method, DELIVERY_SPECIFIC_CARE['vaginal'])
        
        # 构建护理指导
        guidance = {
            'title': template['title'],
            'wound_location': delivery_care['wound_location'],
            'basic_care': template['basic_care'].copy(),
            'delivery_specific': delivery_care['specific_tips'].copy(),
            'diet_advice': template['diet_advice'].copy(),
            'alert_signs': template['alert_signs'].copy(),
            'special_condition_care': [],
            'anomaly_guidance': [],
            'follow_up_schedule': self._get_followup_schedule(wound_stage, patient_info),
            'days_postpartum': self._calc_days_postpartum(patient_info.get('delivery_date'))
        }
        
        # 加入特殊健康状况建议
        health_conditions = patient_info.get('health_conditions', '')
        for condition, care_list in SPECIAL_CONDITION_CARE.items():
            if condition in health_conditions:
                guidance['special_condition_care'].extend(care_list)
        
        # 针对异常类型的额外指导
        if anomaly_types:
            guidance['anomaly_guidance'] = self._get_anomaly_guidance(anomaly_types)
        
        # 生成文本摘要
        guidance['summary_text'] = self._build_summary_text(guidance, patient_info, wound_stage)
        
        return guidance
    
    def _get_anomaly_guidance(self, anomaly_types: list) -> list:
        """针对具体异常类型的处理指导"""
        anomaly_guidance_map = {
            'infection': [
                '感染迹象：立即就医，勿自行挤压脓液',
                '医生可能需要进行伤口清创和抗生素治疗',
                '记录感染开始时间、分泌物颜色（黄/绿色需高度警惕）'
            ],
            'dehiscence': [
                '伤口裂开：保持冷静，用清洁纱布覆盖',
                '立即前往医院，可能需要重新缝合',
                '裂开期间避免活动，减少伤口张力'
            ],
            'hematoma': [
                '血肿：局部冷敷（24h内）或热敷（24h后）',
                '较大血肿需医生抽吸处理',
                '密切观察血肿变化，持续增大需就医'
            ],
            'seroma': [
                '血清肿：一般可自行吸收，保持观察',
                '如积液较多或持续增长，需医生穿刺引流',
                '避免按压或摩擦积液区域'
            ],
            'excessive_discharge': [
                '异常分泌物：记录分泌物颜色、气味、量',
                '清亮或淡黄色分泌物可观察，黄绿色或异味需就医',
                '及时更换敷料，保持局部清洁'
            ],
            'bleeding': [
                '出血：立即用清洁纱布按压伤口15-20分钟',
                '若按压无效或出血量大，立即就医或拨打120',
                '记录出血开始时间和估计出血量'
            ]
        }
        
        guidance = []
        for anomaly in anomaly_types:
            if anomaly in anomaly_guidance_map:
                guidance.extend(anomaly_guidance_map[anomaly])
        
        return guidance
    
    def _get_followup_schedule(self, wound_stage: str, patient_info: dict) -> list:
        """生成随访时间表"""
        delivery_method = patient_info.get('delivery_method', 'vaginal')
        schedule = []
        
        if wound_stage == 'abnormal':
            schedule.append({'time': '今日', 'action': '立即就医，紧急处理异常情况'})
        elif wound_stage == 'inflammation':
            schedule.append({'time': '3-5天后', 'action': '复查伤口愈合情况'})
            schedule.append({'time': '产后14天', 'action': '拆线（如有缝线）'})
        elif wound_stage == 'proliferation':
            schedule.append({'time': '1周后', 'action': '复查伤口愈合进度'})
        
        # 通用随访节点
        schedule.append({'time': '产后42天', 'action': '产后健康复查（必须）：评估伤口、盆底功能、宫颈恢复'})
        
        if delivery_method == 'cesarean':
            schedule.append({'time': '产后3个月', 'action': '评估剖宫产瘢痕情况，必要时行瘢痕治疗'})
        
        return schedule
    
    def _calc_days_postpartum(self, delivery_date) -> int | None:
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
    
    def _build_summary_text(self, guidance: dict, patient_info: dict, wound_stage: str) -> str:
        """构建护理指导文本摘要"""
        name = patient_info.get('name', '亲爱的妈妈')
        days = guidance.get('days_postpartum')
        days_text = f"，产后第{days}天" if days is not None else ""
        delivery_cn = '剖宫产' if patient_info.get('delivery_method') == 'cesarean' else '顺产'
        
        stage_names = {
            'inflammation': '炎症期（正常愈合阶段）',
            'proliferation': '增生修复期（愈合进行中）',
            'maturation': '成熟期（基本愈合）',
            'abnormal': '异常状态（需及时就医）'
        }
        
        stage_name = stage_names.get(wound_stage, wound_stage)
        
        basic_care_text = ''.join([f'• {c}\n' for c in guidance['basic_care'][:3]])
        diet_text = ''.join([f'• {d}\n' for d in guidance['diet_advice'][:3]])
        alert_text = ''.join([f'{a}\n' for a in guidance['alert_signs'][:2]])

        summary = f"""{name}您好{days_text}，以下是您的个性化护理指导：

📋 伤口评估：您的{delivery_cn}伤口目前处于{stage_name}。

🏥 护理要点：
{basic_care_text}
🍽️ 饮食建议：
{diet_text}
⚠️ 警示信号：
{alert_text}
如有任何不适，请及时就医。祝您早日康复！"""
        return summary.strip()