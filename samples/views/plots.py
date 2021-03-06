#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, see http://www.juliabase.org.
# Copyright © 2008–2015 Forschungszentrum Jülich GmbH, Jülich, Germany
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""View for showing a plot as a PDF file.
"""

from __future__ import absolute_import, unicode_literals
import django.utils.six as six

import os.path
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.conf import settings
import jb_common.utils.base
from jb_common.signals import storage_changed
from samples import models, permissions
import samples.utils.views as utils
from samples.utils.plots import PlotError


@login_required
def show_plot(request, process_id, plot_id, thumbnail):
    """Shows a particular plot.  Although its response is a bitmap rather than
    an HTML file, it is served by Django in order to enforce user permissions.

    :param request: the current HTTP Request object
    :param process_id: the database ID of the process to show
    :param plot_id: the plot_id of the image.  This is mostly ``u""`` because
        most measurement models have only one graphics.
    :param thumbnail: whether we serve a thumbnail instead of a real PDF plot

    :type request: HttpRequest
    :type process_id: unicode
    :type plot_id: unicode
    :type thumbnail: bool

    :return:
      the HTTP response object with the image

    :rtype: HttpResponse
    """
    process = get_object_or_404(models.Process, pk=utils.convert_id_to_int(process_id))
    process = process.actual_instance
    permissions.assert_can_view_physical_process(request.user, process)
    plot_filepath = process.calculate_plot_locations(plot_id)["thumbnail_file" if thumbnail else "plot_file"]
    datafile_name = process.get_datafile_name(plot_id)
    if datafile_name is None:
        raise Http404("No such plot available.")
    timestamps = [] if thumbnail else [sample.last_modified for sample in process.samples.all()]
    timestamps.append(process.last_modified)
    if datafile_name:
        datafile_names = datafile_name if isinstance(datafile_name, list) else [datafile_name]
        if not all(os.path.exists(filename) for filename in datafile_names):
            raise Http404("One of the raw datafiles was not found.")
        update_necessary = jb_common.utils.base.is_update_necessary(plot_filepath, datafile_names, timestamps)
    else:
        update_necessary = jb_common.utils.base.is_update_necessary(plot_filepath, timestamps=timestamps)
    if update_necessary:
        try:
            if thumbnail:
                figure = Figure(frameon=False, figsize=(4, 3))
                canvas = FigureCanvasAgg(figure)
                axes = figure.add_subplot(111)
                axes.set_position((0.17, 0.16, 0.78, 0.78))
                axes.grid(True)
                process.draw_plot(axes, plot_id, datafile_name, for_thumbnail=True)
                jb_common.utils.base.mkdirs(plot_filepath)
                canvas.print_figure(plot_filepath, dpi=settings.THUMBNAIL_WIDTH / 4)
            else:
                figure = Figure()
                canvas = FigureCanvasAgg(figure)
                axes = figure.add_subplot(111)
                axes.grid(True)
                axes.set_title(six.text_type(process))
                process.draw_plot(axes, plot_id, datafile_name, for_thumbnail=False)
                # FixMe: Activate this line with Matplotlib 1.1.0.
#                figure.tight_layout()
                jb_common.utils.base.mkdirs(plot_filepath)
                canvas.print_figure(plot_filepath, format="pdf")
            storage_changed.send(models.Process)
        except PlotError as e:
            raise Http404(six.text_type(e) or "Plot could not be generated.")
        except ValueError as e:
            raise Http404("Plot could not be generated: " + e.args[0])
    return jb_common.utils.base.static_file_response(plot_filepath,
                                                     None if thumbnail else process.get_plotfile_basename(plot_id) + ".pdf")
