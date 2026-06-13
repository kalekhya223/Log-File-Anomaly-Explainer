from app import app

def test_home_page():
    tester = app.test_client()
    response = tester.get('/')

    assert response.status_code == 200

def test_upload_page():
    tester = app.test_client()
    response = tester.get('/upload')

    assert response.status_code == 200
