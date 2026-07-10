from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_hospitalinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='hospitalinfo',
            name='latitude',
            field=models.FloatField(
                default=-4.2594,
                help_text='Latitude GPS (CHU Brazzaville par défaut)',
            ),
        ),
        migrations.AddField(
            model_name='hospitalinfo',
            name='longitude',
            field=models.FloatField(
                default=15.2847,
                help_text='Longitude GPS (CHU Brazzaville par défaut)',
            ),
        ),
        migrations.AddField(
            model_name='hospitalinfo',
            name='google_maps_query',
            field=models.CharField(
                blank=True,
                default='Centre Hospitalier Universitaire de Brazzaville, Congo',
                help_text="Requête Google Maps pour l'embed et l'itinéraire",
                max_length=300,
            ),
        ),
    ]
