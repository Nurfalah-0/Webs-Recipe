from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0002_alter_bookmark_id_alter_category_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="recipe",
            name="is_approved",
            field=models.BooleanField(default=False),
        ),
    ]
