import bpy
import os
import math
import bmesh

script_dir = os.path.dirname(os.path.realpath(__file__))
blend_file = os.path.join(script_dir, "/Users/pjramores/projects/bonching/SEAMEO/apiculture-docs/3d-animations/Needle Holder.blend")  # Adjust if needed

try:
    bpy.ops.wm.open_mainfile(filepath=blend_file)
    print(f"Loaded: {blend_file}")
except Exception as e:
    print(f"Error loading {blend_file}: {e}")

# Safer RB World: Lower substeps/iterations to prevent overload
if bpy.context.scene.rigidbody_world:
    bpy.ops.rigidbody.world_remove()
bpy.ops.rigidbody.world_add()
bpy.context.scene.rigidbody_world.enabled = True
rbw = bpy.context.scene.rigidbody_world
rbw.time_scale = 1.0
rbw.substeps_per_frame = 10  # Reduced for stability
rbw.solver_iterations = 10  # Reduced

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
print(f"Mesh objects: {len(mesh_objects)}")
for obj in mesh_objects:
    print(f" - {obj.name}")


def setup_rigid_body(obj, body_type="ACTIVE", mass=1.0, friction=0.5, bounciness=0.0, collision_shape="MESH"):
    if not obj or obj.type != "MESH":
        return False
    obj.hide_viewport = False
    obj.hide_select = False
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if obj.rigid_body is None:
        try:
            override = bpy.context.copy()
            override['active_object'] = obj
            if bpy.context.screen:
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        override['area'] = area
                        override['region'] = next((r for r in area.regions if r.type == 'WINDOW'), None)
                        break
            with bpy.context.temp_override(**override):
                bpy.ops.rigidbody.object_add()
        except Exception as e:
            print(f"Failed rigid body add for {obj.name}: {e}")
            return False
    rb = obj.rigid_body
    rb.type = body_type
    rb.mass = mass
    rb.friction = friction
    rb.bounciness = bounciness
    rb.collision_shape = collision_shape  # Param for testing CONVEX_HULL
    rb.use_margin = True
    rb.margin = 0.01  # Slightly larger for stability
    if body_type == "PASSIVE":
        rb.kinematic = False
    obj.select_set(False)
    print(f"Setup RB for {obj.name} ({body_type}, shape={collision_shape})")
    return True


# Constraint functions (unchanged, but with safer ops)
def create_fixed_constraint(obj1, obj2, constraint_name=None, pivot_location=(0, 0, 0)):
    if constraint_name is None:
        constraint_name = f"Fixed_{obj1.name}_{obj2.name}"
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=pivot_location)
    empty = bpy.context.active_object
    empty.name = constraint_name
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = empty
    empty.select_set(True)
    try:
        bpy.ops.rigidbody.constraint_add()
    except Exception as e:
        print(f"Failed constraint add: {e}")
        return None
    empty.rigid_body_constraint.type = "FIXED"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    empty.rigid_body_constraint.use_breaking = False
    print(f"Fixed constraint: {constraint_name}")
    return empty


def create_hinge_constraint(obj1, obj2, constraint_name=None, use_motor=False, motor_speed=0, axis=(0, 0, 1),
                            pivot_location=(0, 0, 0)):
    if constraint_name is None:
        constraint_name = f"Hinge_{obj1.name}_{obj2.name}"
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=pivot_location)
    empty = bpy.context.active_object
    empty.name = constraint_name
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = empty
    empty.select_set(True)
    try:
        bpy.ops.rigidbody.constraint_add()
    except Exception as e:
        print(f"Failed hinge add: {e}")
        return None
    empty.rigid_body_constraint.type = "HINGE"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    empty.rigid_body_constraint.axis = axis
    if use_motor:
        empty.rigid_body_constraint.use_motor_ang = True
        empty.rigid_body_constraint.motor_ang_target_velocity = motor_speed
        empty.rigid_body_constraint.motor_ang_max_impulse = 5.0  # Lowered for safety
    print(f"Hinge constraint: {constraint_name}")
    return empty


