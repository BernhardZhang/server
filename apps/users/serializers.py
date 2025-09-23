from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'avatar', 'balance', 'total_invested', 'total_received', 'current_valuation', 'ownership_percentage')
        read_only_fields = ('balance', 'total_invested', 'total_received')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'phone')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("密码不匹配")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')

        # 处理可选字段 - 如果phone是空字符串，保持为空字符串
        if 'phone' in validated_data and validated_data['phone'] == '':
            validated_data['phone'] = ''

        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError("邮箱或密码错误")
            if not user.is_active:
                raise serializers.ValidationError("用户账户已被禁用")
            data['user'] = user
        else:
            raise serializers.ValidationError("必须提供邮箱和密码")
        
        return data