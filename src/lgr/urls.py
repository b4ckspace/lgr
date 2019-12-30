from django.contrib import admin
from django.urls import path, include

from lgr import views
from lgr.drf import router


urlpatterns = [
    path('', views.index, name='index'),
    path('auth', views.auth, name='auth'),
    path('loan', views.loan, name='loan'),
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
]
