import bpy
import json
import copy
import math

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
        ballRots = rpl["root"]["playerTilt"]
        stageRots = rpl["root"]["stageTilt"]
        startPos = (
            rpl["root"]["header"]["startPositionX"],
            -rpl["root"]["header"]["startPositionZ"],
            rpl["root"]["header"]["startPositionY"],
        )

        #Add a sphere to act as the ball (Size = radius)
        bpy.ops.mesh.primitive_uv_sphere_add(location = [0.0, 0.0, 0.0], size = 0.5)
        ball = bpy.context.active_object

        #Rename the sphere
        ball.name = "SMBPlayerSphere"

        #This could take a while - display a progress indicator
        bpy.context.window_manager.progress_begin(0, 100)
        PROGRESS_SECTIONS = 3 #Number of overall steps to complete

        ballPosEmpty = bpy.data.objects.new("SMBPlayerBallPos", None)
        bpy.context.scene.objects.link(ballPosEmpty)
        ballPosEmpty.location = startPos
        
        #Keyframe the start position at frame -1
        ballPosEmpty.keyframe_insert(data_path = "location", frame = -1)

        ball.parent = ballPosEmpty

        ############ LOCATION

        #Loop over all frames, and add a keyframe
        i = 0;
        for item in ballPosDeltas:
            bpy.context.window_manager.progress_update(i / len(ballPosDeltas) / PROGRESS_SECTIONS)

            #Translate the mesh
            ballPosEmpty.location = [
                    ballPosEmpty.location[0] + item[0],
                    ballPosEmpty.location[1] + -item[2],
                    ballPosEmpty.location[2] + item[1]
                ]

            #Keyframe the location
            ballPosEmpty.keyframe_insert(data_path = "location", frame = i)

            i += 1;

        ############ BALL ROTATION

        #Add an empty as a rotation indicator (Not really necessary, but could be useful)
        player = bpy.data.objects.new("SMBPlayerRotIndicator", None)
        bpy.context.scene.objects.link(player)
        player.empty_draw_type = "SINGLE_ARROW"
        player.parent = ball

        #Loop over all frames, and add a keyframe
        i = 0;
        for item in ballRots:
            bpy.context.window_manager.progress_update(i / len(ballRots) / 2 + (1 / PROGRESS_SECTIONS))

            #Translate the mesh
            ball.rotation_euler = [
                    math.radians(item[0]),
                    math.radians(-item[2]),
                    math.radians(item[1])
                ]

            #Keyframe the location
            ball.keyframe_insert(data_path = "rotation_euler", frame = i)

            i += 1;
            
        ############ STAGE ROTATION

        #Add an plane for stage tilt
        bpy.ops.mesh.primitive_plane_add(location = [0.0, 0.0, 0.0])
        tiltPlane = bpy.context.active_object
        
        #Set the origin point
        for vert in tiltPlane.data.vertices:
            vert.co[2] -= 0.5

        #Rename the plane
        tiltPlane.name = "SMBStageTilt"

        tiltPlane.parent = ballPosEmpty

        #Loop over all frames, and add a keyframe
        i = 0;
        for item in stageRots:
            bpy.context.window_manager.progress_update(i / len(stageRots) / 2 + (1 / PROGRESS_SECTIONS))

            #Translate the mesh
            tiltPlane.rotation_euler = [
                    math.radians(item[0]),
                    math.radians(-item[1]),
                    0.0
                ]

            #Keyframe the location
            tiltPlane.keyframe_insert(data_path = "rotation_euler", frame = i)

            i += 1;

        bpy.context.window_manager.progress_end()

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
        ballPosEmpty = bpy.data.objects.get("SMBPlayerBallPos") 
        ball = bpy.data.objects.get("SMBPlayerSphere")
        stageTilt = bpy.data.objects.get("SMBStageTilt")

        #Check that the objects exist
        if ballPosEmpty == None:
            self.report({'ERROR'}, "Object SMBPlayerBallPos does not exist\nCreate an object named that or load a replay (Which will create that object for you) before attempting to write a replay")
            return {'CANCELLED'}
        if ball == None:
            self.report({'ERROR'}, "Object SMBPlayerSphere does not exist\nCreate an object named that or load a replay (Which will create that object for you) before attempting to write a replay")
            return {'CANCELLED'}
        if stageTilt == None:
            self.report({'ERROR'}, "Object SMBStageTilt does not exist\nCreate an object named that or load a replay (Which will create that object for you) before attempting to write a replay")
            return {'CANCELLED'}

        #Goto frame -1 and record the start positon
        context.scene.frame_set(-1)
        startPos = [
            ballPosEmpty.location[0],
            ballPosEmpty.location[2],
            -ballPosEmpty.location[1],
        ]

        #List containing all frame delta positions
        ballDeltaPos = []
        #ballRots is absolute rot, not deltas - is in degrees
        ballRots = []
        #stageRots is also absolute rot
        stageRots = []

        #Used so we can calculate the delta position
        prevPos = startPos

        #Loop over all (3840) frames
        #This could take a while - display a progress indicator
        bpy.context.window_manager.progress_begin(0, 100)
        for i in range(0, 3840):
            bpy.context.window_manager.progress_update(i / 3840)
            context.scene.frame_set(i)

            ballDeltaPos.append([
                -(prevPos[0] - ballPosEmpty.location[0]),
                -(prevPos[1] - ballPosEmpty.location[2]),
                -(prevPos[2] - -ballPosEmpty.location[1])
            ])
            
            ballRots.append([
                math.degrees(ball.rotation_euler[0]),
                math.degrees(ball.rotation_euler[2]),
                -math.degrees(ball.rotation_euler[1]),
            ])
            
            stageRots.append([
                math.degrees(stageTilt.rotation_euler[0]),
                -math.degrees(stageTilt.rotation_euler[1]),
            ])

            prevPos = [
                    ballPosEmpty.location[0],
                    ballPosEmpty.location[2],
                    -ballPosEmpty.location[1]
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
            dict["root"]["playerTilt"] = ballRots
            dict["root"]["stageTilt"] = stageRots
            
        else:
            #Don't modify the source JSON
            dict = {
                "comment": "Note - This JSON is NOT a valid replay! It provides snippets to splice into an existing replay",
                "header": {
                        "startPositionX": startPos[0],
                        "startPositionY": startPos[1],
                        "startPositionZ": startPos[2]
                    },
                "playerPositionDelta": ballDeltaPos,
                "playerTilt": ballRots,
                "stageTilt": stageRots
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
        layout.label("- The end frame will be set to 3839 (40s inc. keyframe 0)")

        layout.separator()

        #Load from JSON
        layout.prop(scene, "source_json_prop")
        layout.operator(LoadReplay.bl_idname, icon = "IMPORT")

        layout.separator()

        #Write to JSON
        layout.prop(scene, "target_json_prop")
        layout.prop(scene, "modify_json_prop")
        layout.operator(WriteReplay.bl_idname, icon = "EXPORT")
        layout.label("Will write frames 0 to 3839 (64s)")
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

#def short_to_rad(val):
#    val += 32767
#    val /= 65536.0 * math.pi * 2
#    val -= math.pi
#    return val

if __name__ == "__main__":
    register()

