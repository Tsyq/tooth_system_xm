from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    password = serializers.CharField(
        write_only=True,
        max_length=100,
        required=False
    )

    class Meta:
        model = get_user_model()
        fields = ['id', 'name', 'phone', 'role', 'avatar', 'status', 'created_at', 'updated_at', 'password']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = get_user_model().objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class UserLogOutSerializer(serializers.Serializer):
    "A serializer for validate data for Logging out user"
    refresh = serializers.CharField(required=True,
                                    write_only=True, trim_whitespace=True)

    def validate_refresh(self, value):
        """Validate the refresh token"""
        access_token = self.context.get('access_token')

        if not access_token:
            raise serializers.\
                ValidationError("Something wrong in the access token")

        try:
            access_user_id = access_token.payload.get('user_id')
            if access_user_id is None:
                raise serializers.ValidationError
            ("User ID is missing in the access token.")
        except Exception:
            raise serializers.ValidationError(
                "Something went rong extracting" +
                "user id from payload of access token")

        # Validate the refresh token
        try:
            refresh_token = RefreshToken(value)
            refresh_user_id = refresh_token.payload.get('user_id')
        except TokenError:
            raise serializers.ValidationError(
                "Invalid or expired refresh token.")

        # Check if the user ID in the access token matches the refresh token
        if access_user_id != refresh_user_id:
            raise serializers.ValidationError(
                "The refresh token does not belong " +
                "to the same user as the access token.")

        return value
