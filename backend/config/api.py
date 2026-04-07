from django.db import connections
from django.db.utils import OperationalError
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        db_status = "ok"
        overall_status = "ok"

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except OperationalError:
            db_status = "unavailable"
            overall_status = "degraded"

        status_code = 200 if overall_status == "ok" else 503
        return Response(
            {
                "status": overall_status,
                "services": {
                    "database": db_status,
                },
            },
            status=status_code,
        )
