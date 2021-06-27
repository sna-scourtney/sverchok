# This file is part of project Sverchok. It's copyrighted by the contributors
# recorded in the version control history of the file, available from
# its original location https://github.com/nortikin/sverchok/commit/master
#
# SPDX-License-Identifier: GPL3
# License-Filename: LICENSE

import numpy as np

import bpy
from mathutils import Vector
from bpy.props import FloatProperty, EnumProperty, BoolProperty, IntProperty

from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode, zip_long_repeat, ensure_nesting_level, split_by_count
from sverchok.utils.curve import SvCurve
from sverchok.utils.curve.nurbs import SvNurbsCurve
from sverchok.utils.curve.nurbs_algorithms import intersect_nurbs_curves
from sverchok.utils.curve.freecad import curve_to_freecad, SvSolidEdgeCurve
from sverchok.dependencies import FreeCAD

class SvIntersectNurbsCurvesNode(bpy.types.Node, SverchCustomTreeNode):
    """
    Triggers: Intersect Curves
    Tooltip: Find intersection points of two NURBS curves
    """
    bl_idname = 'SvIntersectNurbsCurvesNode'
    bl_label = 'Intersect NURBS Curves'
    bl_icon = 'OUTLINER_OB_EMPTY'
    #sv_icon = 'SV_CONCAT_CURVES'

    def get_implementations(self, context):
        result = []
        if FreeCAD is not None:
            item = ('FREECAD', "FreeCAD", "Implementation from FreeCAD library", 0)
            result.append(item)
        
        item = ('NATIVE', "Sverchok", "Sverchok built-in implementation", 1)
        result.append(item)

        return result

    implementation : EnumProperty(
            name = "Implementation",
            items = get_implementations,
            update = updateNode)

    match_methods = [
            ('LONG', "Longest", "", 0),
            ('CROSS', "Cross", "", 1)
        ]

    matching : EnumProperty(
            name = "Matching",
            items = match_methods,
            update = updateNode)

    single : BoolProperty(
            name = "Find single intersection",
            default = True,
            update = updateNode)

    precision : FloatProperty(
            name = "Precision",
            default = 0.001,
            precision = 6,
            min = 0,
            update = updateNode)

    methods = [
            ('Nelder-Mead', "Nelder-Mead", "", 0),
            ('L-BFGS-B', 'L-BFGS-B', "", 1),
            ('SLSQP', 'SLSQP', "", 2),
            ('Powell', 'Powell', "", 3),
            ('trust-constr', 'Trust-Constr', "", 4)
        ]

    method : EnumProperty(
            name = "Numeric method",
            items = methods,
            default = methods[0][0],
            update = updateNode)

    split : BoolProperty(
            name = "Split by row",
            default = True,
            update = updateNode)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'implementation', text='')
        layout.prop(self, 'matching')
        layout.prop(self, 'single')
        if self.matching == 'CROSS':
            layout.prop(self, 'split')

    def draw_buttons_ext(self, context, layout):
        self.draw_buttons(context, layout)
        if self.implementation == 'NATIVE':
            layout.prop(self, 'precision')
            layout.prop(self, 'method')

    def sv_init(self, context):
        self.inputs.new('SvCurveSocket', "Curve1")
        self.inputs.new('SvCurveSocket', "Curve2")
        self.outputs.new('SvVerticesSocket', "Intersections")

    def _filter(self, points):
        if not points:
            return points

        prev = points[0]
        result = [prev]
        for p in points[1:]:
            r = (Vector(p) - Vector(prev)).length
            if r > 1e-4:
                result.append(p)
            prev = p
        return result

    def process_native(self, curve1, curve2):
        res = intersect_nurbs_curves(curve1, curve2,
                    method = self.method,
                    numeric_precision = self.precision)
        points = [r[2].tolist() for r in res]
        return self._filter(points)

    def process_freecad(self, sv_curve1, sv_curve2):
        fc_curve1 = curve_to_freecad(sv_curve1)[0]
        fc_curve2 = curve_to_freecad(sv_curve2)[0]
        points = fc_curve1.curve.intersectCC(fc_curve2.curve)
        points = [(p.X, p.Y, p.Z) for p in points]
        return self._filter(points)

    def match(self, curves1, curves2):
        if self.matching == 'LONG':
            return zip_long_repeat(curves1, curves2)
        else:
            return [(c1, c2) for c2 in curves2 for c1 in curves1]

    def process(self):
        if not any(socket.is_linked for socket in self.outputs):
            return

        curve1_s = self.inputs['Curve1'].sv_get()
        curve2_s = self.inputs['Curve2'].sv_get()

        curve1_s = ensure_nesting_level(curve1_s, 2, data_types=(SvCurve,))
        curve2_s = ensure_nesting_level(curve2_s, 2, data_types=(SvCurve,))

        points_out = []

        for curve1s, curve2s in zip_long_repeat(curve1_s, curve2_s):
            new_points = []
            for curve1, curve2 in self.match(curve1s, curve2s):
                curve1 = SvNurbsCurve.to_nurbs(curve1)
                if curve1 is None:
                    raise Exception("Curve1 is not a NURBS")
                curve2 = SvNurbsCurve.to_nurbs(curve2)
                if curve2 is None:
                    raise Exception("Curve2 is not a NURBS")

                if self.implementation == 'NATIVE':
                    ps = self.process_native(curve1, curve2)
                else:
                    ps = self.process_freecad(curve1, curve2)

                if self.single:
                    if len(ps) >= 1:
                        ps = ps[0]

                new_points.append(ps)

            if self.split:
                n = len(curve1s)
                new_points = split_by_count(new_points, n)

            points_out.append(new_points)

        self.outputs['Intersections'].sv_set(points_out)

def register():
    bpy.utils.register_class(SvIntersectNurbsCurvesNode)

def unregister():
    bpy.utils.unregister_class(SvIntersectNurbsCurvesNode)
