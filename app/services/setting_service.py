from app.models.audit import SystemSetting
from app import db


def get_setting(key, default=None, cast=str):
    row = SystemSetting.query.filter_by(setting_key=key).first()
    if not row:
        return default
    try:
        return cast(row.setting_value)
    except (TypeError, ValueError):
        return default


def set_setting(key, value, description=None):
    row = SystemSetting.query.filter_by(setting_key=key).first()
    if not row:
        row = SystemSetting(setting_key=key, setting_value=str(value), description=description)
        db.session.add(row)
    else:
        row.setting_value = str(value)
        if description is not None:
            row.description = description
    db.session.commit()
    return row
