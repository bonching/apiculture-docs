import bpy
import os
import math
import bmesh  # For volume calculation in fallback

# Get the directory where this script is loaded
script_dir = os.path.dirname(os.path.realpath(__file__))

# Make path relative/portable - adjust as needed
blend_file = os.path.join(script_dir, "/Users/pjramores/projects/bonching/SEAMEO/apiculture-docs/3d-animations/Needle Holder.blend")  # Assumes .blend is in same dir as script
# Alternative: blend_file = "/full/path/to/Needle Holder.blend"

# Load the blend file
try:
    bpy.ops.wm.open_mainfile(filepath=blend_file)
    print(f"Loaded: {blend_file}")
except Exception as e:
    print(f"Error loading {blend_file}: {e}")
    # Don't return; continue with current scene if load fails

# Clear existing rigid body world if it exists
if bpy.context.scene.rigidbody_world:
    bpy.ops.rigidbody.world_remove()

# Create rigid body world
bpy.ops.rigidbody.world_add()
bpy.context.scene.rigidbody_world.enabled = True

# Configure rigid body world settings (CORRECTED API PROPERTIES)
rbw = bpy.context.scene.rigidbody_world
rbw.time_scale = 1.0
rbw.substeps_per_frame = 20  # Corrected: Steps per frame (was 'steps_per_second')
rbw.solver_iterations = 20  # Higher for better constraint stability

# List all objects in the scene (filter for meshes)
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
print(f"Mesh objects in scene: {len(mesh_objects)}")
for obj in mesh_objects:
    print(f" - {obj.name}")


# Function to setup rigid body for an object (UPDATED WITH ROBUST CONTEXT HANDLING)
def setup_rigid_body(obj, body_type="ACTIVE", mass=1.0, friction=0.5, bounciness=0.0):
    """Setup rigid body physics for an object with robust context handling."""
    if not obj or obj.type != "MESH":
        print(f"Skipping invalid object: {obj.name if obj else 'None'}")
        return False

    # Ensure object is visible and selectable
    obj.hide_viewport = False
    obj.hide_select = False

    # Deselect all objects first (safe even without UI context)
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except RuntimeError:
        pass  # Ignore if no context for op

    # Set as active and select
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Add rigid body if not already present (with safer context override)
    if obj.rigid_body is None:
        try:
            # Safer context override: Only if screen exists
            override = bpy.context.copy()
            override['active_object'] = obj
            if bpy.context.screen:
                # Find VIEW_3D area safely
                view3d_area = None
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        view3d_area = area
                        break
                if view3d_area:
                    override['area'] = view3d_area
                    override['region'] = next((r for r in view3d_area.regions if r.type == 'WINDOW'), None)

            with bpy.context.temp_override(**override):
                bpy.ops.rigidbody.object_add()
        except RuntimeError as e:
            print(f"Failed to add rigid body to {obj.name}: {e}")
            # Fallback: Try without override
            try:
                bpy.ops.rigidbody.object_add()
            except RuntimeError as e2:
                print(f"Fallback also failed for {obj.name}: {e2}")
                return False
        except Exception as e:
            print(f"Unexpected error adding rigid body to {obj.name}: {e}")
            return False

    # Configure rigid body settings
    rb = obj.rigid_body
    rb.type = body_type
    rb.mass = mass
    rb.friction = friction
    rb.bounciness = bounciness
    rb.collision_shape = "MESH"
    rb.use_margin = True
    rb.margin = 0.005  # Finer margin for detailed meshes
    if body_type == "PASSIVE":
        rb.kinematic = False

    # Deselect after setup
    obj.select_set(False)

    print(f"Setup rigid body for: {obj.name} ({body_type})")
    return True


# Function to create fixed constraint between objects
def create_fixed_constraint(obj1, obj2, constraint_name=None, pivot_location=(0, 0, 0)):
    """Create a fixed constraint between two objects at a specific pivot."""
    if constraint_name is None:
        constraint_name = f"Fixed_{obj1.name}_{obj2.name}"
    # Create empty at pivot location (no context issue here)
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=pivot_location)
    empty = bpy.context.active_object
    empty.name = constraint_name
    # Add rigid body constraint (with basic context prep, safer)
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = empty
    empty.select_set(True)
    try:
        bpy.ops.rigidbody.constraint_add()
    except RuntimeError as e:
        print(f"Failed to add constraint {constraint_name}: {e}")
        return None
    empty.rigid_body_constraint.type = "FIXED"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    empty.rigid_body_constraint.use_breaking = False
    print(f"Created fixed constraint: {constraint_name} between {obj1.name} and {obj2.name} at {pivot_location}")
    return empty


# Function to create a hinge constraint (for rotation)
def create_hinge_constraint(obj1, obj2, constraint_name=None, use_motor=False, motor_speed=0, axis=(0, 0, 1),
                            pivot_location=(0, 0, 0)):
    """Create a hinge rigid body constraint for rotation."""
    if constraint_name is None:
        constraint_name = f"Hinge_{obj1.name}_{obj2.name}"
    # Create empty at pivot
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=pivot_location)
    empty = bpy.context.active_object
    empty.name = constraint_name
    # Add rigid body constraint (with safer prep)
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = empty
    empty.select_set(True)
    try:
        bpy.ops.rigidbody.constraint_add()
    except RuntimeError as e:
        print(f"Failed to add hinge constraint {constraint_name}: {e}")
        return None
    empty.rigid_body_constraint.type = "HINGE"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    empty.rigid_body_constraint.axis = axis  # Rotation axis (default Z)
    # Enable motor if requested
    if use_motor:
        empty.rigid_body_constraint.use_motor_ang = True
        empty.rigid_body_constraint.motor_ang_target_velocity = motor_speed
        empty.rigid_body_constraint.motor_ang_max_impulse = 10.0
    print(f"Created hinge constraint: {constraint_name} between {obj1.name} and {obj2.name} on axis {axis}")
    return empty


