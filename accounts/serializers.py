from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False
    )


class SignupSerializer(serializers.Serializer):
    username = serializers.RegexField(
        r"^[\w.@+-]+$",
        max_length=150,
        error_messages={
            "invalid": "Use only letters, numbers and . @ + - _ in the username.",
        },
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value
