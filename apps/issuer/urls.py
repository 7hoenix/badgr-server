from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from issuer.views import *

urlpatterns = patterns('issuer.views',
    url(r'/create$', login_required(IssuerCreate.as_view()), name='issuer_create'),
    url(r'/(?P<pk>\d+)', IssuerDetail.as_view(), name='issuer_detail'),
    url(r'/notifications$', EarnerNotificationCreate.as_view(), name='notify_earner')
)
