from datetime import datetime


class ValidationError(Exception):
    pass


class PatientSchema:
    """产妇信息验证"""

    REQUIRED_FIELDS = ['name', 'age', 'delivery_method', 'delivery_date']
    VALID_DELIVERY_METHODS = {'vaginal', 'cesarean'}
    VALID_EMOTIONAL_STATES = {'stable', 'anxious', 'depressed', 'happy'}

    def validate(self, data: dict) -> dict:
        """验证并返回清洗后的数据，失败时抛出 ValidationError"""
        errors = []

        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(f'{field} 为必填项')

        if errors:
            raise ValidationError('；'.join(errors))

        name = str(data['name']).strip()
        if len(name) < 2 or len(name) > 50:
            errors.append('姓名长度须在2-50字之间')

        try:
            age = int(data['age'])
            if age < 14 or age > 60:
                errors.append('年龄须在14-60岁之间')
        except (ValueError, TypeError):
            errors.append('年龄必须为整数')
            age = None

        delivery_method = str(data['delivery_method']).strip().lower()
        if delivery_method not in self.VALID_DELIVERY_METHODS:
            errors.append(f"分娩方式须为 {self.VALID_DELIVERY_METHODS} 之一")

        try:
            delivery_date = datetime.strptime(str(data['delivery_date']), '%Y-%m-%d').date()
            if delivery_date > datetime.utcnow().date():
                errors.append('分娩日期不能是未来日期')
        except ValueError:
            errors.append('分娩日期格式须为 YYYY-MM-DD')
            delivery_date = None

        if errors:
            raise ValidationError('；'.join(errors))

        emotional_state = str(data.get('emotional_state', 'stable')).strip().lower()
        if emotional_state not in self.VALID_EMOTIONAL_STATES:
            emotional_state = 'stable'

        bmi = None
        if data.get('bmi'):
            try:
                bmi = float(data['bmi'])
                if bmi < 10 or bmi > 60:
                    bmi = None
            except (ValueError, TypeError):
                bmi = None

        return {
            'name': name,
            'age': age,
            'delivery_method': delivery_method,
            'delivery_date': delivery_date,
            'health_conditions': str(data.get('health_conditions', '')).strip(),
            'allergies': str(data.get('allergies', '')).strip(),
            'bmi': bmi,
            'gravidity': max(1, int(data.get('gravidity', 1) or 1)),
            'parity': max(1, int(data.get('parity', 1) or 1)),
            'contact_phone': str(data.get('contact_phone', '')).strip(),
            'emotional_state': emotional_state,
        }


class AnalysisSchema:
    """分析请求验证"""

    def validate(self, patient_id, image_file) -> tuple:
        """
        验证分析请求
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not patient_id:
            return False, '请选择产妇'

        try:
            int(patient_id)
        except (ValueError, TypeError):
            return False, '无效的产妇ID'

        if not image_file or image_file.filename == '':
            return False, '请上传图像文件'

        return True, ''
