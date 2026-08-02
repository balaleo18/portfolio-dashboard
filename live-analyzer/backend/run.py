import os
import sys
import uvicorn

# Add project root to python path to resolve 'backend' imports correctly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.config import settings


if __name__ == "__main__":
    print(f"Starting backend on {settings.BIND_IP}:{settings.PORT}")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.BIND_IP,
        port=settings.PORT,
        reload=True
    )
