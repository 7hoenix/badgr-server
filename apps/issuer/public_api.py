import os

import StringIO
import cairosvg
from PIL import Image
from django.core.files.storage import DefaultStorage
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import RedirectView

from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import AbstractIssuerAPIEndpoint
from .models import Issuer, BadgeClass, BadgeInstance
from .renderers import BadgeInstanceHTMLRenderer, BadgeClassHTMLRenderer, IssuerHTMLRenderer

import utils
import badgrlog

logger = badgrlog.BadgrLogger()


class JSONComponentView(AbstractIssuerAPIEndpoint):
    """
    Abstract Component Class
    """
    permission_classes = (permissions.AllowAny,)
    html_renderer_class = None

    def log(self, obj):
        pass

    def get(self, request, slug, format='html'):
        try:
            self.current_object = self.model.cached.get(slug=slug)
        except self.model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            self.log(self.current_object)
            return Response(self.current_object.json)

    def get_renderers(self):
        """
        Instantiates and returns the list of renderers that this view can use.
        """
        HTTP_USER_AGENTS = ['LinkedInBot',]
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')

        if self.request.META.get('HTTP_ACCEPT') == '*/*' or \
                len([agent for agent in HTTP_USER_AGENTS if agent in user_agent]):
            return [self.get_html_renderer_class()(), ]

        return [renderer() for renderer in self.renderer_classes]

    def get_html_renderer_class(self):
        return self.html_renderer_class


class ComponentPropertyDetailView(APIView):
    """
    Abstract Component Class
    """
    permission_classes = (permissions.AllowAny,)

    def log(self, obj):
        pass

    def get(self, request, slug):
        try:
            current_object = self.model.cached.get(slug=slug)
        except self.model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            self.log(current_object)

        p = getattr(current_object, self.prop)
        if not bool(p):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return redirect(p.url)


class ImagePropertyDetailView(ComponentPropertyDetailView):
    """
    a subclass of ComponentPropertyDetailView, for image fields, if query_param type='png' re-encode if necessary
    """
    def get(self, request, slug):
        try:
            current_object = self.model.cached.get(slug=slug)
        except self.model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            self.log(current_object)

        image_prop = getattr(current_object, self.prop)
        if not bool(image_prop):
            return Response(status=status.HTTP_404_NOT_FOUND)

        image_type = request.query_params.get('type', 'original')
        if image_type not in ['original', 'png']:
            raise ValidationError(u"invalid image type: {}".format(image_type))

        image_url = image_prop.url
        filename, ext = os.path.splitext(image_prop.name)
        basename = os.path.basename(filename)
        dirname = os.path.dirname(filename)
        new_name = '{dirname}/converted/{basename}.png'.format(dirname=dirname, basename=basename)
        storage = DefaultStorage()

        if image_type == 'original':
            image_url = image_prop.url
        elif image_type == 'png' and ext == '.svg':
            if not storage.exists(new_name):
                with storage.open(image_prop.name, 'rb') as input_svg:
                    out_buf = StringIO.StringIO()
                    cairosvg.svg2png(file_obj=input_svg, write_to=out_buf)
                    storage.save(new_name, out_buf)
            image_url = storage.url(new_name)
        else:
            # attempt to use PIL to do desired image conversion
            if not storage.exists(new_name):
                with storage.open(image_prop.name, 'rb') as input_svg:
                    out_buf = StringIO.StringIO()
                    img = Image.open(input_svg)
                    img.save(out_buf, format=image_type)
                    storage.save(new_name, out_buf)
            image_url = storage.url(new_name)

        return redirect(image_url)


