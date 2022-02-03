import uvicorn

import funcx_container_service

if __name__ == "__main__":
    uvicorn.run(funcx_container_service.app, host="0.0.0.0", port=8000)
