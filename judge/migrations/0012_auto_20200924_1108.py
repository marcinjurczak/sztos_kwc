# Generated by Django 3.1 on 2020-09-24 11:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0011_merge_20200924_1059'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testrun',
            name='return_code',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='testrun',
            name='solution',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='test_runs', to='judge.solution'),
        ),
        migrations.AlterField(
            model_name='testrun',
            name='state',
            field=models.IntegerField(choices=[(0, 'Valid'), (1, 'Crashed'), (2, 'Invalid'), (3, 'Timed Out'), (4, 'Pending')], default=4),
        ),
        migrations.AlterField(
            model_name='testrun',
            name='stderr',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='testrun',
            name='stdout',
            field=models.TextField(null=True),
        ),
    ]
