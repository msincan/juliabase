#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, datetime
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response
from chantal.samples import models
from django import forms
from django.forms.util import ValidationError
from django.utils.translation import ugettext as _, ugettext_lazy
import django.core.urlresolvers
import django.contrib.auth.models
from chantal.samples.views.utils import check_permission
from chantal.samples.views import utils

class SamplesForm(forms.Form):
    _ = ugettext_lazy
    sample_list = forms.ModelMultipleChoiceField(label=_(u"Samples"), queryset=None)
    def __init__(self, user_details, data=None, **keyw):
        u"""Form constructor.  I have to initialise a couple of things here in
        a non-trivial way, especially those that I have added myself
        (``sample_list`` and ``operator``).
        """
        deposition = keyw.get("instance")
        initial = keyw.get("initial", {})
        if deposition:
            # Mark the samples of the deposition in the choise field
            initial.update({"sample_list": [sample._get_pk_val() for sample in deposition.samples.all()]})
        keyw["initial"] = initial
        super(DepositionForm, self).__init__(data, **keyw)
        # FixMe: Maybe removing ".fields" would also work.  Affects some other
        # modules, too.
        self.fields["sample_list"].queryset = \
            models.Sample.objects.filter(Q(processes=deposition) | Q(watchers=user_details)).distinct() if deposition \
            else user_details.my_samples
        self.fields["sample_list"].widget.attrs.update({"size": "15", "style": "vertical-align: top"})
    def clean_sample_list(self):
        sample_list = list(set(self.cleaned_data["sample_list"]))
        if not sample_list:
            raise ValidationError(_(u"You must mark at least one sample."))
        return sample_list

class DepositionForm(forms.ModelForm):
    _ = ugettext_lazy
    operator = utils.OperatorChoiceField(label=_(u"Operator"), queryset=django.contrib.auth.models.User.objects.all())
    class Meta:
        model = models.LargeAreaDeposition
        exclude = ("external_operator",)

class LayerForm(forms.ModelForm):
    _ = ugettext_lazy
    class Meta:
        model = models.LargeAreaLayer
        exclude = ("deposition",)

class AddLayerForm(forms.Form):
    _ = ugettext_lazy
    number_of_layers_to_add = forms.IntegerField(label=_(u"Number of layers to be added"), min_value=0, required=False)
    def clean_number_of_layers_to_add(self):
        return utils.int_or_zero(self.cleaned_data["number_of_layers_to_add"])

class ChangeLayerForm(forms.Form):
    _ = ugettext_lazy
    duplicate_this_layer = forms.BooleanField(label=_(u"duplicate this layer"), required=False)
    remove_this_layer = forms.BooleanField(label=_(u"remove this layer"), required=False)
    def clean(self):
        if self.cleaned_data["duplicate_this_layer"] and self.cleaned_data["remove_this_layer"]:
            raise ValidationError(_(u"You can't duplicate and remove a layer at the same time."))
        return self.cleaned_data

