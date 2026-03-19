from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from accounts.models import Jadwal
from accounts.serializers import ScheduleOutSerializer
from accounts.utils.authenticate import CsrfExemptSessionAuthentication

@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def search_schedule(request):
    asal = request.query_params.get('asal')
    tujuan = request.query_params.get('tujuan')
    tanggal = request.query_params.get('tanggal') 

    jadwals = Jadwal.objects.filter(status='active').select_related('bus')

    if asal:
        jadwals = jadwals.filter(asal__icontains=asal)
    if tujuan:
        jadwals = jadwals.filter(tujuan__icontains=tujuan)
    if tanggal:
        jadwals = jadwals.filter(waktu_keberangkatan__date=tanggal)

    serializer = ScheduleOutSerializer(jadwals, many=True)
    return Response(serializer.data)