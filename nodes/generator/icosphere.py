# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

from math import pi, sqrt
import bpy
from bpy.props import IntProperty, FloatProperty, BoolVectorProperty
import bmesh
from mathutils import Matrix, Vector

from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode
from sverchok.utils.sv_bmesh_utils import numpy_data_from_bmesh
from sverchok.utils.math import from_cylindrical
from sverchok.utils.nodes_mixins.recursive_nodes import SvRecursiveNode


def icosahedron_cylindrical(r):

    d = 2.0/sqrt(5)

    # Calculate icosahedron vertices in cylindrical coordinates
    vertices = []
    vertices.append((0, 0, r))
    for i in range(5):
        vertices.append((d*r, pi/5 + i*2*pi/5, 0.5*d*r))
    for i in range(5):
        vertices.append((d*r, i*2*pi/5, -0.5*d*r))
    vertices.append((0, 0, -r))

    edges = []
    for i in range(1,6):
        edges.append((0,i))
    for i in range(1,5):
        edges.append((i, i+1))
    edges.append((1,5))
    for i in range(1,6):
        edges.append((i, i+5))
    for i in range(1,5):
        edges.append((i, i+6))
    edges.append((5,6))
    for i in range(6,10):
        edges.append((i, i+1))
    edges.append((6,10))
    for i in range(6,11):
        edges.append((i, 11))

    faces = []
    for i in range(1,5):
        faces.append([0, i, i+1])
    faces.append([0, 5, 1])
    for i in range(1,5):
        faces.append([i, i+6, i+1])
    faces.append([1, 5, 6])
    for i in range(1,5):
        faces.append([i, i+5, i+6])
    faces.append([5, 10, 6])
    for i in range(6,10):
        faces.append([i+1, i, 11])
    faces.append([6, 10, 11])

    return vertices, edges, faces

def icosahedron(r):
    vertices, edges, faces = icosahedron_cylindrical(r)
    vertices = [from_cylindrical(rho, phi, z, 'radians') for rho, phi, z in vertices]
    return vertices, edges, faces

class SvIcosphereNode(bpy.types.Node, SverchCustomTreeNode, SvRecursiveNode):
    "IcoSphere primitive"

    bl_idname = 'SvIcosphereNode'
    bl_label = 'IcoSphere'
    bl_icon = 'MESH_ICOSPHERE'

    replacement_nodes = [('SphereNode', None, dict(Faces='Polygons'))]

    def set_subdivisions(self, value):
        # print(value, self.subdivisions_max)
        if value > self.subdivisions_max:
            self['subdivisions'] = self.subdivisions_max
        else:
            self['subdivisions'] = value
        return None

    def get_subdivisions(self):
        return self['subdivisions']

    subdivisions: IntProperty(
        name = "Subdivisions", description = "How many times to recursively subdivide the sphere",
        default=2, min=0,
        set = set_subdivisions, get = get_subdivisions,
        update=updateNode)

    subdivisions_max: IntProperty(
        name = "Max. Subdivisions", description = "Maximum number of subdivisions available",
        default = 5, min=2,
        update=updateNode)

    radius: FloatProperty(
        name = "Radius",
        default=1.0, min=0.0,
        update=updateNode)

    # list_match: EnumProperty(
    #     name="List Match",
    #     description="Behavior on different list lengths, object level",
    #     items=list_match_modes, default="REPEAT",
    #     update=updateNode)
    out_np: BoolVectorProperty(
        name="Output Numpy",
        description="Output NumPy arrays slows this node but may improve performance of nodes it is connected to",
        default=(False, False, False),
        size=3, update=updateNode)

    def sv_init(self, context):
        self['subdivisions'] = 2

        self.inputs.new('SvStringsSocket', 'Subdivisions').prop_name = 'subdivisions'
        self.inputs.new('SvStringsSocket', 'Radius').prop_name = 'radius'

        self.outputs.new('SvVerticesSocket', "Vertices")
        self.outputs.new('SvStringsSocket',  "Edges")
        self.outputs.new('SvStringsSocket',  "Faces")

    def draw_buttons_ext(self, context, layout):
        layout.prop(self, "subdivisions_max")
        layout.prop(self, "list_match")
        layout.label(text="Output Numpy:")
        r = layout.row(align=True)
        for i in range(3):
            r.prop(self, "out_np", index=i, text=self.outputs[i].name, toggle=True)

    def pre_setup(self):
        for s in self.inputs:
            s.nesting_level = 1
            s.pre_processing = 'ONE_ITEM'

    def process_data(self, params):
        out_verts = []
        out_edges = []
        out_faces = []


        for subdivisions, radius in zip(*params):
            if subdivisions == 0:
                # In this case we just return the icosahedron
                verts, edges, faces = icosahedron(radius)
                out_verts.append(verts)
                out_edges.append(edges)
                out_faces.append(faces)
                continue

            if subdivisions > self.subdivisions_max:
                subdivisions = self.subdivisions_max

            bm = bmesh.new()
            bmesh.ops.create_icosphere(
                bm,
                subdivisions=subdivisions,
                diameter=radius)

            verts, edges, faces, _ = numpy_data_from_bmesh(bm, self.out_np)
            bm.free()

            out_verts.append(verts)
            out_edges.append(edges)
            out_faces.append(faces)

        return out_verts, out_edges, out_faces


def register():
    bpy.utils.register_class(SvIcosphereNode)

def unregister():
    bpy.utils.unregister_class(SvIcosphereNode)
