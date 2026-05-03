from config.celery import app


@app.task
def generate_report_task(report_id):
    return report_id