class FormSet(object):
    deposition_prefix = u"%02dL-" % (datetime.date.today().year % 100)
    deposition_number_pattern = re.compile(ur"(?P<prefix>%s)(?P<number>\d+)$" % re.escape(deposition_prefix))
    def __init__(self, user, deposition_number):
        self.user = user
        self.user_details = self.user.get_profile()
        self.deposition = get_object_or_404(LargeAreaDeposition, number=deposition_number) if deposition_number else None
        self.deposition_form = self.add_layer_form = self.samples_form = None
        self.layer_forms = self.change_layer_forms = []
        self.post_data = None
    def from_post_data(self, post_data):
        self.post_data = post_data
        self.deposition_form = DepositionForm(self.post_data, instance=self.deposition)
        self.add_layer_form = AddLayerForm(self.post_data)
        self.samples_form = SamplesForm(self.user_details, self.post_data, instance=self.deposition)
        # FixMe: Normalisation is not necessary
        self.post_data, number_of_layers, __ = utils.normalize_prefixes(self.post_data)
        self.layer_forms = [LayerForm(self.post_data, prefix=str(layer_index)) for layer_index in range(number_of_layers)]
        self.change_layer_forms = [ChangeLayerForm(self.post_data, prefix=str(change_layer_index))
                                   for change_layer_index in range(number_of_layers)]
    def from_database(self):
        # FixMe: Duplication still missing
        if self.deposition:
            # Normal edit of existing deposition
            self.deposition_form = DepositionForm(instance=self.deposition)
            self.layer_forms, self.channel_form_lists = forms_from_database(self.deposition)
        else:
            # New deposition, or duplication has failed
            self.deposition_form = DepositionForm(initial={"number": utils.get_next_deposition_number("L-")})
            self.layer_forms, self.change_layer_forms = [], []
        self.add_layer_form = AddLayerForm()
        self.samples_form = SamplesForm(self.user_details, instance=self.deposition)
    def _change_structure(self):
        structure_changed = False
        new_layers = [("original", layer_form) for layer_form in self.layer_forms]

        # Duplicate layers
        for layer_form, change_layer_form in zip(self.layer_forms, self.change_layer_forms):
            if layer_form.is_valid() and \
                    change_layer_form.is_valid() and change_layer_form.cleaned_data["duplicate_this_layer"]:
                new_layers.append(("duplicate", layer_form))
                structure_changed = True

        # Add layers
        if self.add_layer_form.is_valid():
            for i in range(self.add_layer_form.cleaned_data["number_of_layers_to_add"]):
                new_layers.append(("new", None))
                structure_changed = True
            self.add_layer_form = AddLayerForm()

        # Delete layers
        for i in range(len(self.layer_forms)-1, -1, -1):
            if self.change_layer_forms[i].is_valid() and self.change_layer_forms[i].cleaned_data["remove_this_layer"]:
                del new_layers[i]
                structure_changed = True

        if structure_changed:
            next_full_number = utils.get_next_deposition_number("L-")
            deposition_number_match = self.deposition_number_pattern.match(next_full_number)
            next_layer_number = int(deposition_number_match.group("number"))
            old_prefixes = [int(layer_form.prefix) for layer_form in self.layer_forms if layer_form.is_bound]
            next_prefix = max(old_prefixes) + 1 if old_prefixes else 0
            self.layer_forms = []
            for new_layer in new_layers:
                if new_layer[0] == "original":
                    post_data = self.post_data.copy()
                    prefix = new_layer[1].prefix
                    post_data[prefix+"-number"] = utils.three_digits(next_layer_number)
                    next_layer_number += 1
                    self.layer_forms.append(LayerForm(post_data, prefix=prefix))
                elif new_layer[0] == "duplicate":
                    original_layer = self.layer_forms[new_layer[1]]
                    if original_layer.is_valid():
                        layer_data = original_layer.cleaned_data
                        layer_data["number"] = utils.three_digits(next_layer_number)
                        next_layer_number += 1
                        self.layer_forms.append(LayerForm(initial=layer_data, prefix=str(next_prefix)))
                        next_prefix += 1
                elif new_layer[0] == "new":
                    self.layer_forms.append(LayerForm(initial={"number": utils.three_digits(next_layer_number)},
                                                 prefix=str(next_prefix)))
                    next_layer_number += 1
                    next_prefix += 1
                else:
                    raise AssertionError("Wrong first field in new_layers structure: " + new_layer[0])
            post_data = self.post_data.copy()
            post_data["number"] = deposition_number_match.group("prefix") + \
                utils.three_digits(next_layer_number - 1 if self.layer_forms else next_layer_number)
            self.deposition_form = DepositionForm(post_data)

            self.change_layer_forms = []
            for layer_form in self.layer_forms:
                self.change_layer_forms.append(ChangeLayerForm(prefix=layer_form.prefix))
        return structure_changed
    def _is_all_valid(self):
        all_valid = True
        all_valid = self.deposition_form.is_valid()
        all_valid = self.add_layer_form.is_valid() and all_valid
        all_valid = self.samples_form.is_valid() and all_valid
        all_valid = all([layer_form.is_valid() for layer_form in self.layer_forms]) and all_valid
        all_valid = all([change_layer_form.is_valid() for change_layer_form in self.change_layer_forms]) and all_valid
        return all_valid
    def _is_referentially_valid(self):
        referentially_valid = True
        if not self.layer_forms:
            utils.append_error(self.deposition_form, _(u"No layers given."))
            referentially_valid = False
        if self.deposition_form.is_valid():
            match = deposition_number_pattern.match(self.deposition_form.cleaned_data["number"])
            if not match:
                utils.append_error(self.deposition_form, _(u"Invalid deposition number format."))
                referentially_valid = False
            else:
                number_only = match.group("number")
                deposition_numbers = models.LargeAreaDeposition.objects.filter(
                    number__startswith=self.deposition_prefix).values_list("number", flat=True).all()
                deposition_numbers = [int(number[len(self.deposition_prefix):]) for number in deposition_numbers]
                max_deposition_number = max(deposition_numbers) if deposition_numbers else 0
                if not self.deposition or self.deposition_form.cleaned_data["number"] != deposition.number:
                    if number_only < max_deposition_number + len(self.layer_forms):
                        utils.append_error(self.deposition_form, _(u"Overlap with previous deposition numbers."))
                        referentially_valid = False
                else:
                    higher_deposition_numbers = [number for number in deposition_numbers if number >= number_only]
                    if higher_deposition_numbers:
                        next_number = min(higher_deposition_numbers)
                        number_of_next_layers = models.LargeAreaDeposition.objects.get(
                            name=self.deposition_prefix+utils.three_digits(next_number)).layers.count()
                        if number_only + number_of_next_layers > next_number:
                            utils.append_error(self.deposition_form, _(u"New layers collide with following deposition."))
                            referentially_valid = False
                for i, layer_form in enumerate(self.layer_forms):
                    if layer_form.is_valid() and \
                            layer_form.cleaned_data["number"] - i + len(self.layer_forms) - 1 != number_only:
                        utils.append_error(self.layer_form, _(u"Layer number is not consecutive."))
                        referentially_valid = False
        return referentially_valid
    def save_to_database(self):
        database_ready = self._is_all_valid()
        structure_changed = self.change_structure()
        database_ready = database_ready and not structure_changed
        database_ready = self._is_referentially_valid() and database_ready
        if database_ready:
            # FixMe: Write to database
            pass
        return database_ready
    def get_context_dict(self):
        return {"deposition": self.deposition_form, "samples": self.samples_form, "layers": self.layer_forms,
                "change_layers": self.change_layer_forms, "add_layer": self.add_layer_form}

@login_required
@check_permission("change_largeareadeposition")
def edit(request, deposition_number):
    form_set = FormSet(request.user)
    if request.method == "POST":
        form_set.from_post_data(request.POST)
        if form_set.save_to_database():
            request.session["success_report"] = \
                _(u"Deposition %s was successfully changed in the database.") % deposition_number
            return utils.HttpResponseSeeOther(django.core.urlresolvers.reverse("samples.views.main.main_menu"))
    else:
        form_set.from_database(request, deposition_number)
    title = _(u"Large-area deposition “%s”") % deposition_number if deposition_number else _(u"Add large-area deposition")
    context_dict = {"title": title}
    context_dict.update(form_set.get_context_dict())
    return render_to_response("edit_large_area_deposition.html", context_dict, context_instance=RequestContext(request))
