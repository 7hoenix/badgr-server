from django.conf.urls import url

from .api import (IssuerList, IssuerDetail, IssuerStaffList,
                  BadgeClassList, BadgeClassDetail, BadgeInstanceList,
                  BadgeInstanceDetail, FindBadgeClassDetail, IssuerBadgeInstanceList,
                  AllBadgeClassesList, BatchAssertions)


urlpatterns = [
    # url(r'^$', RedirectView.as_view(url='/v1/issuer/issuers', permanent=False)),

    url(r'^all-badges$', AllBadgeClassesList.as_view(), name='v1_api_issuer_all_badges_list'),
    url(r'^all-badges/find$', FindBadgeClassDetail.as_view(), name='v1_api_find_badgeclass_by_identifier'),

    url(r'^issuers$', IssuerList.as_view(), name='v1_api_issuer_list'),
    url(r'^issuers/(?P<slug>[-\w]+)$', IssuerDetail.as_view(), name='v1_api_issuer_detail'),
    url(r'^issuers/(?P<slug>[-\w]+)/staff$', IssuerStaffList.as_view(), name='v1_api_issuer_staff'),
    url(r'^issuers/(?P<issuerSlug>[-\w]+)/assertions$', IssuerBadgeInstanceList.as_view(), name='v1_api_issuer_instance_list'),

    url(r'^issuers/(?P<issuerSlug>[-\w]+)/badges$', BadgeClassList.as_view(), name='v1_api_badgeclass_list'),
    url(r'^issuers/(?P<issuerSlug>[-\w]+)/badges/(?P<badgeSlug>[-\w]+)$', BadgeClassDetail.as_view(), name='v1_api_badgeclass_detail'),

    url(r'^issuers/(?P<issuerSlug>[-\w]+)/badges/(?P<badgeSlug>[-\w]+)/batchAssertions$', BatchAssertions.as_view(), name='v1_api_badgeclass_batchissue'),

    url(r'^issuers/(?P<issuerSlug>[-\w]+)/badges/(?P<badgeSlug>[-\w]+)/assertions$', BadgeInstanceList.as_view(), name='v1_api_badgeinstance_list'),
    url(r'^issuers/(?P<issuerSlug>[-\w]+)/badges/(?P<badgeSlug>[-\w]+)/assertions/(?P<assertionSlug>[-\w]+)$', BadgeInstanceDetail.as_view(), name='v1_api_badgeinstance_detail'),
]
