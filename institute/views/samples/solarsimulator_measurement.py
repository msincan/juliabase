#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase-Institute, see http://www.juliabase.org.
# Copyright © 2008–2015 Forschungszentrum Jülich GmbH, Jülich, Germany
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# In particular, you may modify this file freely and even remove this license,
# and offer it as part of a web service, as long as you do not distribute it.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import absolute_import, unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _, ugettext
import samples.utils.views as utils
from institute.models import SolarsimulatorMeasurement, SolarsimulatorCellMeasurement


class SolarsimulatorMeasurementForm(utils.ProcessForm):

    class Meta:
        model = SolarsimulatorMeasurement
        fields = "__all__"

    def __init__(self, user, *args, **kwargs):
        super(SolarsimulatorMeasurementForm, self).__init__(user, *args, **kwargs)
        self.fields["temperature"].widget.attrs.update({"size": "5"})


class SolarsimulatorCellForm(forms.ModelForm):

    class Meta:
        model = SolarsimulatorCellMeasurement
        exclude = ("measurement",)

    def __init__(self, *args, **kwargs):
        super(SolarsimulatorCellForm, self).__init__(*args, **kwargs)


class EditView(utils.SubprocessesMixin, utils.ProcessView):
    sub_model = SolarsimulatorCellMeasurement
    form_class = SolarsimulatorMeasurementForm
    subform_class = SolarsimulatorCellForm
    process_field, subprocess_field = "measurement", "cells"


_ = ugettext
