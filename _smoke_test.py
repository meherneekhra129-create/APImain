"""Quick smoke test: verify the FastAPI app loads and all routes are registered."""
from app.main import app

print(f"App title: {app.title}")
print(f"Total routes: {len(app.routes)}")
print("\nAPI endpoints:")
for route in app.routes:
    path = getattr(route, "path", None)
    methods = getattr(route, "methods", None)
    if path and path.startswith("/api"):
        print(f"  {methods}  {path}")
