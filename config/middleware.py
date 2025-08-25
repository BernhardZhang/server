import json
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class JSONLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log incoming JSON requests and outgoing JSON responses
    """
    
    def process_request(self, request):
        """Log incoming JSON requests"""
        # 跳过静态文件和管理员路径的日志记录
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return None
            
        if request.content_type == 'application/json' and hasattr(request, 'body'):
            try:
                body = request.body.decode('utf-8')
                if body:
                    json_data = json.loads(body)
                    print(f"\n=== INCOMING JSON REQUEST ===")
                    print(f"Method: {request.method}")
                    print(f"Path: {request.path}")
                    print(f"Content-Type: {request.content_type}")
                    print(f"JSON Data:")
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
                    print("=" * 30)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"\n=== INCOMING REQUEST (Invalid JSON) ===")
                print(f"Method: {request.method}")
                print(f"Path: {request.path}")
                print(f"Error: {e}")
                print("=" * 30)
        return None
    
    def process_response(self, request, response):
        """Log outgoing JSON responses"""
        # 跳过静态文件和管理员路径的日志记录
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return response
            
        if response.get('Content-Type', '').startswith('application/json'):
            try:
                # Get response content
                content = response.content.decode('utf-8')
                if content:
                    json_data = json.loads(content)
                    print(f"\n=== OUTGOING JSON RESPONSE ===")
                    print(f"Status Code: {response.status_code}")
                    print(f"Path: {request.path}")
                    print(f"Content-Type: {response.get('Content-Type')}")
                    print(f"JSON Data:")
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
                    print("=" * 30)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"\n=== OUTGOING RESPONSE (Invalid JSON) ===")
                print(f"Status Code: {response.status_code}")
                print(f"Path: {request.path}")
                print(f"Error: {e}")
                print("=" * 30)
        return response