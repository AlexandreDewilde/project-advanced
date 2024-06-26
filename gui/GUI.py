import numpy as np
import pygfx as gfx
from wgpu.gui.auto import WgpuCanvas, run
from .FPSTime import FPSTime


class GUI:
    def __init__(
            self,
            sim,
            bound = (-10, 10, -10, 10),
            d3 = False,
            show_fps = True,
            line_color = (1, 0, 0, 1),
            line_colors = None,
            rectangle_color = (0, 1, 0, 0.6),
            rectangle_colors = None,
            particle_color = (0, 1, 1, 1),
            particle_colors = None,
            background_color = (1, 1, 1, 1),
            line_thickness = 2,
            steps_from_file = None,
            ):

        self.sim = sim
        self.bound = bound
        self.show_fps = show_fps
        self.d3 = d3
        self.line_color = line_color
        self.rectangle_color = rectangle_color
        self.particle_color = particle_color
        self.background_color = background_color
        self.line_thickness = line_thickness
        self.line_colors = line_colors
        self.rectangle_colors = rectangle_colors
        self.particle_colors = particle_colors
        self.break_anim = False
        self.size = (bound[1] - bound[0], bound[3] - bound[2])
        self.steps_from_file = steps_from_file

        self.init_scene()
        self.add_light()
        if self.show_fps:
            self.add_fps()

        self.init_sim()
        self.add_break()

        self.current_time = None
        if self.steps_from_file:
            self.parse_text_file()
            self.current_time = 0

    def init_scene(self):
        self.canvas = WgpuCanvas(max_fps=60, title="Granular material simulation")
        self.renderer = gfx.renderers.WgpuRenderer(self.canvas)

        self.scene = gfx.Scene()
        if self.d3:
            self.camera = gfx.PerspectiveCamera(50, 16/9)
            self.scene.add(self.camera.add(gfx.DirectionalLight()))
            self.controller = gfx.OrbitController(self.camera, register_events=self.renderer)
        else:
            self.camera = gfx.OrthographicCamera(*self.size)
            self.camera.show_rect(*self.bound)
        self.scene.add(gfx.Background(None, gfx.BackgroundMaterial(self.background_color)))

    def add_fps(self):
        self.stats = FPSTime(viewport=self.renderer)

    def add_light(self):
        self.scene.add(gfx.AmbientLight(intensity=0.2))

    def add_break(self):
        def break_anim(event):
            if event["key"] == " ":
                self.break_anim = not self.break_anim
        self.canvas.add_event_handler(break_anim, "key_down")

    def init_sim(self):
        if not self.d3:
            self.init_sim_2d()
        else:
            self.init_sim_3d()

    def init_sim_2d(self):
        w, h = self.canvas.get_logical_size()
        pos = self.sim.get_positions()
        sizes = 2 * self.sim.get_radius() * min(w, h) / min(self.size)
        self.geometry = gfx.Geometry(positions=pos, sizes=sizes)
        material = gfx.PointsMaterial(color=self.particle_color, size_mode="vertex", pick_write=True)
        points = gfx.Points(self.geometry, material)
        self.scene.add(points)

        for i, line in enumerate(self.sim.get_lines()):
            geometry = gfx.Geometry(positions=line, colors=[self.line_color if not self.line_colors else self.line_colors[i]])
            material = gfx.LineSegmentMaterial(thickness=self.line_thickness, color_mode="face")
            line = gfx.Line(geometry, material)
            self.scene.add(line)

    def init_sim_3d(self):
        pos = self.sim.get_positions()
        sizes = self.sim.get_radius()
        self.spheres = []
        for i, (coord, size) in enumerate(zip(pos, sizes)):
            geometry = gfx.sphere_geometry(radius=size)
            material = gfx.MeshPhongMaterial(color=self.particle_color if not self.particle_colors else self.particle_colors[i])
            mesh = gfx.Mesh(geometry, material)
            mesh.local.position = coord
            self.spheres.append(mesh)
            self.scene.add(mesh)

        self.camera.show_object(self.scene)

        for line in self.sim.get_lines():
            geometry = gfx.Geometry(positions=line, colors=[self.line_color])
            material = gfx.LineSegmentMaterial(thickness=self.line_thickness, color_mode="face")
            line = gfx.Line(geometry, material)
            self.scene.add(line)

        for i, rectangle in enumerate(self.sim.get_rectangles()):
            rect = gfx.Mesh(
                gfx.Geometry(positions=rectangle, indices=[[0, 1, 2, 3]]),
                gfx.MeshPhongMaterial(color=self.rectangle_color if not self.rectangle_colors else self.rectangle_colors[i])
            )
            self.scene.add(rect)

        for i, mesh in enumerate(self.sim.meshes):
            geometry = gfx.geometry_from_trimesh(mesh)
            material = gfx.material_from_trimesh(mesh)
            mesh = gfx.Mesh(geometry, material)
            self.scene.add(mesh)

    def parse_text_file(self):
        current_time = None
        current_positions = None
        self.t_history = []
        self.positions_history = []
        with open(self.steps_from_file, "r") as f:
            for line in f:
                if line.startswith("Computation time:"):
                    current_time = float(line.split()[-1])
                    current_positions = []
                    self.t_history.append(current_time)
                elif line.startswith("\tPosition"):
                    line = line.split(":")[1].strip()
                    current_positions.append(list(map(float, line.split())))
                elif line == "\n":
                    self.positions_history.append(np.array(current_positions))

    def animate(self):
        if not self.break_anim:
            if self.steps_from_file:
                if self.current_time >= len(self.positions_history):
                    return
                self.stats.set_sim_time(self.t_history[self.current_time])
            else:
                self.sim.step()
                self.stats.set_sim_time(self.sim.t if self.sim.t else 0)
        if not self.d3:
            self.geometry.positions.data[:, :] = self.sim.get_positions() if not self.steps_from_file else self.positions_history[self.current_time]
            self.geometry.positions.update_range()
        else:
            any(setattr(sphere.local, "position", coord) for sphere, coord in zip(self.spheres, self.sim.get_positions() if not self.steps_from_file else self.positions_history[self.current_time]))
        if self.stats:
            with self.stats:
                self.renderer.render(self.scene, self.camera, flush=False)
                self.stats.render()
        if self.current_time is not None:
            self.current_time += 1
        self.canvas.request_draw()

    def run(self):
        self.canvas.request_draw(self.animate)
        run()