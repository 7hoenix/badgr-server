# Created by wiggins@concentricsky.com on 3/30/16.
from collections import OrderedDict

from django.conf import settings
from django.core.urlresolvers import reverse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from issuer.models import Issuer, BadgeClass
from pathway.completionspec import CompletionRequirementSpecFactory
from pathway.models import Pathway, PathwayElement


class PathwayListSerializer(serializers.Serializer):

    def to_representation(self, pathways):
        pathways_serializer = PathwaySerializer(pathways, many=True, context=self.context)
        return OrderedDict([
            ("@context", "https://badgr.io/public/contexts/pathways"),
            ("@type", "IssuerPathwayList"),
            ("pathways", pathways_serializer.data),
        ])


class PathwaySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=254, write_only=True)
    description = serializers.CharField(write_only=True)

    def to_representation(self, instance):
        issuer_slug = self.context.get('issuer_slug', None)
        if not issuer_slug:
            raise ValidationError("Invalid issuer_slug")

        representation = OrderedDict()

        if self.context.get('include_context', False):
            representation.update([
                ("@context", "https://badgr.io/public/contexts/pathways"),
                ("@type", "Pathway"),
            ])

        representation.update([
            ("@id", settings.HTTP_ORIGIN+reverse('pathway_detail', kwargs={'issuer_slug': issuer_slug, 'pathway_slug': instance.slug})),
            ('issuer', settings.HTTP_ORIGIN+reverse('issuer_json', kwargs={'slug': issuer_slug})),
            ('slug', instance.slug)
        ])
        if instance.root_element_id:
            representation.update([
                ('name', instance.cached_root_element.name),
                ('description', instance.cached_root_element.description),
                ('completionBadge', instance.cached_root_element.completion_badgeclass.slug if instance.cached_root_element.completion_badgeclass else None),
                ('elementCount', instance.pathwayelement_set.count()),
                ('rootChildCount', instance.cached_root_element.pathwayelement_set.count()),
            ])

        if self.context.get('include_structure', False):
            self.context.update({
                'pathway_slug': instance.slug,
            })
            element_serializer = PathwayElementSerializer(instance.cached_elements(), many=True, context=self.context)
            representation.update([
                ('rootElement', settings.HTTP_ORIGIN+reverse('pathway_element_detail', kwargs={
                    'issuer_slug': issuer_slug,
                    'pathway_slug': instance.slug,
                    'element_slug': instance.cached_root_element.slug})),
                ('elements', element_serializer.data)
            ])
        return representation

    def create(self, validated_data, **kwargs):
        issuer_slug = self.context.get('issuer_slug', None)
        if not issuer_slug:
            raise ValidationError("Could not determine issuer")
        try:
            issuer = Issuer.cached.get_by_slug_or_id(issuer_slug)
        except Issuer.DoesNotExist:
            raise ValidationError("Could not determine issuer")

        name = validated_data.get('name')

        pathway = Pathway(issuer=issuer)
        pathway.save(name_hint=name)
        root_element = PathwayElement(
            pathway=pathway,
            parent_element=None,
            name=name,
            description=validated_data.get('description'),
        )
        root_element.save()
        pathway.root_element = root_element
        pathway.save()
        return pathway


class PathwayElementSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    parent = serializers.CharField()
    alignmentUrl = serializers.CharField(required=False, allow_null=True)
    ordering = serializers.IntegerField(required=False, default=99)
    completionBadge = serializers.CharField(required=False, allow_null=True)
    requirements = serializers.CharField(required=False, allow_null=True)

    def to_representation(self, instance):
        issuer_slug = self.context.get('issuer_slug', None)
        if not issuer_slug:
            raise ValidationError("Invalid issuer_slug")
        pathway_slug = self.context.get('pathway_slug', None)
        if not pathway_slug:
            raise ValidationError("Invalid pathway_slug")

        include_requirements = self.context.get('include_requirements', True)
        representation = OrderedDict()
        representation.update([
            ('@id', instance.json_id),
            ('slug', instance.slug),
            ('name', instance.name),
            ('description', instance.description),
            ('alignmentUrl', instance.get_alignment_url()),
            ('ordering', instance.ordering),
            ('completionBadge', instance.completion_badgeclass.slug if instance.completion_badgeclass else None),
        ])

        representation['children'] = [
            child.json_id for child in instance.cached_children()
        ]

        if include_requirements and instance.completion_requirements:
            completion_serializer = PathwayElementCompletionSpecSerializer(instance.completion_requirements, context=self.context)
            representation['requirements'] = completion_serializer.data

        return representation

    def create(self, validated_data):
        pathway_slug = self.context.get('pathway_slug', None)
        if not pathway_slug:
            raise ValidationError("Could not determine pathway")
        try:
            pathway = Pathway.cached.get_by_slug_or_id(pathway_slug)
        except Pathway.DoesNotExist:
            raise ValidationError("Could not determine pathway")

        parent_slug = validated_data.get('parent')
        try:
            parent_element = PathwayElement.cached.get_by_slug_or_id(parent_slug)
        except PathwayElement.DoesNotExist:
            raise ValidationError("Invalid parent")
        else:
            if parent_element.pathway != pathway:
                raise ValidationError("Invalid parent")

        badge_slug = validated_data.get('completionBadge')
        completion_badge = None
        if badge_slug:
            try:
                completion_badge = BadgeClass.cached.get_by_slug_or_id(badge_slug)
            except BadgeClass.DoesNotExist:
                raise ValidationError("Invalid completionBadge")

        try:
            ordering = int(validated_data.get('ordering', 99))
        except ValueError:
            ordering = 99

        completion_requirements = None
        requirement_string = validated_data.get('requirements', None)
        if requirement_string:
            try:
                completion_requirements = CompletionRequirementSpecFactory.parse(requirement_string).serialize()
            except ValueError as e:
                raise ValidationError("Invalid completion spec: {}".format(e.message))

        element = PathwayElement(pathway=pathway,
                                 parent_element=parent_element,
                                 ordering=ordering,
                                 name=validated_data.get('name'),
                                 description=validated_data.get('description', None),
                                 alignment_url=validated_data.get('alignmentUrl', None),
                                 completion_badgeclass=completion_badge,
                                 completion_requirements=completion_requirements)
        element.save()
        return element


class PathwayElementCompletionSpecSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance


class RecipientCompletionSerializer(serializers.Serializer):
    def to_representation(self, instance):
        profile, completions = instance
        return OrderedDict([
            ('@id', profile.json_id),
            ('completions', completions)
        ])


class PathwayElementCompletionSerializer(serializers.Serializer):
    def to_representation(self, completions):
        issuer_slug = self.context.get('issuer_slug', None)
        if not issuer_slug:
            raise ValidationError("Invalid issuer_slug")
        pathway_slug = self.context.get('pathway_slug', None)
        if not pathway_slug:
            raise ValidationError("Invalid pathway_slug")
        element_slug = self.context.get('element_slug', None)
        if not element_slug:
            raise ValidationError("Invalid element_slug")

        completions_serializer = RecipientCompletionSerializer(completions.items(), many=True, context=self.context)

        return OrderedDict([
            ("@context", "https://badgr.io/public/contexts/pathways"),
            ("@type", "PathwayElementsCompletionReport"),
            ("rootElement", settings.HTTP_ORIGIN+reverse("pathway_element_detail", kwargs={
                'issuer_slug': issuer_slug,
                'pathway_slug': pathway_slug,
                'element_slug': element_slug
            })),
            ("recipientCompletions", completions_serializer.data),

        ])