class IssuerJson(JSONComponentView):
    """
    GET the actual OBI badge object for an issuer via the /public/issuers/ endpoint
    """
    model = Issuer
    renderer_classes = (JSONRenderer, IssuerHTMLRenderer,)
    html_renderer_class = IssuerHTMLRenderer

    def log(self, obj):
        logger.event(badgrlog.IssuerRetrievedEvent(obj, self.request))

    def get_renderer_context(self, **kwargs):
        context = super(IssuerJson, self).get_renderer_context(**kwargs)
        if getattr(self, 'current_object', None):
            context['issuer'] = self.current_object
            context['badge_classes'] = self.current_object.cached_badgeclasses()
        return context


class IssuerImage(ImagePropertyDetailView):
    """
    GET an image that represents an Issuer
    """
    model = Issuer
    prop = 'image'

    def log(self, obj):
        logger.event(badgrlog.IssuerImageRetrievedEvent(obj, self.request))


class BadgeClassJson(JSONComponentView):
    """
    GET the actual OBI badge object for a badgeclass via public/badges/:slug endpoint
    """
    model = BadgeClass
    renderer_classes = (JSONRenderer, BadgeClassHTMLRenderer,)
    html_renderer_class = BadgeClassHTMLRenderer

    def get_renderer_context(self, **kwargs):
        context = super(BadgeClassJson, self).get_renderer_context(**kwargs)
        if getattr(self, 'current_object', None):
            context['badge_class'] = self.current_object
            context['issuer'] = self.current_object.cached_issuer
        return context

    def log(self, obj):
        logger.event(badgrlog.BadgeClassRetrievedEvent(obj, self.request))


class BadgeClassImage(ImagePropertyDetailView):
    """
    GET the unbaked badge image from a pretty url instead of media path
    """
    model = BadgeClass
    prop = 'image'

    def log(self, obj):
        logger.event(badgrlog.BadgeClassImageRetrievedEvent(obj, self.request))


class BadgeClassCriteria(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        try:
            badge_class = BadgeClass.cached.get(slug=kwargs.get('slug'))
        except BadgeClass.DoesNotExist:
            raise Http404
        return badge_class.get_absolute_url()


class BadgeInstanceJson(JSONComponentView):
    model = BadgeInstance
    renderer_classes = (JSONRenderer, BadgeInstanceHTMLRenderer,)
    html_renderer_class = BadgeInstanceHTMLRenderer

    def get_renderer_context(self, **kwargs):
        context = super(BadgeInstanceJson, self).get_renderer_context()
        if getattr(self, 'current_object', None):
            context['badge_instance'] = self.current_object
            context['badge_class'] = self.current_object.cached_badgeclass
            context['issuer'] = self.current_object.cached_issuer

        return context

    def get(self, request, slug, format='html'):
        try:
            current_object = self.model.cached.get(slug=slug)
            self.current_object = current_object
        except self.model.DoesNotExist:
            return Response("Requested assertion not found.", status=status.HTTP_404_NOT_FOUND)
        else:
            if current_object.revoked is False:

                logger.event(badgrlog.BadgeAssertionCheckedEvent(current_object, request))
                return Response(current_object.json)
            else:
                # TODO update terms based on final accepted terms in response to
                # https://github.com/openbadges/openbadges-specification/issues/33
                revocation_info = {
                    '@context': utils.CURRENT_OBI_CONTEXT_IRI,
                    'id': current_object.get_full_url(),
                    'revoked': True,
                    'revocationReason': current_object.revocation_reason
                }

                logger.event(badgrlog.RevokedBadgeAssertionCheckedEvent(current_object, request))
                return Response(revocation_info, status=status.HTTP_410_GONE)


class BadgeInstanceImage(ComponentPropertyDetailView):
    model = BadgeInstance
    prop = 'image'

    def log(self, badge_instance):
        logger.event(badgrlog.BadgeInstanceDownloadedEvent(badge_instance, self.request))

    def get(self, request, slug):
        try:
            current_object = self.model.cached.get(slug=slug)
        except self.model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            if current_object.revoked:
                return Response(status=status.HTTP_404_NOT_FOUND)

            self.log(current_object)
            return redirect(getattr(current_object, self.prop).url)

