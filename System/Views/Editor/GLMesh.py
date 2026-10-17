from __future__ import annotations

import numpy

from OpenGL import GL

# OpenGL Mesh Representation

class GLMesh:
    def __init__(
            self,
            vertex_data:          numpy.ndarray,
            layout_configuration: list[tuple[int, int]],
            usage_pattern:        int = GL.GL_STATIC_DRAW
        ) -> None:

        self.vertex_array_object_identifier:  int | None            = None
        self.vertex_buffer_object_identifier: int | None            = None
        self.vertex_count:                    int                   = 0
        self.layout_configuration:            list[tuple[int, int]] = layout_configuration
        self.usage_pattern:                   int                   = usage_pattern

        self.stride_bytes: int = sum(component_count for _, component_count in layout_configuration) * 4

        self.rebuild(vertex_data)

    def rebuild(self, vertex_data: numpy.ndarray) -> None:
        if vertex_data.size == 0:
            self.vertex_count = 0
            return

        total_floats_per_vertex = self.stride_bytes // 4
        self.vertex_count       = vertex_data.size // total_floats_per_vertex

        if self.vertex_array_object_identifier is None:
            self.vertex_array_object_identifier  = GL.glGenVertexArrays(1)
            self.vertex_buffer_object_identifier = GL.glGenBuffers(1)

        GL.glBindVertexArray(self.vertex_array_object_identifier)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_object_identifier)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, self.usage_pattern)

        byte_offset = 0

        for location_index, component_count in self.layout_configuration:
            GL.glEnableVertexAttribArray(location_index)
            GL.glVertexAttribPointer(
                location_index,
                component_count,
                GL.GL_FLOAT,
                GL.GL_FALSE,
                self.stride_bytes,
                GL.ctypes.c_void_p(byte_offset)
            )
            byte_offset += component_count * 4

        GL.glBindVertexArray(0)

    def draw(self, draw_mode: int = GL.GL_TRIANGLES) -> None:
        if self.vertex_array_object_identifier is None or self.vertex_count == 0:
            return

        GL.glBindVertexArray(self.vertex_array_object_identifier)
        GL.glDrawArrays(draw_mode, 0, self.vertex_count)
        GL.glBindVertexArray(0)

    def cleanup(self) -> None:
        if self.vertex_buffer_object_identifier is not None:
            GL.glDeleteBuffers(1, [self.vertex_buffer_object_identifier])
            self.vertex_buffer_object_identifier = None

        if self.vertex_array_object_identifier is not None:
            GL.glDeleteVertexArrays(1, [self.vertex_array_object_identifier])
            self.vertex_array_object_identifier = None

        self.vertex_count = 0