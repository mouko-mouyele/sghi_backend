from ninja import Router



from api.routers.admin_router import router as admin_router

from api.routers.auth_router import router as auth_router

from api.routers.billing_router import router as billing_router

from api.routers.clinical_router import router as clinical_router

from api.routers.dashboard_router import router as dashboard_router

from api.routers.hr_router import router as hr_router

from api.routers.lab_router import router as lab_router

from api.routers.patient_router import router as patient_router

from api.routers.pharmacy_router import router as pharmacy_router

from api.schemas import HealthOut

from django.conf import settings

from django.db import connection



router = Router(tags=['SGHL API v1'])





@router.get('/sante', response=HealthOut, auth=None)

def health_check(request):

    db_ok = 'ok'

    try:

        connection.ensure_connection()

    except Exception:

        db_ok = 'error'

    return {

        'status': 'healthy' if db_ok == 'ok' else 'degraded',

        'version': getattr(settings, 'API_VERSION', 'v1'),

        'database': db_ok,

    }





router.add_router('/auth', auth_router)

router.add_router('', admin_router)

router.add_router('', clinical_router)

router.add_router('', dashboard_router)

router.add_router('', hr_router)

router.add_router('/laboratoire', lab_router)

router.add_router('', patient_router)

router.add_router('/pharmacie', pharmacy_router)

router.add_router('/finances', billing_router)


