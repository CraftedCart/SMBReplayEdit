import bpy
import json

#Meta information
bl_info = {
    "name": "SMBReplayEdit",
    "author": "CraftedCart",
    "version": (1, 0),
    "blender": (2, 75, 0),
    "description": "SMB replay editing tools",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

#Operation
class SetupEnv(bpy.types.Operator):
    bl_idname = "object.setup_env"
    bl_label = "Setup environment"
    bl_description = "Sets various values/preferences to allow working with SMB replays easily"
    bl_options = {'REGISTER', 'UNDO'}

    #Execute function
    def execute(self, context):
        bpy.context.user_preferences.edit.use_negative_frames = True
        bpy.context.scene.render.fps = 60

        print("Setup environment")
        return {'FINISHED'}

#Operation
class LoadReplay(bpy.types.Operator):
    bl_idname = "object.load_replay"
    bl_label = "Load replay from JSON"
    bl_description = "Loads a replay from the source JSON file"
    bl_options = {'REGISTER', 'UNDO'}

    #Execute function
    def execute(self, context):
        #Read the JSON file
        print("Reading " + context.scene.source_json_prop)
        f = open(context.scene.source_json_prop, "r")
        jsonStr = f.read()
        f.close()
        print("Read JSON")

        rpl = json.loads(jsonStr) #rpl = replay

        ballPosDeltas = rpl["root"]["playerPositionDelta"]
        startPos = (
            -rpl["root"]["header"]["startPositionX"],
            rpl["root"]["header"]["startPositionZ"],
            rpl["root"]["header"]["startPositionY"],
        )

        #Add a sphere to act as the ball (Size = radius)
        bpy.ops.mesh.primitive_uv_sphere_add(location = startPos, size = 0.5)

        #Rename the sphere
        for obj in bpy.context.selected_objects:
            obj.name = "SMBPlayerSphere"

        #Keyframe the start position at frame -1
        context.scene.frame_set(-1)
        bpy.ops.anim.keyframe_insert_menu(type='Location')

        #Loop over all frames, and add a keyframe
        i = 0;
        for item in ballPosDeltas:
            context.scene.frame_set(i)

            #Translate the mesh
            bpy.ops.transform.translate(
                value = (
                    -ballPosDeltas[i][0],
                    ballPosDeltas[i][2],
                    ballPosDeltas[i][1]
                )
            )

            #Keyframe the location
            bpy.ops.anim.keyframe_insert_menu(type='Location')

            i += 1;

        print("Loaded replay")
        return {'FINISHED'}

#Operation
class WriteReplay(bpy.types.Operator):
    bl_idname = "object.write_replay"
    bl_label = "Write replay to JSON"
    bl_description = "Writes a replay to the target JSON file"
    bl_options = {'REGISTER', 'UNDO'}

    #Execute function
    def execute(self, context):
        #Find SMBPlayerSphere
        ball = bpy.data.objects["SMBPlayerSphere"]

        #Goto frame -1 and record the start positon
        context.scene.frame_set(-1)
        startPos = [
            ball.location[1],
            ball.location[2],
            -ball.location[0],
        ]

        #List containing all frame delta positions
        ballDeltaPos = []

        #Used so we can calculate the delta position
        prevPos = startPos

        #Loop over all (3839) frames
        for i in range(0, 3839):
            context.scene.frame_set(i)

            ballDeltaPos.append([
                -(prevPos[0] - ball.location[1]),
                -(prevPos[1] - ball.location[2]),
                -(-prevPos[2] - ball.location[0])
            ])

            prevPos = [
                    ball.location[1],
                    ball.location[2],
                    -ball.location[0]
                ]

        dict = {
            "comment": "Note - This JSON is NOT a valid replay! It provides snippets to splice into an existing replay",
            "header": {
                    "startPositionX": startPos[0],
                    "startPositionY": startPos[1],
                    "startPositionZ": startPos[2]
                },
            "playerPositionDelta": ballDeltaPos
            }

        str = json.dumps(dict, indent = 2)

        f = open(context.scene.target_json_prop, "w")
        f.write(str)
        f.close()

        print("Wrote replay")
        return {'FINISHED'}

#The tool shelf panel
class SMBReplayEditPanel(bpy.types.Panel):
    bl_label = "SMBReplayEdit"
    bl_idname = "smb_replay_edit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS" #Put the menu on the left tool shelf
    bl_category = "SMBReplayEdit" #Tab name of the tool shelf
    bl_context = (("objectmode"))

    #Menu and input
    def draw(self, context):
        obj = context.object
        scene = context.scene

        layout = self.layout

        #Setup environment
        layout.operator(SetupEnv.bl_idname)
        layout.label("Setup environment will tweak Blender")
        layout.label("    to make it easier to work with replays")
        layout.label("Use negative frames will be enabled")
        layout.label("    So you can select frame -1 and modify")
        layout.label("    the starting keyframe")
        layout.label("The framerate will be set to 60 FPS")

        layout.separator()

        #Load from JSON
        layout.prop(scene, "source_json_prop")
        layout.operator(LoadReplay.bl_idname)

        layout.separator()

        #Write to JSON
        layout.prop(scene, "target_json_prop")
        layout.operator(WriteReplay.bl_idname)
        layout.label("Will write frames 0 to 3839 (63.98s)")
        layout.label("The ball should be named SMBPlayerSphere")

        layout.separator()

        layout.label("The keyframe at -1 is where the start position is")

def register():
    bpy.utils.register_module(__name__)

    #Properties
    bpy.types.Scene.source_json_prop = bpy.props.StringProperty(
        name = "Source JSON File",
        description = "The JSON file to load from",
        subtype = 'FILE_PATH'
    )

    bpy.types.Scene.target_json_prop = bpy.props.StringProperty(
        name = "Target JSON File",
        description = "The JSON file to save to",
        subtype = 'FILE_PATH'
    )

    print("This add-on was activated")

def unregister():
    del bpy.types.Scene.source_json_prop
    del bpy.types.Scene.target_json_prop

    bpy.utils.unregister_module(__name__)
    print("This add-on was deactivated")

if __name__ == "__main__":
    register()
