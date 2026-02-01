# run.py
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting AutoCare Connect API...")
    print("📡 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )