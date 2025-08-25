from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.utils import timezone
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, LoginSerializer

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

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]