from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import db, Patient
from models.schemas import PatientSchema, ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)
patient_bp = Blueprint('patient', __name__, url_prefix='/patients')
_schema = PatientSchema()


@patient_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('patient/register.html')

    try:
        data = _schema.validate(request.form.to_dict())
        patient = Patient(**data)
        db.session.add(patient)
        db.session.commit()
        flash(f'产妇 {patient.name} 注册成功！', 'success')
        return redirect(url_for('patient.profile', patient_id=patient.id))
    except ValidationError as e:
        flash(f'信息验证失败：{e}', 'danger')
    except Exception as e:
        db.session.rollback()
        logger.error(f"注册产妇失败: {e}")
        flash('注册失败，请稍后重试', 'danger')

    return render_template('patient/register.html', form_data=request.form)


@patient_bp.route('/<int:patient_id>')
def profile(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        analyses = patient.analyses.order_by(
            db.text('created_at DESC')
        ).limit(20).all()
        return render_template('patient/profile.html', patient=patient, analyses=analyses)
    except Exception as e:
        logger.error(f"获取产妇信息失败: {e}")
        flash('获取信息失败', 'danger')
        return redirect(url_for('patient.list_patients'))


@patient_bp.route('/')
def list_patients():
    try:
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '').strip()
        query = Patient.query
        if q:
            query = query.filter(Patient.name.like(f'%{q}%'))
        patients = query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        return render_template('patient/list.html', patients=patients, q=q)
    except Exception as e:
        logger.error(f"列出产妇失败: {e}")
        flash('获取产妇列表失败', 'danger')
        return render_template('patient/list.html', patients=None, q='')
