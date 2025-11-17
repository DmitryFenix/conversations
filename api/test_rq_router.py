"""
Временный скрипт для проверки подключения роутера
"""
import sys
sys.path.insert(0, '/app')

try:
    from rq_dashboard import router
    print(f"✓ Router imported successfully")
    print(f"Router prefix: {router.prefix}")
    print(f"Router routes:")
    for route in router.routes:
        if hasattr(route, 'path'):
            print(f"  - {route.path} ({route.methods if hasattr(route, 'methods') else 'N/A'})")
except Exception as e:
    print(f"✗ Failed to import router: {e}")
    import traceback
    traceback.print_exc()


