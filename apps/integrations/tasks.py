from config.celery import app


@app.task
def sync_api_connection_task(connection_id):
    return {"connection_id": connection_id, "status": "placeholder"}
