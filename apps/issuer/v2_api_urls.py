from django.conf.urls import url

from .api import (IssuerList, IssuerDetail, BadgeClassList, BadgeClassDetail, BadgeInstanceList,
                  BadgeInstanceDetail, IssuerBadgeInstanceList,
                  AllBadgeClassesList, BatchAssertions)

urlpatterns = [

    url(r'^issuers$', IssuerList.as_view(), name='v2_api_issuer_list'),
    url(r'^issuers/(?P<issuer_uri>[^/]+)$', IssuerDetail.as_view(), name='v2_api_issuer_detail'),
    url(r'^issuers/(?P<issuer_uri>[^/]+)/assertions$', IssuerBadgeInstanceList.as_view(), name='v2_api_issuer_assertion_list'),
    url(r'^issuers/(?P<issuer_uri>[^/]+)/badgeclasses$', BadgeClassList.as_view(), name='v2_api_issuer_badgeclass_list'),

    url(r'^badgeclasses$', AllBadgeClassesList.as_view(), name='v2_api_badgeclass_list'),
    url(r'^badgeclasses/(?P<badge_uri>[^/]+)$', BadgeClassDetail.as_view(), name='v2_api_badgeclass_detail'),
    url(r'^badgeclasses/(?P<badge_uri>[^/]+)/issue$', BatchAssertions.as_view(), name='v2_api_badgeclass_issue'),
    url(r'^badgeclasses/(?P<badge_uri>[^/]+)/assertions$', BadgeInstanceList.as_view(), name='v2_api_badgeclass_assertion_list'),

    url(r'^assertions/(?P<assertion_uri>[^/]+)$', BadgeInstanceDetail.as_view(), name='v2_api_assertion_detail'),
]
