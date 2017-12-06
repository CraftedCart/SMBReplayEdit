import bpy
import json
import copy

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
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = 3839

        print("Setup environment")
        return {'FINISHED'}

#Operation
class LoadReplay(bpy.types.Operator):
    bl_idname = "object.load_replay"
    bl_label = "Load replay from source JSON"
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
        #This could take a while - display a progress indicator
        bpy.context.window_manager.progress_begin(0, 100)
        i = 0;
        for item in ballPosDeltas:
            bpy.context.window_manager.progress_update(i / len(ballPosDeltas))
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

        bpy.context.window_manager.progress_end()

        #Go back to frame 0 for convenience
        context.scene.frame_set(0)

        print("Loaded replay")
        return {'FINISHED'}

#Operation
class WriteReplay(bpy.types.Operator):
    bl_idname = "object.write_replay"
    bl_label = "Write replay to target JSON"
    bl_description = "Writes a replay to the target JSON file"
    bl_options = {'REGISTER', 'UNDO'}

    #Execute function
    def execute(self, context):
        #Find SMBPlayerSphere
        ball = bpy.data.objects.get("SMBPlayerSphere")

        #Check that an object named SMBPlayerSphere exists
        if ball == None:
            self.report({'ERROR'}, "Object SMBPlayerSphere does not exist\nCreate an object named that or load a replay (Which will create that object for you) before attempting to write a replay")
            return {'CANCELLED'}

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
        #This could take a while - display a progress indicator
        bpy.context.window_manager.progress_begin(0, 100)
        for i in range(0, 3839):
            bpy.context.window_manager.progress_update(i / 3839)
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

        bpy.context.window_manager.progress_end()

        dict = None #Output dict

        if context.scene.modify_json_prop:
            #Modify the source JSON
            f = open(context.scene.source_json_prop, "r")
            jsonStr = f.read()
            f.close()
            dict = json.loads(jsonStr)

            #Modify it
            dict["root"]["header"]["startPositionX"] = startPos[0]
            dict["root"]["header"]["startPositionY"] = startPos[1]
            dict["root"]["header"]["startPositionZ"] = startPos[2]
            dict["root"]["playerPositionDelta"] = ballDeltaPos
        else:
            #Don't modify the source JSON
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
        layout.label("- Use negative frames will be enabled")
        layout.label("    - So you can select frame -1 and modify")
        layout.label("      the starting keyframe")
        layout.label("- The framerate will be set to 60 FPS")
        layout.label("- The start frame will be set to 0")
        layout.label("- The end frame will be set to 3839 (63.98s)")

        layout.separator()

        #Load from JSON
        layout.prop(scene, "source_json_prop")
        layout.operator(LoadReplay.bl_idname, icon = "IMPORT")

        layout.separator()

        #Write to JSON
        layout.prop(scene, "target_json_prop")
        layout.prop(scene, "modify_json_prop")
        layout.operator(WriteReplay.bl_idname, icon = "EXPORT")
        layout.label("Will write frames 0 to 3839 (63.98s)")
        layout.label("The ball should be named SMBPlayerSphere")

        layout.separator()

        layout.label("The keyframe at -1 is where the start position is")
    
#Operation
class ToFrame(bpy.types.Operator):
    bl_idname = "object.to_frame"
    bl_label = "Jump to frame"
    bl_options = {'REGISTER', 'UNDO'}
    
    frame = bpy.props.IntProperty(name = "Frame")

    #Execute function
    def execute(self, context):
        context.scene.frame_set(self.frame)
        return {'FINISHED'}
    
#Operation
class IncCurrentFrame(bpy.types.Operator):
    bl_idname = "object.inc_current_frame"
    bl_label = "Increment curent frame"
    bl_description = "Moves the playback cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    frames = bpy.props.IntProperty(name = "Frames")

    #Execute function
    def execute(self, context):
        context.scene.frame_set(context.scene.frame_current + self.frames)
        return {'FINISHED'}
    
