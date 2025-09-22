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
        signup_response = self.client.post('/auth/signup', 
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

        # json = login_response.json

        # print(json)

        self.assertEqual(status_code, 200)

    def test_get_all_databases(self):
        """ Test getting all databases """
        response = self.client.get('/databases/databases')

        # print(response.json)

        status_code = response.status_code

        self.assertEqual(status_code, 200)
        
    def test_get_one_database(self):
        id = 1
        response = self.client.get(f'/databases/databases/{id}')

        status_code = response.status_code
        # print(status_code)

        self.assertEqual(status_code, 404)  # Nu exista inca nicio baza de date

    def test_upload_database(self):
        signup_response = self.client.post('/auth/signup', 
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
        
        acces_token = login_response.json["access token"]

        upload_database_response = self.client.post('/databases/databases/upload',
            data={
                "name": "Test Database",    
                "model_name": "gpt-3.5-turbo",
                "purpose": "Test purpose",
                "file": (io.BytesIO(b"dummy content"), "test.txt"),
                "description": "Test description",
                "user_id": 1
            },
            headers={
                "Authorization": f"Bearer {acces_token}"
            }
        )

        status_code = upload_database_response.status_code

        # print(upload_database_response.json)

        self.assertEqual(status_code, 201)


    def test_delete_database(self):
        signup_response = self.client.post('/auth/signup', 
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
        
        access_token = login_response.json["access token"]


        upload_database_response = self.client.post('/databases/databases/upload',
            data={
                "name": "Test Database",    
                "model_name": "gpt-3.5-turbo",
                "purpose": "Test purpose",
                "file": (io.BytesIO(b"dummy content"), "test.txt"),
                "description": "Test description",
                "user_id": str(1),
            },
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        # print(upload_database_response.json)

        id = upload_database_response.json["id"]
        # print("Database ID:", id)

        delete_database_response = self.client.delete(
                f'/databases/databases/{id}',
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