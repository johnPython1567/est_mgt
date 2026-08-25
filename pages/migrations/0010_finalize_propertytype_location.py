from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0009_backfill_propertytype_location'),
    ]

    operations = [
        # Drop the index on the old CharField before dropping the
        # column itself, so Django's migration state stays consistent
        # (the column and its index are removed together).
        migrations.RemoveIndex(
            model_name='property',
            name='property_type_idx',
        ),
        migrations.RemoveField(
            model_name='property',
            name='property_type',
        ),
        migrations.RemoveField(
            model_name='property',
            name='city',
        ),
        migrations.RemoveField(
            model_name='property',
            name='state',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='property_type_fk',
            new_name='property_type',
        ),
        migrations.AlterField(
            model_name='property',
            name='property_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='properties',
                to='pages.propertytype',
            ),
        ),
        migrations.AlterField(
            model_name='property',
            name='location',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='properties',
                to='pages.location',
            ),
        ),
    ]