def create_generic_constraint(obj1, obj2, constraint_name=None, pivot_location=(0, 0, 0)):
    if constraint_name is None:
        constraint_name = f"Generic_{obj1.name}_{obj2.name}"
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=pivot_location)
    empty = bpy.context.active_object
    empty.name = constraint_name
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = empty
    empty.select_set(True)
    try:
        bpy.ops.rigidbody.constraint_add()
    except Exception as e:
        print(f"Failed generic add: {e}")
        return None
    empty.rigid_body_constraint.type = "GENERIC"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    # Loose limits to avoid lockup
    empty.rigid_body_constraint.use_limit_lin_x = True
    empty.rigid_body_constraint.limit_lin_x_lower = -0.05
    empty.rigid_body_constraint.limit_lin_x_upper = 0.05
    empty.rigid_body_constraint.use_limit_ang_z = True
    empty.rigid_body_constraint.limit_ang_z_lower = -math.pi / 2
    empty.rigid_body_constraint.limit_ang_z_upper = math.pi / 2
    print(f"Generic constraint: {constraint_name}")
    return empty


def animate_bolt_rotation(obj, start_frame=1, end_frame=250, rotations=2, axis_index=2):
    obj.rotation_mode = "XYZ"
    obj.rotation_euler[axis_index] = 0
    obj.keyframe_insert(data_path="rotation_euler", index=axis_index, frame=start_frame)
    obj.rotation_euler[axis_index] = rotations * 2 * math.pi
    obj.keyframe_insert(data_path="rotation_euler", index=axis_index, frame=end_frame)
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "LINEAR"
    print(f"Animated {obj.name}: {rotations} rotations")


def setup_needle_holder_animation(dry_run=False, bake_simulation=False, constraint_type="HINGE",
                                  collision_shape="MESH"):
    if dry_run:
        print("DRY RUN: Skipping ops, just printing setup...")
        return
    bolt_obj = None
    connected_objects = []
    for obj in mesh_objects:
        name_lower = obj.name.lower()
        if any(k in name_lower for k in ['bolt', 'screw', 'lead', 'ratchet']):
            bolt_obj = obj
            print(f"Found bolt: {obj.name}")
        elif any(k in name_lower for k in ['slider', 'holder', 'needle', 'jaw']):
            connected_objects.append(obj)
            print(f"Found connected: {obj.name}")
    if bolt_obj is None and mesh_objects:
        # Fallback volume sort
        def get_volume(o):
            bm = bmesh.new()
            bm.from_mesh(o.data)
            vol = bm.calc_volume()
            bm.free()
            return vol

        sorted_meshes = sorted(mesh_objects, key=get_volume)
        bolt_obj = sorted_meshes[0]
        connected_objects = sorted_meshes[1:]
        print(f"Fallback bolt: {bolt_obj.name}")
    if bolt_obj is None:
        raise ValueError("No objects found!")

    # Setup RBs
    setup_rigid_body(bolt_obj, "PASSIVE", 2.0, collision_shape=collision_shape)
    bolt_obj.rigid_body.kinematic = True
    for obj in connected_objects:
        setup_rigid_body(obj, "ACTIVE", 1.0, friction=0.8, collision_shape=collision_shape)

    # Constraints
    pivot_loc = bolt_obj.location
    for obj in connected_objects:
        if constraint_type == "FIXED":
            create_fixed_constraint(bolt_obj, obj, pivot_location=pivot_loc)
        elif constraint_type == "HINGE":
            create_hinge_constraint(bolt_obj, obj, pivot_location=pivot_loc, use_motor=True,
                                    motor_speed=0.5)  # Slower motor
        else:
            create_generic_constraint(bolt_obj, obj, pivot_location=pivot_loc)

    # Animate
    animate_bolt_rotation(bolt_obj, 1, 250, 2)

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 250
    bpy.context.scene.frame_current = 1

    # Safer Bake
    if bake_simulation:
        try:
            bpy.ops.ptcache.bake_all(bake=True)
            print("Bake complete!")
        except Exception as e:
            print(f"Bake failed (expected on crashy setups): {e}. Preview without bake.")

    print("\n=== Setup Done! ===")
    print("Spacebar to play. If crash, try dry_run=True or no bake.")


# Run safely: Dry run first, then full with no bake
setup_needle_holder_animation(dry_run=True)  # Test printout
setup_needle_holder_animation(bake_simulation=False, constraint_type="HINGE", collision_shape="MESH")  # Main run