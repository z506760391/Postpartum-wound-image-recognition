import random
from utils.logger import get_logger

logger = get_logger(__name__)

# 各愈合阶段鼓励话语
ENCOURAGEMENT_BY_STAGE = {
    'inflammation': [
        '您的伤口正处于初期愈合阶段，这是完全正常的。每一天都是身体努力修复的见证，您做得很棒！',
        '产后头几天是最辛苦的时期，您正在经历这段旅程的开始。您的勇气和坚持令人钦佩！',
        '炎症反应是身体自我保护的信号，说明您的免疫系统正在积极工作。请相信自己的身体，它比您想象的更强大！',
        '新生命的到来需要付出勇气与代价，您已经做到了最难的部分。接下来的每一天都会越来越好！',
    ],
    'proliferation': [
        '太棒了！您的伤口已经进入愈合的中期，新生的组织正在悄悄修复。您的努力没有白费！',
        '每一天您都在向完全康复迈进一步。看看您走过的路，您是如此坚强的妈妈！',
        '伤口正在愈合，就像花朵在悄然绽放。您的身体在您的呵护下正在创造奇迹！',
        '增生期是身体修复最努力的阶段，您和宝宝都在一天天变得更好，这是多么美好的事情！',
    ],
    'maturation': [
        '恭喜您！伤口已基本愈合，这是您坚持护理的成果。您真的做到了，为自己鼓掌吧！',
        '经过这段时间的悉心照护，您的伤口已经进入成熟愈合阶段。您是最用心的妈妈！',
        '看到伤口愈合得如此之好，一定是因为您每天都认真护理。您的付出让宝宝有了一位健康的妈妈！',
        '伤口愈合是一段旅程，而您已经走到了终点。接下来是享受与宝宝在一起的美好时光！',
    ],
    'abnormal': [
        '发现问题是解决问题的第一步，您做了正确的事来检查伤口。请不要担心，医生会帮助您的！',
        '遇到这种情况需要勇气面对，而您做到了。及时就医是对自己和宝宝最好的关爱！',
        '您的身体在发出需要帮助的信号，请认真对待它。专业的医护人员会陪伴您度过这段时光！',
    ],
    'unknown': [
        '感谢您认真关注自己的伤口状况，这种负责任的态度值得称赞！',
        '定期检查伤口是产后护理的重要一环，您做得很好！',
    ],
}

# 情绪关怀语句
EMOTIONAL_CARE = {
    'stable': [
        '看到您保持如此平和的状态，真的令人欣慰。好的心态是最好的良药！',
        '心情稳定的您，一定也在以最好的状态照顾宝宝。您是家人的力量！',
    ],
    'anxious': [
        '产后焦虑是很多妈妈都会经历的，您并不孤单。如果焦虑感持续存在，建议和医生聊聊，他们会帮助您。',
        '感受到您现在的紧张，这完全可以理解。深呼吸，记住——您已经做得很好了！如有需要，爱丁堡产后抑郁量表可以帮助您了解自己的情绪状态。',
        '焦虑的感受会随着时间慢慢减少，如果您感到难以控制，请告诉医生或护士，寻求帮助是强大的表现。',
    ],
    'depressed': [
        '您的感受是真实的，产后情绪低落比您想象的更常见。请记得，寻求帮助不是软弱，而是勇敢。',
        '爱丁堡产后抑郁量表（EPDS）是评估产后情绪的有效工具，建议您向医生咨询，他们能给予专业支持。',
        '黑暗的隧道总有尽头，您现在的感受是可以被帮助的。请告诉您的家人或医生，让他们一起支持您！',
    ],
    'happy': [
        '您积极愉快的心情真的让人感到温暖！好的情绪对伤口愈合也有积极作用，继续保持！',
        '看到您这么开心，相信宝宝也感受到了妈妈满满的爱。这种幸福是最美好的礼物！',
    ],
}

