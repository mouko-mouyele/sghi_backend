from ninja import NinjaAPI

from api.v1 import router as v1_router

api = NinjaAPI(
    title='SGHL — Système de Gestion Hospitalière et de Laboratoire',
    version='1.0.0',
    description=(
        'API REST typée pour l\'ERP médical SGHL. '
        'Digitalisation du parcours patient, LIS, pharmacie, facturation et RH.'
    ),
    docs_url='/docs',
    openapi_url='/openapi.json',
)

api.add_router('/v1', v1_router)
