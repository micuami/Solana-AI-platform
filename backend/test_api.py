import unittest
import io
from backend.main import create_app
from backend.configuration_classes_for_flask import TestConfig
from backend.externals import db

class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client(self)
        with self.app.app_context():
            db.create_all()

    def signup_and_login(self, username="testuser", email="testuser@test.com", password="password"):
        # helper to register and login, returns access_token and user_id
        signup_response = self.client.post('/auth/signup',
            json={
                "username": username,
                "email": email,
                "password": password
            })
        self.assertIn(signup_response.status_code, (200, 201))

        login_response = self.client.post('/auth/login',
            json={
                "identifier": username,
                "password": password
            })
        self.assertEqual(login_response.status_code, 200)
        data = login_response.get_json()
        access_token = data.get("access_token")
        user_id = data.get("user_id")
        return access_token, user_id

    def test_signup(self):
        signup_response = self.client.post('/auth/signup',
            json={
                "username": "testuser",
                "email": "testuser@test.com",
                "password": "password"
            })
        status_code = signup_response.status_code
        self.assertEqual(status_code, 201)

    def test_login(self):
        # ensure signup then login works
        self.client.post('/auth/signup',
            json={
                "username": "testuser",
                "email": "testuser@test.com",
                "password": "password"
            })

        login_response = self.client.post('/auth/login',
            json={
                "identifier": "testuser",
                "password": "password"
            })

        status_code = login_response.status_code
        self.assertEqual(status_code, 200)

    def test_get_all_databases(self):
        """ Test getting all databases """
        response = self.client.get('/databases/databases')
        status_code = response.status_code
        self.assertEqual(status_code, 200)

    def test_get_one_database(self):
        id = 1
        response = self.client.get(f'/databases/databases/{id}')
        status_code = response.status_code
        self.assertEqual(status_code, 404)  # Nu exista inca nicio baza de date

    def test_upload_database(self):
        access_token, user_id = self.signup_and_login()

        upload_database_response = self.client.post('/databases/databases/upload',
            data={
                "name": "Test Database",
                "model_name": "gpt-3.5-turbo",
                "purpose": "Test purpose",
                # 'file' must be a tuple (fileobj, filename) to be sent as multipart
                "file": (io.BytesIO(b"dummy content"), "test.txt"),
                "description": "Test description",
            },
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        status_code = upload_database_response.status_code
        # print(upload_database_response.get_json())
        self.assertEqual(status_code, 201)

    def test_delete_database(self):
        access_token, user_id = self.signup_and_login()

        upload_database_response = self.client.post('/databases/databases/upload',
            data={
                "name": "Test Database",
                "model_name": "gpt-3.5-turbo",
                "purpose": "Test purpose",
                "file": (io.BytesIO(b"dummy content"), "test.txt"),
                "description": "Test description",
            },
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        self.assertEqual(upload_database_response.status_code, 201)
        upload_json = upload_database_response.get_json()
        db_id = upload_json.get("id")
        self.assertIsNotNone(db_id)

        delete_database_response = self.client.delete(
            f'/databases/databases/{db_id}',
            headers={"Authorization": f"Bearer {access_token}"}
        )
        status_code = delete_database_response.status_code
        self.assertEqual(status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

if __name__ == '__main__':
    unittest.main()