# 母亲角色肯定
MOTHER_AFFIRMATIONS = [
    '您不仅要照顾自己的伤口，还要哺育新生命，这是世界上最伟大的事情之一。',
    '成为妈妈的那一刻起，您就已经是超级英雄了。',
    '您对宝宝的爱，从怀孕的第一天就开始了，这份爱会陪伴他/她一生。',
    '照顾好自己，才能更好地照顾宝宝。您为自己的健康所做的一切，都是对宝宝的爱。',
    '宝宝需要一个健康快乐的妈妈，您正在为此而努力，这非常了不起！',
]

CLOSING_WORDS = [
    '我们一直在您身边，有任何问题随时联系医护团队。祝您和宝宝健康快乐！',
    '记得：照顾好自己，就是给宝宝最好的礼物。我们为您加油！',
    '康复之路上，您不是一个人。医护团队、家人都在支持您，加油！',
    '感谢您信任我们的系统，希望今天的分析对您有所帮助。保重！',
]

GREETINGS = [
    '亲爱的{name}妈妈，您好！',
    '{name}妈妈，很高兴为您服务！',
    '您好，亲爱的{name}！我们非常关心您的康复情况。',
]

PRACTICAL_TIPS = {
    'inflammation': '建议每日用生理盐水轻轻清洁伤口1-2次，并保持伤口干燥透气。',
    'proliferation': '伤口结痂后请不要强行撕除，保持局部湿润环境有助于愈合。',
    'maturation': '可以开始使用硅酮凝胶预防瘢痕增生，避免阳光直射愈合部位。',
    'abnormal': '请立即前往医院就诊，不要自行处理伤口，保持冷静并记录异常出现的时间。',
    'unknown': '请保持伤口清洁干燥，如有疑问及时咨询医生。',
}


class HumancareGenerator:
    """人文关怀内容生成器"""

    def generate(self, patient_info: dict, wound_stage: str,
                 urgency_level: str = 'normal', anomaly_types: list = None) -> dict:
        """
        生成个性化人文关怀内容
        
        Args:
            patient_info: 产妇信息字典
            wound_stage: 伤口愈合阶段
            urgency_level: 紧急程度
            anomaly_types: 检测到的异常类型列表
        Returns:
            包含各类关怀语句的字典
        """
        anomaly_types = anomaly_types or []
        name = patient_info.get('name', '妈妈')
        emotional_state = patient_info.get('emotional_state', 'stable')

        greeting = random.choice(GREETINGS).format(name=name)

        encouragements = ENCOURAGEMENT_BY_STAGE.get(wound_stage, ENCOURAGEMENT_BY_STAGE['unknown'])
        encouragement = random.choice(encouragements)

        emotional_phrases = EMOTIONAL_CARE.get(emotional_state, EMOTIONAL_CARE['stable'])
        emotional_support = random.choice(emotional_phrases)

        mother_affirmation = random.choice(MOTHER_AFFIRMATIONS)
        practical_tip = PRACTICAL_TIPS.get(wound_stage, PRACTICAL_TIPS['unknown'])
        closing = random.choice(CLOSING_WORDS)

        # 紧急情况特殊提示
        urgency_note = ''
        if urgency_level == 'emergency':
            urgency_note = '⚠️ 【重要提醒】检测到紧急情况，请立即前往医院就诊，不要拖延！'
        elif urgency_level == 'high':
            urgency_note = '⚠️ 建议您尽快联系主治医生或前往医院复查，以确保安全。'

        full_message = '\n\n'.join(filter(None, [
            greeting,
            encouragement,
            mother_affirmation,
            emotional_support,
            practical_tip,
            urgency_note,
            closing,
        ]))

        return {
            'greeting': greeting,
            'encouragement': encouragement,
            'mother_affirmation': mother_affirmation,
            'emotional_support': emotional_support,
            'practical_tip': practical_tip,
            'urgency_note': urgency_note,
            'closing_words': closing,
            'full_message': full_message,
        }
