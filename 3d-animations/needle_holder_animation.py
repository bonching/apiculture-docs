import bpy
import os
import math

# Get the directory where this script is loaded
script_dir = os.path.dirname(os.path.realpath(__file__))
blend_file = os.path.join(script_dir, "Needle Holder.blend")

# Load the blend file
bpy.ops.wm.open_mainfile(filepath=blend_file)

print(f"Loaded: {blend_file}")

# Clear existing rigid body world if it exists
if bpy.context.scene.rigidbody_world:
    bpy.ops.rigidbody.world_remove()

# Create rigid body world
bpy.ops.rigidbody.world_add()
bpy.context.scene.rigidbody_world.enabled = True

# Configure rigid body world settings
rbw = bpy.context.scene.rigidbody_world
rbw.time_scale = 1.0
rbw.steps_per_second = 60
rbw.solver_iterations = 10

# List all objects in the scene
print(f"Objects in scene: {len(bpy.context.scene.objects)}")
for obj in bpy.context.scene.objects:
    print(f" - {obj.name} (Type: {obj.type})")

# Function to setup rigid body for an object
def setup_rigid_body(obj, body_type="ACTIVE", mass=1.0, friction=0.5, bounciness=0.0):
    """Setup rigid body physics for an object."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Add rigid body if not already present
    if obj.rigid_body is None:
        bpy.ops.rigidbody.object_add()

    # Configure rigid body settings
    obj.rigid_body.type = body_type
    obj.rigid_body.mass = mass
    obj.rigid_body.friction = friction
    obj.rigid_body.bounciness = bounciness
    obj.rigid_body.collision_shape = "MESH"
    obj.rigid_body.use_margin = True
    obj.rigid_body.margin = 0.01

    if body_type == "PASSIVE":
        obj.rigid_body.kinematic = False

    obj.select_set(False)
    print(f"Setup rigid body for: {obj.name} ({body_type})")

# Function to create fixed constraint between objects
def create_fixed_constraint(obj1, obj2, constraint_name=None):
    """Create a fixed constraint between two objects."""
    if constraint_name is None:
        constraint_name = f"Constraint_{obj1.name}_{obj2.name}"

    # Create an empty at the location between the two objects
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=obj1.location)
    empty = bpy.context.active_object
    empty.name = constraint_name

    # Add rigid body constraint
    bpy.ops.rigidbody.constraint_add()
    empty.rigid_body_constraint.type = "FIXED"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2
    empty.rigid_body_constraint.use_breaking = False

    print(f"Created fixed constraint: {constraint_name} between {obj1.name} and {obj2.name}")
    return empty

# Function to create a hinge constraint (for rotation)
def create_hinge_constraint(obj1, obj2, constraint_name=None, use_motor=False, motor_speed=0):
    """Create a hinge rigid body constraint for rotation."""
    if constraint_name is None:
        constraint_name = f"Hinge_{obj1.name}_{obj2.name}"

    # Create an empty at the location of obj1
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=obj1.location)
    empty = bpy.context.active_object
    empty.name = constraint_name

    # Add rigid body constraint
    bpy.ops.rigidbody.constraint_add()
    empty.rigid_body_constraint.type = "HINGE"
    empty.rigid_body_constraint.object1 = obj1
    empty.rigid_body_constraint.object2 = obj2

    # Enable motor if requested
    if use_motor:
        empty.rigid_body_constraint.use_motor_ang = True
        empty.rigid_body_constraint.motor_ang_target_velocity = motor_speed
        empty.rigid_body_constraint.motor_ang_max_impulse = 10.0

    print(f"Created hinge constraint: {constraint_name} between {obj1.name} and {obj2.name}")
    return empty

# Function to animate bolt rotation with keyframes
def animate_bolt_rotation(obj, start_frame=1, end_frame=250, rotations=2):
    """Animate a bolt object rotation using keyframes."""
    obj.rotation_mode = "XYZ"

    # Set initial rotation
    obj.rotation_euler.z = 0
    obj.keyframe_insert(data_path="rotation_euler", index=2, frame=start_frame)

    # Set final rotation
    obj.rotation_euler.z = rotations * 2 * math.pi
    obj.keyframe_insert(data_path="rotation_euler", index=2, frame=end_frame)

    # Make the animation linear
    if obj.animation_data:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"

    print(f"Animated {obj.name} rotation: {rotations} rotations from frame {start_frame} to {end_frame}")

# Main setup
def setup_needle_holder_animation():
    """Main function to setup the needle holder animation."""

    # Identify key objects (adjust these names based on your actual object names)
    # Common naming patterns: bolt, screw, lead_screw, slider, holder, etc.

    bolt_obj = None
    connected_objects = []

    # Try to find bolt/screw holder
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            name_lower = obj.name.lower()
            if any(keyword in name_lower for keyword in ['bolt', 'screw', 'lead']):
                bolt_obj = obj
                print(f"\n Found bolt/screw: {obj.name}")
            elif any(keyword in name_lower for keyword in ['slider', 'holder', 'needle']):
                connected_objects.append(obj)
                print(f"Found connected object: {obj.name}")

    # If no bolt found, try to identify by position or use first mesh object
    if bolt_obj is None and len(bpy.data.objects) > 0:
        mesh_objs = [obj for obj in bpy.data.objects if obj.type == "MESH"]
        if mesh_objs:
            bolt_obj = mesh_objs[0]
            connected_objects = mesh_objs[1:]
            print(f"\nUsing first mesh object as bolt: {bolt_obj.name}")

    if bolt_obj is None:
        print("ERROR: No suitable objects found for animation!")
        return

    # Setup rigid bodies
    # Bolt is animated (kinematic and animated passive)
    setup_rigid_body(bolt_obj, body_type="PASSIVE", mass=2.0)
    bolt_obj.rigid_body.kinematic = True

    # Connected objects are active rigid bodies
    for obj in connected_objects:
        setup_rigid_body(obj, body_type="ACTIVE", mass=1.0, friction=0.5)

    # Create constraint between bolt and connected objects
    for obj in connected_objects:
        create_fixed_constraint(bolt_obj, obj)

    # Animate the bolt rotation
    animate_bolt_rotation(bolt_obj, start_frame=1, end_frame=250, rotations=2)

    # Set animation frame range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 250
    bpy.context.scene.frame_current = 1

    print("\n=== Animation setup complete! ===")
    print("Press space to play animation.")
    print(f"Frame range: {bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}")

# Run the setup function
setup_needle_holder_animation()

# Optional: Bake the rigid body simulation
# Uncomment the following lines to bake the simulation
# bpy.ops.ptcache.bake_all(bake=True)
# print("Rigid body simulation baked!")