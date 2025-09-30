from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.conf import settings
import logging
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, LoginSerializer, ChangePasswordSerializer
from . import cipherFunctions
from . import params

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        # 清除用户的缓存数据，确保获取最新信息
        cache_key = f'user_profile_{user.id}'
        cache.delete(cache_key)

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def logout_view(request):
    try:
        # 清除用户的缓存数据
        cache_key = f'user_profile_{request.user.id}'
        cache.delete(cache_key)

        request.user.auth_token.delete()
    except:
        pass
    logout(request)
    return Response({'message': '登出成功'})

@api_view(['GET'])
def profile_view(request):
    """获取用户配置文件，带缓存优化"""
    user_id = request.user.id
    cache_key = f'user_profile_{user_id}'

    # 尝试从缓存获取
    cached_data = cache.get(cache_key)
    if cached_data:
        # 添加缓存标识
        cached_data['_cached'] = True
        cached_data['_cache_time'] = timezone.now().isoformat()
        return Response(cached_data)

    # 缓存未命中，从数据库获取
    user_data = UserSerializer(request.user).data

    # 缓存30秒，减少频繁查询
    cache.set(cache_key, user_data, 30)

    # 添加非缓存标识
    user_data['_cached'] = False
    user_data['_cache_time'] = timezone.now().isoformat()

    return Response(user_data)

