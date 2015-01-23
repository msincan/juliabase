#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, the samples database.
#
# Copyright © 2008–2014 Forschungszentrum Jülich, Germany,
#                       Marvin Goblet <m.goblet@fz-juelich.de>,
#                       Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


from __future__ import unicode_literals
import samples.utils.views as utils
from institute.models import LayerThicknessMeasurement


class LayerThicknessForm(utils.ProcessForm):
    """Form for the layer thickness measurement.
    """
    class Meta:
        model = LayerThicknessMeasurement
        fields = "__all__"


class EditView(utils.ProcessView):
    model = LayerThicknessMeasurement
    form_class = LayerThicknessForm
