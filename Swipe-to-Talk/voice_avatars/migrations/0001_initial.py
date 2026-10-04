from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConversationSession",
            fields=[
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("updated_on", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Opaque session id shared with the voice agent.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "avatar_id",
                    models.CharField(
                        help_text="Persona key from personas.PERSONAS.",
                        max_length=64,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("active", "Active"),
                            ("ended", "Ended"),
                        ],
                        default="pending",
                        help_text="Lifecycle status of the call (pending -> active -> ended).",
                        max_length=12,
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the voice agent first connected to this session.",
                        null=True,
                    ),
                ),
                (
                    "ended_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the call was hung up.",
                        null=True,
                    ),
                ),
                (
                    "duration_seconds",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Reported call duration in seconds.",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="Swiper who started the call.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voice_avatar_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user", "status"], name="voice_avatars_user_status_idx")
                ],
            },
        ),
    ]