# New: Generic constraint for complex mechanisms (allows limits on DOF)
def create_generic_constraint(obj1, obj2, constraint_name=None, pivot_location=(0, 0, 0)):
    """Create a generic 6-DOF constraint with customizable limits (e.g., for screw motion)."""
    if constraint_name is None:
        constraint_name = f"Generic_{obj1.name}_{obj2.name}"
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=pivot_location)
    empty = bpy.context.active_object
    empty.name = constraint_name
    # Context prep for constraint
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except:
        pass
    bpy.context.view_layer.objects.active = empty
    empty.select_set(True)
    try:
        bpy.ops.rigidbody.constraint_add()
    except RuntimeError as e:
        print(f"Failed to add generic constraint {constraint_name}: {e}")
        return None
    empty.rigid_body_constraint.type = "GENERIC"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    # Example limits: Allow rotation on Z, translation on Y (adjust for your model)
    empty.rigid_body_constraint.use_limit_lin_x = True
    empty.rigid_body_constraint.limit_lin_x_lower = -0.1
    empty.rigid_body_constraint.limit_lin_x_upper = 0.1
    empty.rigid_body_constraint.use_limit_ang_z = True
    empty.rigid_body_constraint.limit_ang_z_lower = -math.pi
    empty.rigid_body_constraint.limit_ang_z_upper = math.pi
    print(f"Created generic constraint: {constraint_name} between {obj1.name} and {obj2.name}")
    return empty


# Function to animate bolt rotation with keyframes (axis-agnostic)
def animate_bolt_rotation(obj, start_frame=1, end_frame=250, rotations=2, axis_index=2):  # Default Z=2
    """Animate a bolt object rotation using keyframes on specified axis."""
    obj.rotation_mode = "XYZ"
    # Set initial rotation
    obj.rotation_euler[axis_index] = 0
    obj.keyframe_insert(data_path="rotation_euler", index=axis_index, frame=start_frame)
    # Set final rotation
    obj.rotation_euler[axis_index] = rotations * 2 * math.pi
    obj.keyframe_insert(data_path="rotation_euler", index=axis_index, frame=end_frame)
    # Make the animation linear
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"
    print(
        f"Animated {obj.name} rotation on axis {axis_index}: {rotations} rotations from frame {start_frame} to {end_frame}")


# Main setup
def setup_needle_holder_animation(bake_simulation=False, constraint_type="HINGE"):  # New param for constraint choice
    """Main function to setup the needle holder animation."""
    # Identify key objects
    bolt_obj = None
    connected_objects = []
    # Keyword matching
    for obj in mesh_objects:  # Use filtered list
        name_lower = obj.name.lower()
        if any(keyword in name_lower for keyword in ['bolt', 'screw', 'lead', 'ratchet']):
            bolt_obj = obj
            print(f"\nFound bolt/screw: {obj.name}")
        elif any(keyword in name_lower for keyword in ['slider', 'holder', 'needle', 'jaw']):
            connected_objects.append(obj)
            print(f"Found connected object: {obj.name}")

    # Fallback: Sort by bounding box volume (smallest = bolt?)
    if bolt_obj is None and mesh_objects:
        def get_volume(obj):
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            volume = bm.calc_volume()
            bm.free()
            return volume

        sorted_meshes = sorted(mesh_objects, key=get_volume)
        bolt_obj = sorted_meshes[0] if sorted_meshes else None
        connected_objects = sorted_meshes[1:]
        print(f"\nFallback: Using smallest mesh as bolt: {bolt_obj.name}")

    if bolt_obj is None:
        raise ValueError("ERROR: No suitable objects found for animation!")

    # Setup rigid bodies (with error handling)
    if not setup_rigid_body(bolt_obj, body_type="PASSIVE", mass=2.0):
        print("Warning: Failed to setup bolt rigid body!")
    else:
        bolt_obj.rigid_body.kinematic = True  # Drives animation

    for obj in connected_objects:
        if not setup_rigid_body(obj, body_type="ACTIVE", mass=1.0, friction=0.8):
            print(f"Warning: Failed to setup {obj.name} rigid body!")

    # Create constraints (use HINGE or GENERIC for relative motion)
    pivot_loc = bolt_obj.location  # Or compute joint: e.g., average locations
    for obj in connected_objects:
        if constraint_type == "FIXED":
            create_fixed_constraint(bolt_obj, obj, pivot_location=pivot_loc)
        elif constraint_type == "HINGE":
            create_hinge_constraint(bolt_obj, obj, pivot_location=pivot_loc, use_motor=True,
                                    motor_speed=1.0)  # Motor for driven rotation
        else:  # "GENERIC"
            create_generic_constraint(bolt_obj, obj, pivot_location=pivot_loc)

    # Animate the bolt (try axis 2=Z, but inspect model and adjust)
    animate_bolt_rotation(bolt_obj, start_frame=1, end_frame=250, rotations=2, axis_index=2)

    # Set animation frame range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 250
    bpy.context.scene.frame_current = 1

    # Optional bake
    if bake_simulation:
        try:
            bpy.ops.ptcache.bake_all(bake=True)
            print("Rigid body simulation baked!")
        except Exception as e:
            print(f"Bake failed: {e} (Preview without baking)")

    print("\n=== Animation setup complete! ===")
    print("Press space to play. Use 'constraint_type' param for FIXED/HINGE/GENERIC.")
    print(f"Frame range: {bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}")


# Run the setup function
setup_needle_holder_animation(bake_simulation=True, constraint_type="HINGE")  # Start with HINGE for rotation