from django.conf.urls import patterns, url

from badgeuser.api import BadgeUserToken, BadgeUserProfile, BadgeUserEmailList, BadgeUserEmailDetail, BadgeUserForgotPassword, \
    BadgeUserEmailConfirm

urlpatterns = patterns('badgeuser.api_views',
    url(r'^/auth-token$', BadgeUserToken.as_view(), name='user_auth_token'),
    url(r'^/profile$', BadgeUserProfile.as_view(), name='user_profile'),
    url(r'^/forgot-password$', BadgeUserForgotPassword.as_view(), name='user_forgot_password'),
    url(r'^/emails$', BadgeUserEmailList.as_view(), name='api_user_emails'),
    url(r'^/emails/(?P<id>[^/]+)$', BadgeUserEmailDetail.as_view(), name='api_user_email_detail'),
    url(r'^/legacyconfirmemail/(?P<confirm_id>[^/]+)$', BadgeUserEmailConfirm.as_view(), name='legacy_user_email_confirm'),
    url(r'^/confirmemail/(?P<confirm_id>[^/]+)$', BadgeUserEmailConfirm.as_view(), name='api_user_email_confirm')
)
