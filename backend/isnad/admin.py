from django import forms
from django.contrib import admin

from .collection_scope import BUKHARI_TITLES, is_bukhari_reference
from .models import Hadith, Narrator, TransmissionEdge


class HadithForm(forms.ModelForm):
    book_title = forms.ChoiceField(choices=[(title, title) for title in BUKHARI_TITLES])

    def clean_reference_url(self):
        reference = self.cleaned_data["reference_url"]
        if reference and not is_bukhari_reference(reference):
            raise forms.ValidationError("Expected a Sunnah.com Bukhari reference.")
        return reference


@admin.register(Hadith)
class HadithAdmin(admin.ModelAdmin):
    form = HadithForm

    def get_queryset(self, request):
        return super().get_queryset(request).filter(book_title__in=BUKHARI_TITLES)


@admin.register(TransmissionEdge)
class TransmissionEdgeAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(hadith__book_title__in=BUKHARI_TITLES)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "hadith":
            kwargs["queryset"] = Hadith.objects.using(kwargs.get("using")).filter(book_title__in=BUKHARI_TITLES)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Narrator)
