from app import create_app, db
from app.models import User, Advertiser, SpendingData, Activity, LeadStatusHistory, Attachment

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Advertiser': Advertiser,
        'SpendingData': SpendingData,
        'Activity': Activity,
        'LeadStatusHistory': LeadStatusHistory,
        'Attachment': Attachment
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)