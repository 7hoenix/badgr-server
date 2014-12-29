from django import forms
from issuer.models import EarnerNotification, Issuer
from badgeanalysis.models import OpenBadge
from badgeanalysis.validation_messages import BadgeValidationError

class IssuerForm(forms.ModelForm):

    class Meta:
        model = Issuer
        exclude = []


class NotifyEarnerForm(forms.ModelForm):

    class Meta:
        model = EarnerNotification
        exclude = []

    def clean_url(self):
        import pdb; pdb.set_trace();
        try:
            EarnerNotification.objects.get(url=self.cleaned_data['url'])

        except EarnerNotification.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(
                "The earner of this assertion has already been notified: %(url)s",
                code='invalid',
                params={'url': self.cleaned_data['url']}
            )
        return self.cleaned_data['url']

    def clean(self):
        import pdb; pdb.set_trace();
        cleaned_data = super(NotifyEarnerForm, self).clean()
        if not self.errors.get('url') and not self.errors.get('email'):
            try:
                cleaned_data['badge'] = OpenBadge(recipient_input=cleaned_data['email'], badge_input=cleaned_data['url'])
                cleaned_data['badge'].save()
            except BadgeValidationError as e:
                raise forms.ValidationError(e.to_dict()['message'], code='invalid')
            # except Exception as e:
            #     raise e
                # raise forms.ValidationError(e.message, code='unknown')
            else:
                pass

        return cleaned_data