#Operation
class Accelerate(bpy.types.Operator):
    bl_idname = "object.accelerate"
    bl_label = "Accelerate and keyframe"
    bl_description = "Moves the ball over time"
    bl_options = {'REGISTER', 'UNDO'}
    
    frames = bpy.props.IntProperty(name = "Frames")

    #Execute function
    def execute(self, context):
        #Find SMBPlayerSphere
        ball = bpy.data.objects.get("SMBPlayerSphere")

        #Check that an object named SMBPlayerSphere exists
        if ball == None:
            self.report({'ERROR'}, "Object SMBPlayerSphere does not exist\nCreate an object named that or load a replay (Which will create that object for you) before attempting to accelerate")
        
        #Get the velocity by comparing location between the 2 previous frames
        context.scene.frame_set(context.scene.frame_current - 1)
        currentLoc = copy.copy(ball.location)
        context.scene.frame_set(context.scene.frame_current - 1)
        prevLoc = copy.copy(ball.location)
        velocity = [
                currentLoc[0] - prevLoc[0],
                currentLoc[1] - prevLoc[1],
                currentLoc[2] - prevLoc[2]
            ]
            
        #Move currentLoc
        for i in range(0, self.frames):
            velocity = [
                    velocity[0] + context.scene.accel_prop[0],
                    velocity[1] + context.scene.accel_prop[1],
                    velocity[2] + context.scene.accel_prop[2],
                ]
            
            currentLoc = [
                    currentLoc[0] + velocity[0],
                    currentLoc[1] + velocity[1],
                    currentLoc[2] + velocity[2]
                ]
                
            ball.location = currentLoc
            ball.keyframe_insert(data_path = "location", frame = context.scene.frame_current + 2 + i)
                
        #Set the current frame for convenience
        context.scene.frame_set(context.scene.frame_current + self.frames + 2)
        
        return {'FINISHED'}

#The tools tool shelf panel
class SMBReplayEditToolsPanel(bpy.types.Panel):
    bl_label = "SMBReplayEdit Tools"
    bl_idname = "smb_replay_edit_tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS" #Put the menu on the left tool shelf
    bl_category = "SMBReplayEdit" #Tab name of the tool shelf
    bl_context = (("objectmode"))

    #Menu and input
    def draw(self, context):
        obj = context.object
        scene = context.scene

        layout = self.layout
        
        layout.label("Timeline controls")

        #Timeline convenience controls
        row = layout.row(align=True)
        row.alignment = 'EXPAND'
        row.operator(ToFrame.bl_idname, icon = "REW", text = "To -1").frame = -1
        row.operator(ToFrame.bl_idname, icon = "REW", text = "To 0").frame = 0
        row.operator(ToFrame.bl_idname, icon = "FF", text = "To 3600").frame = 3600
        
        row = layout.row(align=True)
        row.alignment = 'EXPAND'
        #Icons took up too much space here
        row.operator(IncCurrentFrame.bl_idname, text = "- 60").frames = -60
        row.operator(IncCurrentFrame.bl_idname, text = "- 30").frames = -30
        row.operator(IncCurrentFrame.bl_idname, text = "- 15").frames = -15
        row.operator(IncCurrentFrame.bl_idname, text = "- 1").frames = -1
        row.operator(IncCurrentFrame.bl_idname, text = "+ 1").frames = 1
        row.operator(IncCurrentFrame.bl_idname, text = "+ 15").frames = 15
        row.operator(IncCurrentFrame.bl_idname, text = "+ 30").frames = 30
        row.operator(IncCurrentFrame.bl_idname, text = "+ 60").frames = 60
        
        layout.separator()

        #Acceleration
        layout.label("Acceleration")
        layout.label("Default gravity acceleration is 0, 0, -0.0098")
        layout.prop(scene, "accel_prop")
        layout.operator(Accelerate.bl_idname).frames = 1

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

    bpy.types.Scene.modify_json_prop = bpy.props.BoolProperty(
        name = "Modify existing replay",
        description = "If checked, the sections in the source JSON file will be modified and saved to the target JSON file, rather than writing an incomplete JSON replay\nThe source file will not be overwritten",
        default = True
    )
    
    bpy.types.Scene.accel_prop = bpy.props.FloatVectorProperty(
        name = "Acceleration",
        description = "The acceleration value (In Blender space, so Z = up, etc.)",
        default = [0, 0, -0.0098],
        precision = 4
    )

    print("This add-on was activated")

def unregister():
    del bpy.types.Scene.source_json_prop
    del bpy.types.Scene.target_json_prop
    del bpy.types.Scene.modify_json_prop
    del bpy.types.Scene.accel_prop

    bpy.utils.unregister_module(__name__)
    print("This add-on was deactivated")

if __name__ == "__main__":
    register()