@api_view(['POST'])
def change_password_view(request):
    """修改密码"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # 清除用户的缓存数据
        cache_key = f'user_profile_{user.id}'
        cache.delete(cache_key)

        return Response({'message': '密码修改成功'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@require_http_methods(["POST"])
def sso_login_view(request):
    """处理第三方登录 - 按照官方文档格式"""
    logger.info(f"[SSO Login] 收到请求: {request.method}")
    logger.info(f"[SSO Login] 请求头: {dict(request.headers)}")
    logger.info(f"[SSO Login] POST数据: {dict(request.POST)}")

    if not request.POST:
        logger.error("[SSO Login] 无POST数据")
        return JsonResponse({
            'iCode': -700,
            'sMsg': '第三方服务器返回参数出现错误',
            'sToken': ''
        }, status=400)

    try:
        username = request.POST.get('sUserName')
        encryptedAesKey = request.POST.get('sEncryptedAESKey')
        encryptedPassword = request.POST.get('sPassword')

        if not all([username, encryptedAesKey, encryptedPassword]):
            logger.error("[SSO Login] 缺少必要参数")
            return JsonResponse({
                'iCode': -700,
                'sMsg': '第三方服务器返回参数出现错误',
                'sToken': ''
            }, status=400)

        logger.info(f"username: {username}")
        logger.info(f"encryptedAesKey: {encryptedAesKey}")
        logger.info(f"encryptedPassword: {encryptedPassword}")

        aesKey = cipherFunctions.RSA_Decrypt(cipher_text=encryptedAesKey.encode("utf-8"), private_key=params.RSA_PRIVATE_KEY).decode(
            "utf-8")
        logger.info(f"aesKey: {aesKey}")
        password = cipherFunctions.AES_Decrypt(key=aesKey.encode("utf-8"),
                                    cipher=encryptedPassword.encode("utf-8")).decode("utf-8")

        # aesKey = cipherFunctions.RSA_Decrypt(encryptedAesKey, params.RSA_PRIVATE_KEY)
        # password = cipherFunctions.AES_Decrypt(aesKey, encryptedPassword)
        logger.info(f"password: {password}")

        try:
            # sUserName既是username又是email
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.error(f"[SSO Login] 用户不存在: username={username}")
            return JsonResponse({
                'iCode': -800,
                'sMsg': '用户名或者密码错误',
                'sToken': ''
            }, status=401)

        if user.check_password(password):
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"[SSO Login] 登录成功: username={username}")
            return JsonResponse({
                'iCode': 0,
                'sMsg': '登录成功',
                'sToken': token.key
            })
        else:
            logger.error(f"[SSO Login] 密码错误: username={username}")
            return JsonResponse({
                'iCode': -800,
                'sMsg': '用户名或者密码错误',
                'sToken': ''
            }, status=401)

    except Exception as e:
        logger.error(f"[SSO Login] 服务器异常: {str(e)}")
        return JsonResponse({
            'iCode': -900,
            'sMsg': '第三方服务器异常',
            'sToken': ''
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def sso_register_view(request):
    """处理第三方注册 - 按照官方文档格式"""
    logger.info(f"[SSO Register] 收到请求: {request.method}")
    logger.info(f"[SSO Register] 请求头: {dict(request.headers)}")
    logger.info(f"[SSO Register] POST数据: {dict(request.POST)}")

    if not request.POST:
        logger.error("[SSO Register] 无POST数据")
        return JsonResponse({
            'iCode': -700,
            'sMsg': '第三方服务器返回参数出现错误',
            'sToken': ''
        }, status=400)

    try:
        username = request.POST.get('sUserName')
        encryptedAesKey = request.POST.get('sEncryptedAESKey')
        encryptedPassword = request.POST.get('sPassword')

        if not all([username, encryptedAesKey, encryptedPassword]):
            logger.error("[SSO Register] 缺少必要参数")
            return JsonResponse({
                'iCode': -700,
                'sMsg': '第三方服务器返回参数出现错误',
                'sToken': ''
            }, status=400)

        logger.info(f"username: {username}")
        logger.info(f"encryptedAesKey: {encryptedAesKey}")
        logger.info(f"encryptedPassword: {encryptedPassword}")

        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            logger.error(f"[SSO Register] 用户名已存在: username={username}")
            return JsonResponse({
                'iCode': -801,
                'sMsg': '用户名已经存在',
                'sToken': ''
            }, status=400)

        aesKey = cipherFunctions.RSA_Decrypt(cipher_text=encryptedAesKey.encode("utf-8"), private_key=params.RSA_PRIVATE_KEY).decode(
            "utf-8")
        # aesKey = cipherFunctions.RSA_Decrypt(encryptedAesKey, params.RSA_PRIVATE_KEY)
        logger.info(f"aesKey: {aesKey}")

        # 使用多编码方式解密密码，处理编码问题
        # password = cipherFunctions.AES_Decrypt(aesKey, encryptedPassword)
        password = cipherFunctions.AES_Decrypt(key=aesKey.encode("utf-8"),
                                    cipher=encryptedPassword.encode("utf-8")).decode("utf-8")
        logger.info(f"password: {password}")

        # sUserName既是username又是email
        user = User.objects.create_user(username=username, email=username, password=password)
        token, created = Token.objects.get_or_create(user=user)

        logger.info(f"[SSO Register] 注册成功: username={username}")
        return JsonResponse({
            'iCode': 0,
            'sMsg': '注册成功',
            'sToken': token.key
        })

    except Exception as e:
        logger.error(f"[SSO Register] 服务器异常: {str(e)}")
        return JsonResponse({
            'iCode': -900,
            'sMsg': '第三方服务器异常',
            'sToken': ''
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def sso_reset_password_view(request):
    """处理第三方密码重置 - 按照官方文档格式"""
    logger.info(f"[SSO Reset Password] 收到请求: {request.method}")
    logger.info(f"[SSO Reset Password] 请求头: {dict(request.headers)}")
    logger.info(f"[SSO Reset Password] POST数据: {dict(request.POST)}")

    if not request.POST:
        logger.error("[SSO Reset Password] 无POST数据")
        return JsonResponse({
            'iCode': -700,
            'sMsg': '第三方服务器返回参数出现错误',
            'sToken': ''
        }, status=400)

    try:
        username = request.POST.get('username')
        encryptedAesKey = request.POST.get('encryptedAESKey')
        encryptedPassword = request.POST.get('password')
        encryptedNewPassword = request.POST.get('newPassword')

        if not all([username, encryptedAesKey, encryptedPassword, encryptedNewPassword]):
            logger.error("[SSO Reset Password] 缺少必要参数")
            return JsonResponse({
                'iCode': -700,
                'sMsg': '第三方服务器返回参数出现错误',
                'sToken': ''
            }, status=400)

        aesKey = cipherFunctions.RSA_Decrypt(encryptedAesKey, params.RSA_PRIVATE_KEY)
        password = cipherFunctions.AES_Decrypt(aesKey, encryptedPassword)
        newPassword = cipherFunctions.AES_Decrypt(aesKey, encryptedNewPassword)

        try:
            # sUserName既是username又是email
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.error(f"[SSO Reset Password] 用户不存在: username={username}")
            return JsonResponse({
                'iCode': -800,
                'sMsg': '用户名或者密码错误',
                'sToken': ''
            }, status=401)

        if user.check_password(password):
            user.set_password(newPassword)
            user.save()

            # 清除用户的缓存数据
            cache_key = f'user_profile_{user.id}'
            cache.delete(cache_key)

            # 生成新的token
            token, created = Token.objects.get_or_create(user=user)

            logger.info(f"[SSO Reset Password] 密码修改成功: username={username}")
            return JsonResponse({
                'iCode': 0,
                'sMsg': '密码修改成功',
                'sToken': token.key
            })
        else:
            logger.error(f"[SSO Reset Password] 旧密码错误: username={username}")
            return JsonResponse({
                'iCode': -800,
                'sMsg': '用户名或者密码错误',
                'sToken': ''
            }, status=401)

    except Exception as e:
        logger.error(f"[SSO Reset Password] 服务器异常: {str(e)}")
        return JsonResponse({
            'iCode': -900,
            'sMsg': '第三方服务器异常',
            'sToken': ''
        }, status=500)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


@csrf_exempt
@require_http_methods(["GET"])
def sso_success_view(request):
    """
    处理第三方重定向成功页面 - 在URL中传递token供前端使用
    """
    try:
        # 获取token参数（第三方服务重定向时带的参数）
        token_key = request.GET.get('sToken')

        if not token_key:
            return JsonResponse({'error': 'missing_token'}, status=400)

        # 直接通过token验证用户
        try:
            token = Token.objects.get(key=token_key)
            user = token.user

            # 重定向到配置的成功页面，在URL中包含token和用户信息
            redirect_url = getattr(settings, 'REDIRECT_URL', 'https://gfy.denglu1.cn')

            # 在重定向URL中添加token、用户名和用户ID参数
            redirect_with_token = f"{redirect_url}?token={token.key}&username={user.username}&user_id={user.id}"
            logger.info(f"redirect_with_token: {redirect_with_token}")
            return HttpResponseRedirect(redirect_with_token)

        except Token.DoesNotExist:
            return JsonResponse({'error': 'invalid_token'}, status=401)

    except Exception as e:
        return JsonResponse({'error': 'system_error'}, status=500)