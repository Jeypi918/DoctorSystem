# Add missing user_id columns

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('core_doctor') AND name = 'user_id') "
            "ALTER TABLE core_doctor ADD user_id BIGINT NOT NULL DEFAULT 1",
            reverse_sql="ALTER TABLE core_doctor DROP COLUMN user_id"
        ),
        migrations.RunSQL(
            "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('core_userprofile') AND name = 'user_id') "
            "ALTER TABLE core_userprofile ADD user_id BIGINT NOT NULL DEFAULT 1",
            reverse_sql="ALTER TABLE core_userprofile DROP COLUMN user_id"
        ),
    ]