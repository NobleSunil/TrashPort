from django.db import migrations


def remove_dummy_seeded_collectors(apps, schema_editor):
    """
    Purge pre-seeded dummy collector accounts (e.g. collector.*@trashport.in).
    Real collectors register themselves through the public registration workflow.
    """
    User = apps.get_model("users", "User")
    User.objects.filter(
        role="COLLECTOR",
        email__startswith="collector.",
        email__endswith="@trashport.in",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("waste_management", "0014_city_alter_pickuprequest_collector_earnings_and_more"),
        ("users", "0008_collectorprofile_hub"),
    ]

    operations = [
        migrations.RunPython(remove_dummy_seeded_collectors, migrations.RunPython.noop),
    ]
