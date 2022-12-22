# imports
import glfw
from OpenGL.GL import *
from ctypes import *
from core.texture_manager import *
import threading
import numpy as np
from core.logger import *
from core.fileutils import *
from settings import *
from core.util import *

glfw.init()

class TerrainRenderer:
    def __init__(self, window, mode=GL_TRIANGLES):
        self.event = threading.Event()

        self.parent = window
        self.mode = mode
        self.vbos = {}
        self.debug_text = []

        self.texture_manager = TextureAtlas()
        self.listener = ListenerBase("cache/vbo/")
        self.listener2 = ListenerBase("cache/vbo_remove/")
        self.writer = WriterBase("cache/vbo/")
        self.writer2 = WriterBase("cache/vbo_remove/")
        self.delete_queue = []
        self.delete_queue_vbo = []
        self.create_queue = []
        self.vbos_being_rendered = 0
        self.rendering = False

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glDepthMask(GL_TRUE)
        glDepthRange(0.0, 1.0)
        glClearDepth(1.0)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glFrontFace(GL_CCW)
        if not USING_GRAPHICS_DEBUGGER:
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)

    def debug(self, text):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.debug_text.append(f"[{timestamp}] {text}")

    def create_vbo(self, id):
        self.create_queue.append(id)

    def _create_vbo(self, id):
        self.vbo, self.vbo_1 = glGenBuffers(2)
        self.debug("[TerrainRenderer] Creating VBO...")
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, VERTICES_SIZE, None, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_1)
        glBufferData(GL_ARRAY_BUFFER, TEXCOORDS_SIZE, None, GL_DYNAMIC_DRAW)
        self.debug("[TerrainRenderer] Setting default VBO data...")
        self.vbos[id] = {
            "vbo": self.vbo,
            "vbo_1": self.vbo_1,
            "_len": 0,
            "_len_": 0,
            "vertices": (),
            "texCoords": (),
            "render": True,
            "addition_history": []
        }

    def delete_vbo(self, id):
        self.delete_queue_vbo.append(id)

    def shared_context(self, window):
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        window2 = glfw.create_window(500,500, "Window 2", None, window)
        glfw.make_context_current(window2)
        self.event.set()

        while not glfw.window_should_close(window):
            if not self.rendering:
                time.sleep(1/60)
                try:
                    if self.listener.get_queue_length() > 0:
                        self.debug("[TerrainRenderer] Reading file...")
                        i = self.listener.get_last_item()
                        self.debug("[TerrainRenderer] Processing file...")
                        id = i["id"]
                        data = self.vbos[id]
                        vbo = data["vbo"]
                        vbo_1 = data["vbo_1"]
                        _vertices = data["vertices"]
                        _texCoords = data["texCoords"]
                        _len = data["_len"]
                        _len_ = data["_len_"]

                        vertices = np.array(i["vertices"], dtype=np.float32)
                        texture_coords = np.array(i["texCoords"], dtype=np.float32)

                        bytes_vertices = vertices.nbytes
                        bytes_texCoords = texture_coords.nbytes

                        verts = (GLfloat * len(vertices))(*vertices)
                        texCoords = (GLfloat * len(texture_coords))(*texture_coords)

                        # Check if the data is already in the VBO
                        if verts in data["addition_history"]:
                            continue
                        if texCoords in data["addition_history"]:
                            continue                    

                        log_vertex_addition((vertices, texture_coords), (bytes_vertices, bytes_texCoords), _len*4, _len_*4, self.listener.get_queue_length())
                        
                        self.debug("[TerrainRenderer] Adding data to VBO...")
                        glBindBuffer(GL_ARRAY_BUFFER, vbo)
                        glBufferSubData(GL_ARRAY_BUFFER, _len, bytes_vertices, verts)
                        if not USING_GRAPHICS_DEBUGGER:
                            glVertexPointer (3, GL_FLOAT, 0, None)
                        glFlush()

                        glBindBuffer(GL_ARRAY_BUFFER, vbo_1)
                        glBufferSubData(GL_ARRAY_BUFFER, _len_, bytes_texCoords, texCoords)
                        if not USING_GRAPHICS_DEBUGGER:
                            glTexCoordPointer(2, GL_FLOAT, 0, None)
                        glFlush()

                        self.debug("[TerrainRenderer] Updating VBO data...")
                        _vertices += tuple(vertices)
                        _texCoords += tuple(texture_coords)

                        _len += bytes_vertices
                        _len_ += bytes_texCoords

                        data["_len"] = _len
                        data["_len_"] = _len_
                        data["vertices"] = _vertices
                        data["texCoords"] = _texCoords
                        data["addition_history"].append((vertices, texture_coords))

                    if self.listener2.get_queue_length() > 0:
                        self.debug("[TerrainRenderer] Reading file...")
                        data = self.listener2.get_last_item()
                        self.debug("[TerrainRenderer] Processing file...")
                        id = data["id"]

                        vbo_data = data["vbo_data"]
                        vertices = vbo_data["vertices"]
                        texCoords = vbo_data["texCoords"]

                        _vertices = self.vbos[id]["vertices"]
                        _texCoords = self.vbos[id]["texCoords"]
                        self.debug("[TerrainRenderer] Processing index ranges...")

                        # Get index of the data in the VBO
                        indexrange_vertices = get_indexrange(_vertices, vertices)
                        indexrange_texCoords = [indexrange_vertices[0]//3*2, indexrange_vertices[1]//3*2]
                        self.debug("[TerrainRenderer] Removing data from VBO...")

                        # Remove the data from the VBO
                        _vertices = _vertices[:indexrange_vertices[0]] + _vertices[indexrange_vertices[1]:]
                        _texCoords = _texCoords[:indexrange_texCoords[0]] + _texCoords[indexrange_texCoords[1]:]

                        # Update the VBO
                        self.vbos[id]["vertices"] = _vertices
                        self.vbos[id]["texCoords"] = _texCoords

                        # Update the VBO on the GPU
                        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[id]["vbo"])
                        glBufferSubData(GL_ARRAY_BUFFER, 0, len(_vertices)*4, (GLfloat * len(_vertices))(*_vertices))
                        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[id]["vbo_1"])
                        glBufferSubData(GL_ARRAY_BUFFER, 0, len(_texCoords)*4, (GLfloat * len(_texCoords))(*_texCoords))

                        print("Removed data from VBO: " + id)

                    if len(self.delete_queue_vbo) > 0:
                        try:
                            id = self.delete_queue_vbo.pop()
                            # Remove all data from the VBO
                            self.vbos[id]["_len"] = 0
                            self.vbos[id]["_len_"] = 0
                            self.vbos[id]["vertices"] = ()
                            self.vbos[id]["texCoords"] = ()
                            self.vbos[id]["addition_history"] = []
                            self.debug("[TerrainRenderer] Deleting VBO data...")

                            glBindBuffer(GL_ARRAY_BUFFER, self.vbos[id]["vbo"])
                            glBufferData(GL_ARRAY_BUFFER, VERTICES_SIZE, None, GL_DYNAMIC_DRAW)
                            glBindBuffer(GL_ARRAY_BUFFER, self.vbos[id]["vbo_1"])
                            glBufferData(GL_ARRAY_BUFFER, TEXCOORDS_SIZE, None, GL_DYNAMIC_DRAW)
                            self.debug("[TerrainRenderer] Deleting VBO...")

                            glDeleteBuffers(2, [self.vbos[id]["vbo"], self.vbos[id]["vbo_1"]])

                            del self.vbos[id]
                            info("TerrainRenderer", "Deleted VBO: " + id)
                        except:
                            pass

                    for i in range(len(self.create_queue)):
                        id = self.create_queue.pop()
                        self.debug("[TerrainRenderer] Creating VBO...")
                        self._create_vbo(id)
                        
                except Exception as e:
                    error("TerrainRenderer", f"Error in thread: {e}")
                glfw.swap_buffers(window2)
        glfw.terminate()
        self.event.set()
        self.listener.thread.join()
        del self.listener

    def init(self, window):
        glfw.make_context_current(None)
        self.thread = threading.Thread(target=self.shared_context, args=[window], daemon=True)
        self.thread.start()
        self.event.wait()
        glfw.make_context_current(window)
        self.create_vbo("DEFAULT")

    def add(self, vertices, texCoords):
        self.writer.write("AUTO", {
            "vertices": vertices,
            "texCoords": texCoords,
        })

    def remove(self, vertices, texCoords, id):
        self.writer2.write("AUTO", {
            "vbo_data":{
                "vertices": vertices,
                "texCoords": texCoords,
            },
            "id": id
        })


    def init(self, window):
        glfw.make_context_current(None)
        thread = threading.Thread(
            target=self.shared_context, args=[window], daemon=True)
        thread.start()
        self.event.wait()
        glfw.make_context_current(window)

    def add_mesh(self, storage):
        to_add = storage._group()

        for i in to_add:
            self.add(i[0], i[1])

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT)

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        self.vbos_being_rendered = 0
        self.rendering = True
        try:
            for data in self.vbos.values():
                if data["render"]:
                    glBindBuffer(GL_ARRAY_BUFFER, data["vbo"])
                    if not USING_GRAPHICS_DEBUGGER:
                        glVertexPointer(3, GL_FLOAT, 0, None)
                    glFlush()

                    glBindBuffer(GL_ARRAY_BUFFER, data["vbo_1"])
                    if not USING_GRAPHICS_DEBUGGER:
                        glTexCoordPointer(2, GL_FLOAT, 0, None)
                    glFlush()

                    glDrawArrays(self.mode, 0, data["_len"]//8)
                    self.vbos_being_rendered += 1
        except RuntimeError:
            pass
        finally:
            self.rendering = False

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)