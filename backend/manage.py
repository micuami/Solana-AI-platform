# manage.py (place în proiect root, same level as backend/)
from backend.main import create_app
from backend.externals import db
from flask_migrate import Migrate

# apelează create_app() fără argumente → va folosi DevConfig din configuration_classes_for_flask
app = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run(debug=True)
# rulează serverul Flask în mod debug când execuți direct manage.py