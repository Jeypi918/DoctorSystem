# Add unique constraints for user_id

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_user_columns'),
    ]

    operations = [
        migrations.RunSQL(
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID('core_doctor') AND name = 'UQ_core_doctor_user_id') "
            "ALTER TABLE core_doctor ADD CONSTRAINT UQ_core_doctor_user_id UNIQUE (user_id)",
            reverse_sql="ALTER TABLE core_doctor DROP CONSTRAINT UQ_core_doctor_user_id"
        ),
        migrations.RunSQL(
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID('core_userprofile') AND name = 'UQ_core_userprofile_user_id') "
            "ALTER TABLE core_userprofile ADD CONSTRAINT UQ_core_userprofile_user_id UNIQUE (user_id)",
            reverse_sql="ALTER TABLE core_userprofile DROP CONSTRAINT UQ_core_userprofile_user_id"
        ),
    ]