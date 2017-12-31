SMBReplayEdit
=============

## Usage

- Grab smb-tools from PistonMiner here: https://github.com/PistonMiner/smb-tools
- Use it to convert a GCI containing an SMB 1 replay to JSON
- Load the Blender script, set the source JSON file to the generated JSON, and hit load
- Move and keyframe the location SMBPlayerBallPos to keyframe the ball location
- Rotate and keyframe the rotation of SMBPlayerBall for the ball rotation
- Rotate and keyframe the rotation of SMBStageTilt for the stage rotation
- Specity a target JSON file in the sidebar panel, making sure "Modify existing replay" is checked
- Hit write replay
- Use smb-build-replay from smb-tools to convert the JSON back to a GCI

