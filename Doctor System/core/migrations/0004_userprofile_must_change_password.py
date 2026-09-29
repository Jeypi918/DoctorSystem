from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_unique_constraints'),
    ]

    operations = [
        migrations.RunSQL(
            "IF COL_LENGTH('core_userprofile', 'must_change_password') IS NULL "
            "ALTER TABLE core_userprofile ADD must_change_password BIT NOT NULL "
            "CONSTRAINT DF_core_userprofile_must_change_password DEFAULT 0",
            reverse_sql=(
                "ALTER TABLE core_userprofile DROP CONSTRAINT DF_core_userprofile_must_change_password; "
                "ALTER TABLE core_userprofile DROP COLUMN must_change_password"
            ),
        ),
    ]