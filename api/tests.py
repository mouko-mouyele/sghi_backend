import pytest
from django.contrib.auth import get_user_model
from ninja.testing import TestClient

from api.api import api

User = get_user_model()
client = TestClient(api)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='testadmin',
        password='Test@12345678',
        role='ADMIN',
        is_staff=True,
    )


@pytest.mark.django_db
def test_health_endpoint():
    response = client.get('/v1/sante')
    assert response.status_code == 200
    assert response.json()['database'] == 'ok'


@pytest.mark.django_db
def test_login_and_me(admin_user):
    login = client.post('/v1/auth/login', json={
        'username': 'testadmin',
        'password': 'Test@12345678',
    })
    assert login.status_code == 200
    data = login.json()
    assert 'access_token' in data
    assert data['role'] == 'ADMIN'

    me = client.get('/v1/auth/me', headers={'Authorization': f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()['username'] == 'testadmin'


@pytest.mark.django_db
def test_patient_register():
    response = client.post('/v1/auth/register/patient', json={
        'username': 'patient_test',
        'password': 'Patient@Test123',
        'email': 'patient@example.com',
        'nom': 'Dupont',
        'prenom': 'Marie',
        'date_naissance': '1995-06-15',
        'sexe': 'F',
        'telephone': '06 123 45 67',
        'consentement_traitement': True,
    })
    assert response.status_code == 200
    assert response.json()['role'] == 'PATIENT'


@pytest.mark.django_db
def test_dashboard_requires_auth():
    assert client.get('/v1/dashboard/kpis').status_code == 401
