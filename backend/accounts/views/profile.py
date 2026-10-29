from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny

from accounts.serializers.profile import MeSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    
    def get_object(self):
        return self.request.user