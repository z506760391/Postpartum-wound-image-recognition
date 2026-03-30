import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models.database import db, Patient, WoundAnalysis
from models.schemas import AnalysisSchema
from services.wound_analyzer import WoundAnalyzer
from services.care_guidance import CareGuidanceService
from utils.image_processor import ImageProcessor
from utils.humancare_generator import HumancareGenerator
from utils.logger import get_logger

logger = get_logger(__name__)
analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')

_schema = AnalysisSchema()
_image_processor = ImageProcessor()
_care_service = CareGuidanceService()
_humancare = HumancareGenerator()


@analysis_bp.route('/upload', methods=['GET'])
def upload_page():
    patients = Patient.query.order_by(Patient.name).all()
    return render_template('analysis/upload.html', patients=patients)


@analysis_bp.route('/upload', methods=['POST'])
def upload():
    patient_id = request.form.get('patient_id')
    image_file = request.files.get('image')

    valid, err = _schema.validate(patient_id, image_file)
    if not valid:
        flash(err, 'danger')
        return redirect(url_for('analysis.upload_page'))

    # 验证图像格式
    is_valid_img, img_err = _image_processor.validate_image(image_file)
    if not is_valid_img:
        flash(img_err, 'danger')
        return redirect(url_for('analysis.upload_page'))

    try:
        patient = Patient.query.get_or_404(int(patient_id))

        # 保存图像
        upload_folder = current_app.config['UPLOAD_FOLDER']
        save_path = _image_processor.save_upload(image_file, upload_folder, patient.id)
        image_hash = _image_processor.compute_hash(save_path)

        # 构建患者信息字典
        patient_info = {
            'name': patient.name,
            'age': patient.age,
            'delivery_method': patient.delivery_method,
            'delivery_date': patient.delivery_date,
            'health_conditions': patient.health_conditions or '',
            'bmi': patient.bmi,
            'parity': patient.parity,
            'emotional_state': patient.emotional_state or 'stable',
        }

        # 伤口分析
        analyzer = WoundAnalyzer()
        analysis_result = analyzer.analyze(save_path, patient_info)

        wound_stage = analysis_result.get('wound_stage', 'unknown')
        anomaly_types = analysis_result.get('anomaly_types', [])
        urgency_level = analysis_result.get('urgency_level', 'normal')

        # 护理指导
        care_guidance = _care_service.generate(wound_stage, patient_info, anomaly_types)

        # 人文关怀
        humancare = _humancare.generate(patient_info, wound_stage, urgency_level, anomaly_types)

        # 保存分析记录
        record = WoundAnalysis(
            patient_id=patient.id,
            image_path=save_path,
            image_hash=image_hash,
            wound_stage=wound_stage,
            confidence_score=analysis_result.get('confidence_score', 0.0),
            anomaly_detected=analysis_result.get('anomaly_detected', False),
            urgency_level=urgency_level,
            baidu_raw_result=analysis_result.get('raw_api_result'),
            care_guidance=json.dumps(care_guidance, ensure_ascii=False),
            humancare_message=humancare.get('full_message', ''),
        )
        record.set_anomaly_types(anomaly_types)
        db.session.add(record)
        db.session.commit()

        return redirect(url_for('analysis.result', analysis_id=record.id))

    except Exception as e:
        db.session.rollback()
        logger.error(f"分析上传失败: {e}", exc_info=True)
        flash(f'分析失败：{e}', 'danger')
        return redirect(url_for('analysis.upload_page'))


@analysis_bp.route('/result/<int:analysis_id>')
def result(analysis_id):
    try:
        record = WoundAnalysis.query.get_or_404(analysis_id)
        patient = Patient.query.get_or_404(record.patient_id)

        care_guidance = {}
        if record.care_guidance:
            try:
                care_guidance = json.loads(record.care_guidance)
            except Exception:
                pass

        return render_template(
            'analysis/result.html',
            record=record,
            patient=patient,
            care_guidance=care_guidance,
            anomaly_types=record.get_anomaly_types(),
        )
    except Exception as e:
        logger.error(f"获取分析结果失败: {e}")
        flash('获取结果失败', 'danger')
        return redirect(url_for('analysis.upload_page'))


@analysis_bp.route('/history/<int:patient_id>')
def history(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        analyses = WoundAnalysis.query.filter_by(patient_id=patient_id).order_by(
            WoundAnalysis.created_at.desc()
        ).all()
        return render_template('analysis/history.html', patient=patient, analyses=analyses)
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        flash('获取历史记录失败', 'danger')
        return redirect(url_for('patient.list_patients'))
