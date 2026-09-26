"""House render rig — one camera, one light, one canvas for every Graveborne sprite.

Every asset obeys the same contract, so a sprite drops into the battle grid with no per-asset tuning:

  * 1 Blender unit = 1 battle tile. The tile centre is the world origin; +Y is north (away from the camera), +Z up.
  * Figures stand on a miniature base whose top is at z = BASE_H and face the camera (-Y).
  * Camera: orthographic, looking north, pitched ELEV degrees below the horizon (a high three-quarter view,
    matching the game's convention of top-down ground with props drawn standing up the screen).
  * Canvas: CANVAS tiles square. The tile centre projects to (50%, ANCHOR_Y) of the image, so in CSS a sprite is
    placed at width 1.5*TS, left -0.25*TS, top TS/2 - ANCHOR_Y*1.5*TS  (= -0.61*TS).
  * Light: warm key from the viewer's upper-left front, cool fill from the right, cold rim from behind. The rim is
    what separates a dark figure from dark ground at 26px, so it is never optional.
"""
import math
import bpy
from mathutils import Vector

CANVAS = 1.5      # tiles across the (square) image
ANCHOR_Y = 0.74   # where the tile centre lands, as a fraction of image height from the top
BASE_H = 0.035    # miniature base thickness (feet stand at this height)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'NONE'
    return sc


def _aim(obj, direction):
    """Point an object's local -Z (lights, cameras) along `direction`."""
    obj.rotation_euler = Vector(direction).normalized().to_track_quat('-Z', 'Y').to_euler()


def camera(elev=55.0, canvas=CANVAS, anchor_y=ANCHOR_Y):
    """Orthographic camera looking north, pitched `elev` degrees down, framed so the origin lands on the anchor."""
    sc = bpy.context.scene
    th = math.radians(elev)
    d = Vector((0.0, math.cos(th), -math.sin(th)))            # view direction
    c = canvas * (anchor_y - 0.5)                              # screen-up offset of the image centre from the origin
    p0 = Vector((0.0, c * math.sin(th), c * math.cos(th)))     # a point on the camera axis
    cd = bpy.data.cameras.new('cam')
    cd.type = 'ORTHO'
    cd.ortho_scale = canvas
    cd.clip_start, cd.clip_end = 0.01, 100.0
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    cam.location = p0 - d * 20.0
    cam.rotation_euler = (math.pi / 2 - th, 0.0, 0.0)
    sc.camera = cam
    return cam


def _sun(name, frm, energy, color, angle_deg, shadow=True):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = energy
    ld.color = color
    ld.angle = math.radians(angle_deg)
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    _aim(ob, -Vector(frm))
    return ob


def lights(rim_color=(0.80, 0.88, 1.0), rim_energy=4.0, key_energy=2.6):
    """The house light. `frm` vectors point FROM the scene TOWARD the light.
    Only the key casts shadows: rims exist to carve the silhouette, not to throw shadows at the camera."""
    _sun('key', (-0.50, -0.55, 1.05), key_energy, (1.0, 0.86, 0.70), 16)    # high: short shadows stay on the tile
    _sun('fill', (0.90, -0.35, 0.30), 0.35, (0.55, 0.65, 0.92), 30, shadow=False)
    _sun('rim', (0.40, 0.95, 0.45), rim_energy, rim_color, 4, shadow=False)
    _sun('rim2', (-0.80, 0.65, 0.30), rim_energy * 0.5, rim_color, 6, shadow=False)
    _sun('contact', (0.0, 0.0, 1.0), 0.6, (1.0, 0.95, 0.9), 70)     # soft overhead: a grounding blob under the feet


def world(top=(0.075, 0.078, 0.085), bottom=(0.008, 0.007, 0.006), strength=0.5):
    """Dim overcast dome: gives metal something to reflect and lifts the shadows a touch."""
    w = bpy.data.worlds.new('world')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    N, L = nt.nodes, nt.links
    bg = N['Background']
    bg.inputs['Strength'].default_value = strength
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    rmp = N.new('ShaderNodeValToRGB')
    rmp.color_ramp.elements[0].position = 0.35
    rmp.color_ramp.elements[0].color = (*bottom, 1)
    rmp.color_ramp.elements[1].position = 0.85
    rmp.color_ramp.elements[1].color = (*top, 1)
    mp = N.new('ShaderNodeMapRange')          # view z in [-1,1] -> [0,1]
    mp.inputs['From Min'].default_value = -1.0
    L.new(tc.outputs['Generated'], sep.inputs[0])
    L.new(sep.outputs['Z'], mp.inputs['Value'])
    L.new(mp.outputs['Result'], rmp.inputs['Fac'])
    L.new(rmp.outputs['Color'], bg.inputs['Color'])
    return w


def shadow_catcher(size=4.0):
    """Invisible floor that keeps only the shadows — so a sprite's shadow falls onto the game's own ground."""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    pl = bpy.context.active_object
    pl.name = 'shadow_catcher'
    pl.is_shadow_catcher = True
    return pl


def render_settings(res=768, samples=96, view='Standard', exposure=0.0, look='None'):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filter_size = 1.2
    sc.view_settings.view_transform = view
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


LOOKS = {
    # the grimdark house look: filmic grade, an overcast dome for steel to reflect, a harder key
    'grit':    dict(view='AgX', look='AgX - High Contrast', exposure=0.1,
                    world=dict(top=(0.13, 0.135, 0.15), bottom=(0.01, 0.009, 0.008), strength=0.7),
                    key=3.0, rim=3.4),
    # the first (painted-miniature) look, kept for comparison
    'painted': dict(view='Standard', look='None', exposure=0.0, world={}, key=2.6, rim=4.0),
}


def stage(elev=45.0, res=768, samples=96, rim_color=None, rim_energy=None, look='grit'):
    """Reset and build the complete house stage. Assets then add geometry and call render()."""
    L = LOOKS[look]
    reset()
    render_settings(res=res, samples=samples, view=L['view'], look=L['look'], exposure=L['exposure'])
    world(**L['world'])
    lights(rim_color=rim_color or (0.80, 0.88, 1.0), rim_energy=rim_energy or L['rim'], key_energy=L['key'])
    camera(elev=elev)
    shadow_catcher()
