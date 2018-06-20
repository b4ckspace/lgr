from django import forms
from django.utils.html import format_html

from lgr import models
from lgr import validators


class ReturnForm(forms.Form):
    CHOICES = []

    loan_pk = forms.IntegerField(widget=forms.HiddenInput)
    items = forms.MultipleChoiceField(required=True, choices=CHOICES,
                                      widget=forms.CheckboxSelectMultiple)
    comment = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, loan=None, **kwargs):
        super().__init__(*args, **kwargs)
        if loan:
            self.CHOICES = [(b.pk, b.__str__) for b in loan.barcodes.all()]
            self.fields['loan_pk'].initial = loan.pk
            self.fields['items'].choices = self.CHOICES


class BarcodeMoveintoForm(forms.Form):
    barcodes = forms.CharField(
        widget=forms.Textarea,
        help_text=format_html('Enter one barcode per line.')
    )

    def clean_barcodes(self):
        text = self.cleaned_data['barcodes']
        as_barcodes = [models.Barcode.objects.filter(pk=b).first()
                    for b in text.splitlines()]
        return as_barcodes


class BarcodeQuickaddForm(forms.Form):
    barcodes = forms.CharField(
        widget=forms.Textarea,
        help_text=format_html(
            'Ident barcodes by two spaces for parent/child relationships.<br/>'
            'Format: Either "# owner" or "barcode:item:barcode description"'
        )
    )

    def clean_barcodes(self):
        barcodes = self.cleaned_data['barcodes']
        return validators.barcode_quickadd(barcodes)


def move_multiple_inject(form):
    '''injects fields for move_multiple django admin page'''
    form.fields.update({
        'action': forms.CharField(widget=forms.HiddenInput, initial='move_multiple'),
        'apply': forms.BooleanField(widget=forms.HiddenInput, initial=True),
    })
    return form
